# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import base64

from django.conf import settings

from apps.backend.components.collections.agent_new import components
from apps.node_man import constants
from common.api import JobApi

from . import base


class PushEnvironFilesTestCaseMixin:

    GSE_ENVIRON_DIR: str = "/etc/sysconfig/gse/ce/environ.sh"
    GSE_ENVIRON_WIN_DIR: str = "C:\\Windows\\System32\\config\\gse\\test"

    OVERWRITE_OBJ__KV_MAP = {
        settings: {
            "GSE_ENVIRON_DIR": GSE_ENVIRON_DIR,
            "GSE_ENVIRON_WIN_DIR": GSE_ENVIRON_WIN_DIR,
            "GSE_ENABLE_PUSH_ENVIRON_FILE": True,
        },
    }

    def component_cls(self):
        return components.PushEnvironFilesComponent


class PushEnvironFilesTestCase(PushEnvironFilesTestCaseMixin, base.JobBaseTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "推送环境变量文件成功"

    def tearDown(self) -> None:
        record = self.job_api_mock_client.call_recorder.record

        # 该接口仅调用一次
        self.assertEqual(len(record[JobApi.push_config_file]), 1)
        push_config_file_query_params = record[JobApi.push_config_file][0].args[0]

        # 仅下发一个配置文件
        self.assertEqual(len(push_config_file_query_params["file_list"]), 1)
        config_info = push_config_file_query_params["file_list"][0]

        self.assertEqual(push_config_file_query_params["file_target_path"], self.GSE_ENVIRON_DIR)

        config_content = base64.b64decode(config_info["content"]).decode()

        self.assertTrue(settings.GSE_AGENT_HOME in config_content)
        self.assertTrue(f"{settings.GSE_AGENT_HOME}/{constants.PluginChildDir.OFFICIAL.value}" in config_content)

        super().tearDown()


class PushWindowsEnvironFilesTestCase(PushEnvironFilesTestCaseMixin, base.JobBaseTestCase):
    @classmethod
    def setup_obj_factory(cls):
        cls.obj_factory.host_os_type_options = [constants.OsType.WINDOWS]

    @classmethod
    def get_default_case_name(cls) -> str:
        return "推送环境变量文件成功（Windows）"

    def tearDown(self) -> None:
        record = self.job_api_mock_client.call_recorder.record

        # 该接口仅调用一次
        self.assertEqual(len(record[JobApi.push_config_file]), 1)
        push_config_file_query_params = record[JobApi.push_config_file][0].args[0]

        # 仅下发一个配置文件
        self.assertEqual(len(push_config_file_query_params["file_list"]), 2)

        for file in push_config_file_query_params["file_list"]:

            config_content = base64.b64decode(file["content"]).decode()

            self.assertTrue("c:\\\\gse" in config_content)
            self.assertTrue("47000" in config_content)
            self.assertTrue("c:\\\\gse\\\\plugins" in config_content)

        self.assertEqual(push_config_file_query_params["file_target_path"], self.GSE_ENVIRON_WIN_DIR)

        super().tearDown()
