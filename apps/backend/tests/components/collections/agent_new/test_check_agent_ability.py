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

from apps.backend.components.collections.agent_new import components
from common.api import JobApi

from . import base
from .test_restart import RestartTestCase


class CheckAgentAbilityTestCase(RestartTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "测试Agent功能成功"

    def component_cls(self):
        return components.CheckAgentAbilityComponent

    def tearDown(self) -> None:
        record = self.job_api_mock_client.call_recorder.record
        fast_execute_script_query_params = record[JobApi.fast_execute_script][0].args[0]
        self.assertEqual(
            "c:\\gse\\agent\\bin\\gse_agent.exe --version",
            base64.b64decode(fast_execute_script_query_params["script_content"]).decode(),
        )


#
class PollingResultFailedTestCase(base.JobFailedBaseTestCase, CheckAgentAbilityTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "测试失败 Agent 功能失败"
