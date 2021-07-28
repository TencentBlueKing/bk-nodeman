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
from unittest.mock import patch

from django.test import TestCase

from apps.backend.components.collections.plugin import DebugComponent
from apps.backend.tests.components.collections.plugin import utils
from apps.utils.unittest.testcase import TestCaseLifeCycleMixin
from pipeline.component_framework.test import (
    ComponentTestCase,
    ComponentTestMixin,
    ExecuteAssertion,
    ScheduleAssertion,
)


class DebugTest(TestCase, TestCaseLifeCycleMixin, ComponentTestMixin):
    def setUp(self):
        self.ids = utils.PluginTestObjFactory.init_db()
        self.COMMON_INPUTS = utils.PluginTestObjFactory.inputs(
            attr_values={
                "description": "description",
                "bk_host_id": utils.BK_HOST_ID,
                "subscription_instance_ids": [self.ids["subscription_instance_record_id"]],
                "subscription_step_id": self.ids["subscription_step_id"],
            },
            # 主机信息保持和默认一致
            instance_info_attr_values={},
        )
        patch(utils.CMDB_CLIENT_MOCK_PATH, utils.CmdbClient).start()
        patch(utils.PLUGIN_CLIENT_MOCK_PATH, utils.JobMockClient).start()
        patch(utils.PLUGIN_MULTI_THREAD_PATH, utils.request_multi_thread_client).start()
        patch(utils.JOB_JOBAPI, utils.JobMockClient).start()
        patch(utils.JOB_MULTI_THREAD_PATH, utils.request_multi_thread_client).start()

        max_debug_polling_time_path = "apps.backend.components.collections.plugin.DebugService.MAX_DEBUG_POLLING_TIME"
        patch(max_debug_polling_time_path, 5).start()

        super().setUp()

    def component_cls(self):
        return DebugComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试debug原子",
                inputs=self.COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=True,
                    outputs={"succeeded_subscription_instance_ids": [self.ids["subscription_instance_record_id"]]},
                ),
                schedule_assertion=[
                    ScheduleAssertion(
                        success=True,
                        schedule_finished=False,
                        outputs={
                            "last_logs": "job_start\n",
                            "polling_time": 5,
                            "succeeded_subscription_instance_ids": [self.ids["subscription_instance_record_id"]],
                        },
                        callback_data=[],
                    ),
                    ScheduleAssertion(
                        success=True,
                        schedule_finished=False,
                        outputs={
                            "last_logs": "job_start\n",
                            "polling_time": 10,
                            "succeeded_subscription_instance_ids": [self.ids["subscription_instance_record_id"]],
                        },
                        callback_data=[],
                    ),
                    ScheduleAssertion(
                        success=True,
                        schedule_finished=True,
                        outputs={
                            "last_logs": "job_start\n",
                            "polling_time": 10,
                            "succeeded_subscription_instance_ids": [self.ids["subscription_instance_record_id"]],
                        },
                        callback_data=[],
                    ),
                ],
                execute_call_assertion=None,
            )
        ]
