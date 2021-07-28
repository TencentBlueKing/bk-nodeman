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

from django.test import TestCase
from mock import MagicMock, patch

from apps.backend.components.collections.agent import (
    ConfigurePolicyComponent,
    ConfigurePolicyService,
)
from apps.backend.tests.components.collections.agent import utils
from apps.node_man import models
from pipeline.component_framework.test import (
    ComponentTestCase,
    ComponentTestMixin,
    ExecuteAssertion,
    Patcher,
    ScheduleAssertion,
)

DESCRIPTION = "配置到Gse&Nginx的策略"

COMMON_INPUTS = utils.AgentTestObjFactory.inputs(
    attr_values={"description": DESCRIPTION, "bk_host_id": utils.BK_HOST_ID},
    # 主机信息保持和默认一致
    instance_info_attr_values={},
)

VPC_MOCK_CLIENT_PATH = "apps.backend.components.collections.agent.VpcClient"


class ConfigurePolicyTestService(ConfigurePolicyService):
    id = utils.JOB_TASK_PIPELINE_ID
    root_pipeline_id = utils.INSTANCE_RECORD_ROOT_PIPELINE_ID


class ConfigurePolicyTestComponent(ConfigurePolicyComponent):
    bound_service = ConfigurePolicyTestService


def describe_address_templates_func(*args, **kwargs):
    return [utils.TEST_IP] if args[0] == "True" else []


class VpcMockClient:
    def __init__(
        self,
        init_return=None,
        ip_templates_return=None,
        describe_address_templates_return=describe_address_templates_func,
    ):
        self.init = MagicMock(return_value=init_return)
        self.ip_templates = ip_templates_return
        self.describe_address_templates = MagicMock(side_effect=describe_address_templates_return)


class ConfigPoliceBaseTest(TestCase, ComponentTestMixin):

    VPC_SUCCESS_MOCK_CLIENT = VpcMockClient(init_return=(True, "success"), ip_templates_return=["True"])

    VPC_INIT_FAIL_MOCK_CLIENT = VpcMockClient(init_return=(False, "is not ok"))

    def setUp(self):
        utils.AgentTestObjFactory.init_db()
        # 填充登录IP
        models.Host.objects.filter(bk_host_id=utils.BK_HOST_ID).update(login_ip=utils.TEST_IP)

    def component_cls(self):
        return ConfigurePolicyTestComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="策略配置成功",
                inputs=COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=True, outputs={"polling_time": 0, "login_ip": utils.TEST_IP}
                ),
                schedule_assertion=[
                    ScheduleAssertion(
                        success=True, schedule_finished=True, outputs={"polling_time": 0, "login_ip": utils.TEST_IP}
                    ),
                ],
                execute_call_assertion=None,
                patchers=[Patcher(target=VPC_MOCK_CLIENT_PATH, return_value=self.VPC_SUCCESS_MOCK_CLIENT)],
            ),
            ComponentTestCase(
                name="VpcClient init失败",
                inputs=COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=True, outputs={"polling_time": 0, "login_ip": utils.TEST_IP}
                ),
                schedule_assertion=[
                    ScheduleAssertion(
                        success=False, schedule_finished=False, outputs={"polling_time": 0, "login_ip": utils.TEST_IP}
                    ),
                ],
                execute_call_assertion=None,
                patchers=[Patcher(target=VPC_MOCK_CLIENT_PATH, return_value=self.VPC_INIT_FAIL_MOCK_CLIENT)],
            ),
        ]

    def tearDown(self):
        # 状态查询
        self.assertTrue(models.JobTask.objects.filter(current_step__endswith=DESCRIPTION).exists())


class ConfigPoliceTimeOutFailTest(TestCase, ComponentTestMixin):

    VPC_MOCK_CLIENT = VpcMockClient(init_return=(True, "success"), ip_templates_return=["False"])

    POLLING_TIMEOUT_MOCK_PATH = "apps.backend.components.collections.agent.POLLING_TIMEOUT"

    def setUp(self):
        utils.AgentTestObjFactory.init_db()
        # 填充登录IP
        models.Host.objects.filter(bk_host_id=utils.BK_HOST_ID).update(login_ip=utils.TEST_IP)

        # 调整超时时间，便于测试
        self.polling_timeout = patch(self.POLLING_TIMEOUT_MOCK_PATH, 6 * 5)
        self.polling_timeout.start()

    def component_cls(self):
        return ConfigurePolicyTestComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="配置策略重试超时测试",
                inputs=COMMON_INPUTS,
                parent_data={},
                # 进入调度
                execute_assertion=ExecuteAssertion(
                    success=True, outputs={"polling_time": 0, "login_ip": utils.TEST_IP}
                ),
                schedule_assertion=[
                    ScheduleAssertion(
                        success=True, schedule_finished=False, outputs={"polling_time": 5, "login_ip": utils.TEST_IP}
                    ),
                    ScheduleAssertion(
                        success=True, schedule_finished=False, outputs={"polling_time": 10, "login_ip": utils.TEST_IP}
                    ),
                    ScheduleAssertion(
                        success=True, schedule_finished=False, outputs={"polling_time": 15, "login_ip": utils.TEST_IP}
                    ),
                    # 超时
                    ScheduleAssertion(
                        success=False, schedule_finished=True, outputs={"polling_time": 15, "login_ip": utils.TEST_IP}
                    ),
                ],
                execute_call_assertion=None,
                patchers=[Patcher(target=VPC_MOCK_CLIENT_PATH, return_value=self.VPC_MOCK_CLIENT)],
            )
        ]

    def tearDown(self):
        # 状态查询
        self.assertTrue(models.JobTask.objects.filter(current_step__endswith=DESCRIPTION).exists())
        self.polling_timeout.stop()
