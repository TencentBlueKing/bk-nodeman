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
from typing import Any, Dict, List

from apps.backend.components.collections.agent_new import components
from apps.mock_data import common_unit
from apps.node_man import constants
from common.api import JobApi

from . import base, utils


class WindowsAgentTestObjFactory(utils.AgentTestObjFactory):
    def structure_instance_host_info_list(self) -> List[Dict[str, Any]]:
        """
        构造Agent安装目标实例，如需修改测试样例，可以继承该类，覆盖该方法
        :return:
        """
        instance_host_info_list = super().structure_instance_host_info_list()
        # 改用 Windows
        os_type = constants.OsType.WINDOWS
        for instance_host_info in instance_host_info_list:
            instance_host_info.update(
                os_type=os_type, bk_os_type=constants.BK_OS_TYPE[common_unit.host.HOST_MODEL_DATA["os_type"]]
            )
        return instance_host_info_list


class RestartTestCase(base.JobBaseTestCase):
    OBJ_FACTORY_CLASS = WindowsAgentTestObjFactory

    @classmethod
    def get_default_case_name(cls) -> str:
        return "重启成功"

    def component_cls(self):
        return components.RestartComponent

    def tearDown(self) -> None:
        record = self.job_api_mock_client.call_recorder.record
        fast_execute_script_query_params = record[JobApi.fast_execute_script][0].args[0]
        self.assertEqual(
            "c:\\gse\\agent\\bin\\gsectl.bat restart",
            base64.b64decode(fast_execute_script_query_params["script_content"]).decode(),
        )
        super().tearDown()


class SkipPollingResultTestCase(base.JobSkipPollingResultTestCase, RestartTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "重启成功: 跳过作业平台任务结果等待"
