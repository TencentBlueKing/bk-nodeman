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
from copy import deepcopy

from django.test import TestCase
from mock import patch

from apps.backend.api.constants import JobDataStatus, JobIPStatus
from apps.backend.components.collections.agent import (
    ReloadAgentConfigComponent,
    ReloadAgentConfigService,
)
from apps.backend.tests.components.collections.agent import utils
from apps.node_man import constants
from pipeline.component_framework.test import (
    ComponentTestCase,
    ComponentTestMixin,
    ExecuteAssertion,
    Patcher,
    ScheduleAssertion,
)

DESCRIPTION = "重载Agent配置"

COMMON_INPUTS = utils.AgentTestObjFactory.inputs(
    attr_values={"description": DESCRIPTION, "bk_host_id": utils.BK_HOST_ID}, instance_info_attr_values={}
)

COMMON_INPUTS.update(
    {
        # Job插件需要的inputs参数
        "job_client": {
            "bk_biz_id": utils.DEFAULT_BIZ_ID_NAME["bk_biz_id"],
            "username": utils.DEFAULT_CREATOR,
            "os_type": constants.OsType.LINUX,
        },
        "ip_list": [{"bk_cloud_id": constants.DEFAULT_CLOUD, "ip": utils.TEST_IP}],
        "context": "test",
        "script_timeout": 100,
        "script_param": "test",
    }
)


class ReloadAgentConfigTestService(ReloadAgentConfigService):
    id = utils.JOB_TASK_PIPELINE_ID
    root_pipeline_id = utils.INSTANCE_RECORD_ROOT_PIPELINE_ID


class ReloadAgentConfigTestComponent(ReloadAgentConfigComponent):
    bound_service = ReloadAgentConfigTestService


class ReloadAgentConfigSuccessTest(TestCase, ComponentTestMixin):

    JOB_MOCK_CLIENT = utils.JobMockClient(
        fast_execute_script_return=utils.JOB_INSTANCE_ID_METHOD_RETURN,
        get_job_instance_log_return=utils.JOB_GET_INSTANCE_LOG_RETURN,
    )

    def setUp(self):
        utils.AgentTestObjFactory.init_db()
        self.job_version = patch(utils.JOB_VERSION_MOCK_PATH, "V3")
        self.job_version.start()

    def tearDown(self):
        self.job_version.stop()

    def component_cls(self):
        return ReloadAgentConfigTestComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="重载Agent配置成功",
                inputs=COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=True,
                    outputs={"polling_time": 0, "job_instance_id": 10000},
                ),
                schedule_assertion=[
                    ScheduleAssertion(
                        success=True,
                        schedule_finished=True,
                        outputs={
                            "polling_time": 0,
                            "job_instance_id": 10000,
                            "task_result": {
                                "success": [
                                    {
                                        "ip": utils.TEST_IP,
                                        "bk_cloud_id": 0,
                                        "log_content": "success",
                                        "error_code": 0,
                                        "exit_code": 0,
                                    }
                                ],
                                "pending": [],
                                "failed": [],
                            },
                        },
                    ),
                ],
                execute_call_assertion=None,
                patchers=[Patcher(target=utils.JOB_CLIENT_MOCK_PATH, return_value=self.JOB_MOCK_CLIENT)],
            )
        ]


class ReloadAgentConfigTimeOutTest(ReloadAgentConfigSuccessTest):
    def setUp(self):
        super().setUp()
        self.polling_timeout = patch(utils.POLLING_TIMEOUT_MOCK_PATH, 2 * 5)
        self.polling_timeout.start()
        get_job_instance_log_running_return = deepcopy(utils.JOB_GET_INSTANCE_LOG_RETURN)
        get_job_instance_log_running_return["data"][0]["status"] = JobDataStatus.PENDING
        get_job_instance_log_running_return["data"][0]["is_finished"] = False
        get_job_instance_log_running_return["data"][0]["step_results"][0]["ip_status"] = JobIPStatus.RUNNING

        self.JOB_MOCK_CLIENT = utils.JobMockClient(
            fast_execute_script_return=utils.JOB_INSTANCE_ID_METHOD_RETURN,
            get_job_instance_log_return=get_job_instance_log_running_return,
        )
        self.common_pending_task_result = {
            "success": [],
            "pending": [
                {"ip": utils.TEST_IP, "bk_cloud_id": 0, "log_content": "success", "error_code": 0, "exit_code": 0}
            ],
            "failed": [],
        }

    def tearDown(self):
        self.polling_timeout.stop()

    def cases(self):
        return [
            ComponentTestCase(
                name="重载Agent配置超时",
                inputs=COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=True,
                    outputs={"polling_time": 0, "job_instance_id": 10000},
                ),
                schedule_assertion=[
                    ScheduleAssertion(
                        success=True,
                        schedule_finished=False,
                        outputs={
                            "polling_time": 5,
                            "job_instance_id": 10000,
                            "task_result": self.common_pending_task_result,
                        },
                    ),
                    ScheduleAssertion(
                        success=True,
                        schedule_finished=False,
                        outputs={
                            "polling_time": 10,
                            "job_instance_id": 10000,
                            "task_result": self.common_pending_task_result,
                        },
                    ),
                    ScheduleAssertion(
                        success=False,
                        schedule_finished=True,
                        outputs={
                            "polling_time": 10,
                            "job_instance_id": 10000,
                            "ex_data": "任务轮询超时",
                            "task_result": self.common_pending_task_result,
                        },
                    ),
                ],
                execute_call_assertion=None,
                patchers=[Patcher(target=utils.JOB_CLIENT_MOCK_PATH, return_value=self.JOB_MOCK_CLIENT)],
            )
        ]
