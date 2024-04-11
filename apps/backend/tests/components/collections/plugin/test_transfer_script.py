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
from mock.mock import patch

from apps.backend.components.collections.plugin import TransferScriptComponent
from apps.backend.tests.components.collections.plugin.test_transfer_package import (
    TransferPackageTest,
)
from apps.backend.tests.components.collections.plugin.utils import JOB_INSTANCE_ID
from apps.node_man import constants, models
from pipeline.component_framework.test import (
    ComponentTestCase,
    ExecuteAssertion,
    ScheduleAssertion,
)


class TransferLinuxScriptTest(TransferPackageTest):
    def component_cls(self):
        return TransferScriptComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试脚本分发",
                inputs={**self.COMMON_INPUTS, **{"op_types": [constants.GseOpType.STOP, constants.GseOpType.START]}},
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


class TransferAixScriptTest(TransferLinuxScriptTest):
    def setUp(self):
        super().setUp()
        models.Host.objects.all().update(os_type=constants.OsType.AIX)


class TransferWindowsScriptTest(TransferLinuxScriptTest):
    def setUp(self):
        super().setUp()
        models.Host.objects.all().update(os_type=constants.OsType.WINDOWS)


class TransferFileToTmpDirWithLinux(TransferLinuxScriptTest):
    def test_component(self):
        with patch(
            "apps.backend.tests.components.collections.plugin.utils.JobMockClient.fast_transfer_file"
        ) as fast_transfer_file:
            fast_transfer_file.return_value = {
                "job_instance_name": "API Quick Distribution File1521101427176",
                "job_instance_id": JOB_INSTANCE_ID,
            }
            super().test_component()
            self.assertEqual(
                f"/tmp/plugin_scripts_sub_{self.ids['subscription_id']}",
                fast_transfer_file.call_args[0][0]["file_target_path"],
            )


class TransferFileToTmpDirWithAix(TransferAixScriptTest, TransferFileToTmpDirWithLinux):
    def setUp(self):
        super(TransferAixScriptTest, self).setUp()

    def test_component(self):
        super(TransferFileToTmpDirWithLinux, self).test_component()


class TransferFileToTmpDirWithWindows(TransferWindowsScriptTest):
    def test_component(self):
        with patch(
            "apps.backend.tests.components.collections.plugin.utils.JobMockClient.fast_transfer_file"
        ) as fast_transfer_file:
            fast_transfer_file.return_value = {
                "job_instance_name": "API Quick Distribution File1521101427176",
                "job_instance_id": JOB_INSTANCE_ID,
            }
            super().test_component()
            self.assertEqual(
                "c:\\gse\\plugins\\bin",
                fast_transfer_file.call_args[0][0]["file_target_path"],
            )
