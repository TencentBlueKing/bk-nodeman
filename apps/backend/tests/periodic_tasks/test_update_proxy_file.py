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

import os
import random
import shutil
from typing import Optional

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


DOWNLOAD_PATH: Optional[str] = None
MD5SUM = {}

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
        "success": [
            {"ip": utils.TEST_IP, "bk_cloud_id": constants.DEFAULT_CLOUD, "log_content": '{"7z.exe": "1sd124bsdbsdb1"}'}
        ],
        "pending": [],
        "failed": [],
    },
}

Job_Mock_Client = job_utils.JobV3MockApi(
    fast_execute_script_return=FAST_EXECUTE_SCRIPT,
)

Gse_Mock_Client = utils.GseMockClient(
    get_agent_status_return=GET_AGENT_STATUS,
)

Storage_Mock_Client = utils.StorageMock(get_file_md5_return=MD5SUM, fast_transfer_file_return=10001)

Job_Demand_Mock_Client = utils.JobDemandMock(poll_task_result_return=POLL_RESULT)

OVERWRITE_OBJ__KV_MAP = {
    settings: {
        "DOWNLOAD_PATH": "/tmp",
        "STORAGE_TYPE": "FILE_SYSTEM",
        "BKREPO_BUCKET": "bucket",
        "BKREPO_PROJECT": "project",
    }
}


class TestUpdateProxyFile(CustomBaseTestCase):
    download_files = [c for f in constants.FILES_TO_PUSH_TO_PROXY for c in f["files"]]

    def setUp(self) -> None:
        create_cloud_area(number=5, creator="admin")
        alive_number, unknown_number = 1, 1
        host_to_create, _, _ = create_host(number=unknown_number, node_type="PROXY", proc_type="UNKNOWN")
        create_host(number=alive_number, node_type="PROXY", bk_host_id=20)
        patch("apps.node_man.periodic_tasks.update_proxy_file.client_v2", Gse_Mock_Client).start()
        patch("apps.node_man.periodic_tasks.update_proxy_file.JobApi", Job_Mock_Client).start()
        patch("apps.node_man.periodic_tasks.update_proxy_file.JobDemand", Job_Demand_Mock_Client).start()
        patch("apps.node_man.periodic_tasks.update_proxy_file.get_storage", mock.MagicMock(Storage_Mock_Client)).start()

    def test_file_system_update(self):
        self.DOWNLOAD_PATH = files.mk_and_return_tmpdir()
        OVERWRITE_OBJ__KV_MAP[settings]["DOWNLOAD_PATH"] = self.DOWNLOAD_PATH
        with self.settings(
            DOWNLOAD_PATH=OVERWRITE_OBJ__KV_MAP[settings]["DOWNLOAD_PATH"],
            STORAGE_TYPE=core_const.StorageType.FILE_SYSTEM.value,
        ):
            for file in self.download_files:
                size = random.randint(99, 2000)
                with open(os.path.join(settings.DOWNLOAD_PATH, file), "wb") as e:
                    e.write(os.urandom(size))
            # 存在差异，同步文件
            self.assertIsNone(call_command("update_proxy_file"))
            for file in self.download_files:
                MD5SUM.update({file: md5sum(os.path.join(settings.DOWNLOAD_PATH, file))})
            # 不存在差异
            self.assertIsNone(call_command("update_proxy_file"))
            shutil.rmtree(settings.DOWNLOAD_PATH)

    def test_blueking_artifactory_update(self):
        with self.settings(
            DOWNLOAD_PATH=OVERWRITE_OBJ__KV_MAP[settings]["DOWNLOAD_PATH"],
            STORAGE_TYPE=core_const.StorageType.BLUEKING_ARTIFACTORY.value,
            BKREPO_PROJECT=OVERWRITE_OBJ__KV_MAP[settings]["BKREPO_PROJECT"],
            BKREPO_BUCKET=OVERWRITE_OBJ__KV_MAP[settings]["BKREPO_BUCKET"],
        ):
            self.assertIsNone(call_command("update_proxy_file"))
