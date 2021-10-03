# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import json
import os
import random
import shutil
from typing import Dict

import mock
from django.conf import settings
from django.core.management import call_command
from mock import patch

from apps.backend.tests.components.collections.agent import utils
from apps.backend.tests.components.collections.job import utils as job_utils
from apps.core.files import constants as core_const
from apps.node_man import constants
from apps.node_man.tests.utils import create_cloud_area, create_host
from apps.utils import files
from apps.utils.files import md5sum
from apps.utils.unittest.testcase import CustomBaseTestCase

FAST_EXECUTE_SCRIPT = {
    "job_instance_name": "API Quick execution script1521100521303",
    "job_instance_id": 10000,
    "step_instance_id": 10001,
}


GET_AGENT_STATUS = {
    f"{constants.DEFAULT_CLOUD}:{utils.TEST_IP}": {
        "ip": utils.TEST_IP,
        "bk_cloud_id": constants.DEFAULT_CLOUD,
        "bk_agent_alive": constants.BkAgentStatus.ALIVE,
    }
}

POLL_RESULT = {
    "is_finished": True,
    "task_result": {
        "success": [{"ip": utils.TEST_IP, "bk_cloud_id": constants.DEFAULT_CLOUD, "log_content": ""}],
        "pending": [],
        "failed": [],
    },
}

OVERWRITE_OBJ__KV_MAP = {
    "settings": {
        "DOWNLOAD_PATH": "/tmp",
        "STORAGE_TYPE": "FILE_SYSTEM",
        "BKREPO_BUCKET": "bucket",
        "BKREPO_PROJECT": "project",
    }
}


class TestUpdateProxyFile(CustomBaseTestCase):
    download_files = [file_name for file_set in constants.FILES_TO_PUSH_TO_PROXY for file_name in file_set["files"]]

    @classmethod
    def init_proxy_host(cls, alive_number: int = 1, unknown_number: int = 0, ip=None, bk_cloud_id=None):
        if unknown_number:
            create_host(
                number=unknown_number,
                node_type="PROXY",
                proc_type="UNKNOWN",
                ip=ip,
                bk_cloud_id=bk_cloud_id,
                bk_host_id=random.randint(1e2, 1e5),
            )
        if alive_number:
            create_host(
                number=alive_number,
                node_type="PROXY",
                ip=ip,
                bk_cloud_id=bk_cloud_id,
                bk_host_id=random.randint(1e2, 1e5),
            )

    @classmethod
    def setUpTestData(cls):
        cls.JOB_MOCK_CLIENT = job_utils.JobV3MockApi(
            fast_execute_script_return=FAST_EXECUTE_SCRIPT,
        )
        cls.GSE_MOCK_CLIENT = utils.GseMockClient(
            get_agent_status_return=GET_AGENT_STATUS,
        )
        cls.JOB_DEMAND_MOCK_CLIENT = utils.JobDemandMock(poll_task_result_return=POLL_RESULT)

    def setUp(self) -> None:
        create_cloud_area(number=5, creator="admin")
        patch("apps.node_man.periodic_tasks.update_proxy_file.JobApi", self.JOB_MOCK_CLIENT).start()

    def test_file_system_update(self):
        # 不存在proxy
        self.assertIsNone(call_command("update_proxy_file"))

        # 没有存活的proxy
        GET_AGENT_STATUS[f"{constants.DEFAULT_CLOUD}:{utils.TEST_IP}"][
            "bk_agent_alive"
        ] = constants.BkAgentStatus.NOT_ALIVE
        patch("apps.node_man.periodic_tasks.update_proxy_file.client_v2", self.GSE_MOCK_CLIENT).start()
        self.init_proxy_host(alive_number=0, unknown_number=1)
        self.assertIsNone(call_command("update_proxy_file"))

        OVERWRITE_OBJ__KV_MAP["settings"]["DOWNLOAD_PATH"] = files.mk_and_return_tmpdir()
        with self.settings(
            DOWNLOAD_PATH=OVERWRITE_OBJ__KV_MAP["settings"]["DOWNLOAD_PATH"],
            STORAGE_TYPE=core_const.StorageType.FILE_SYSTEM.value,
        ):
            local_files_md5_map: Dict[str, str] = {}
            GET_AGENT_STATUS[f"{constants.DEFAULT_CLOUD}:{utils.TEST_IP}"][
                "bk_agent_alive"
            ] = constants.BkAgentStatus.ALIVE
            patch("apps.node_man.periodic_tasks.update_proxy_file.client_v2", self.GSE_MOCK_CLIENT).start()

            # 本地服务器没有相关文件
            self.init_proxy_host(alive_number=1, ip=utils.TEST_IP, bk_cloud_id=constants.DEFAULT_CLOUD)
            self.assertRaises(FileExistsError, call_command("update_proxy_file"))

            mock_source_file = self.download_files[random.randint(1, 5)]
            mock_compare_file = self.download_files[random.randint(6, 10)]
            size = random.randint(99, 2000)
            for mock_file in [mock_source_file, mock_compare_file]:
                with open(os.path.join(OVERWRITE_OBJ__KV_MAP["settings"]["DOWNLOAD_PATH"], mock_file), "wb") as e:
                    e.write(os.urandom(size))
            source_file_md5 = md5sum(os.path.join(settings.DOWNLOAD_PATH, mock_source_file))
            compare_file_md5 = md5sum(os.path.join(settings.DOWNLOAD_PATH, mock_compare_file))
            for file in self.download_files:
                local_files_md5_map.update({file: source_file_md5})
            storage_mock_client = utils.StorageMock(
                get_file_md5_return=source_file_md5, fast_transfer_file_return=10001
            )
            patch(
                "apps.node_man.periodic_tasks.update_proxy_file.get_storage", mock.MagicMock(storage_mock_client)
            ).start()

            # 本地文件不存在差异
            for job_result in POLL_RESULT["task_result"]["success"]:
                job_result["log_content"] = json.dumps(local_files_md5_map)
            patch("apps.node_man.periodic_tasks.update_proxy_file.JobDemand", self.JOB_DEMAND_MOCK_CLIENT).start()
            self.assertIsNone(call_command("update_proxy_file"))

            # 存在差异 同步文件
            for file in self.download_files:
                local_files_md5_map.update({file: compare_file_md5})
            storage_mock_client = utils.StorageMock(
                get_file_md5_return=compare_file_md5, fast_transfer_file_return=10001
            )
            patch(
                "apps.node_man.periodic_tasks.update_proxy_file.get_storage", mock.MagicMock(storage_mock_client)
            ).start()
            self.assertIsNone(call_command("update_proxy_file"))
            shutil.rmtree(settings.DOWNLOAD_PATH)

    def test_blueking_artifactory_update(self):
        with self.settings(
            DOWNLOAD_PATH=OVERWRITE_OBJ__KV_MAP["settings"]["DOWNLOAD_PATH"],
            STORAGE_TYPE=core_const.StorageType.BLUEKING_ARTIFACTORY.value,
            BKREPO_PROJECT=OVERWRITE_OBJ__KV_MAP["settings"]["BKREPO_PROJECT"],
            BKREPO_BUCKET=OVERWRITE_OBJ__KV_MAP["settings"]["BKREPO_BUCKET"],
        ):
            self.assertIsNone(call_command("update_proxy_file"))
