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

from apps.backend.components.collections.plugin import InitProcOperateScriptComponent
from apps.backend.tests.components.collections.plugin.test_install_package import (
    InstallPackageTest,
)
from pipeline.component_framework.test import (
    ComponentTestCase,
    ExecuteAssertion,
    ScheduleAssertion,
)


class InitProcOperateScriptTest(InstallPackageTest):
    def component_cls(self):
        return InitProcOperateScriptComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试初始化插件操作脚本",
                inputs=self.COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=True,
                    outputs={"succeeded_subscription_instance_ids": [self.ids["subscription_instance_record_id"]]},
                ),
                schedule_assertion=ScheduleAssertion(
                    success=True,
                    schedule_finished=True,
                    outputs={
                        "succeeded_subscription_instance_ids": [self.ids["subscription_instance_record_id"]],
                        "polling_time": 5,
                    },
                    callback_data=[],
                ),
                execute_call_assertion=None,
            )
        ]
