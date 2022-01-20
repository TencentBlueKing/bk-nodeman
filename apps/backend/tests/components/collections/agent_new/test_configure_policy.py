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
import os
from typing import Dict, Optional

import mock
from tencentcloud.vpc.v20170312.models import (
    DescribeAddressTemplatesResponse,
    ModifyAddressTemplateAttributeResponse,
)

from apps.backend.components.collections.agent_new.components import (
    ConfigurePolicyComponent,
)
from apps.mock_data import api_mkd
from apps.mock_data import utils as mock_data_utils
from apps.node_man import models
from apps.node_man.handlers.security_group import (
    SopsSecurityGroupFactory,
    TencentVpcSecurityGroupFactory,
)
from pipeline.component_framework.test import (
    ComponentTestCase,
    ExecuteAssertion,
    ScheduleAssertion,
)

from . import utils


class ConfigurePolicyComponentBaseTest(utils.AgentServiceBaseTestCase):
    def component_cls(self):
        return ConfigurePolicyComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="无需配置策略",
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=bool(self.common_inputs["subscription_instance_ids"]),
                    outputs={"succeeded_subscription_instance_ids": self.common_inputs["subscription_instance_ids"]},
                ),
                schedule_assertion=[
                    ScheduleAssertion(
                        success=True,
                        schedule_finished=True,
                        outputs={
                            "succeeded_subscription_instance_ids": self.common_inputs["subscription_instance_ids"]
                        },
                    ),
                ],
                execute_call_assertion=None,
                patchers=[],
            ),
        ]


class SopsConfigurePolicyComponentBaseTest(ConfigurePolicyComponentBaseTest):
    SOPS_CLIENT_MOCK_PATH = "apps.node_man.handlers.security_group.SopsApi"

    create_task_result: int = None
    start_task_result: bool = None
    get_task_status_result: Optional[Dict] = None
    sops_mock_client: Optional[api_mkd.sops.utils.SOPSMockClient] = None

    @classmethod
    def structure_sops_mock_data(cls):
        """
        构造SOPS接口返回数据
        :return:
        """
        cls.create_task_result = 123
        cls.start_task_result = True
        cls.get_task_status_result = {"state": "FINISHED"}

    def init_mock_clients(self):
        self.sops_mock_client = api_mkd.sops.utils.SOPSMockClient(
            create_task_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.RETURN_VALUE.value, return_obj=self.create_task_result
            ),
            start_task_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.RETURN_VALUE.value, return_obj=self.start_task_result
            ),
            get_task_status_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.RETURN_VALUE.value,
                return_obj=self.get_task_status_result,
            ),
        )

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.structure_sops_mock_data()

    def setUp(self):
        models.GlobalSettings.set_config(
            models.GlobalSettings.KeyEnum.SECURITY_GROUP_TYPE.value, SopsSecurityGroupFactory.SECURITY_GROUP_TYPE
        )
        self.init_mock_clients()
        mock.patch(self.SOPS_CLIENT_MOCK_PATH, self.sops_mock_client).start()
        super().setUp()

    def cases(self):
        return [
            ComponentTestCase(
                name="通过标准运维配置策略",
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=bool(self.common_inputs["subscription_instance_ids"]),
                    outputs={
                        "add_ip_output": {"task_id": self.create_task_result},
                        "polling_time": 0,
                        "succeeded_subscription_instance_ids": self.common_inputs["subscription_instance_ids"],
                    },
                ),
                schedule_assertion=[
                    ScheduleAssertion(
                        success=True,
                        schedule_finished=True,
                        outputs={
                            "add_ip_output": {"task_id": self.create_task_result},
                            "polling_time": 0,
                            "succeeded_subscription_instance_ids": self.common_inputs["subscription_instance_ids"],
                        },
                    ),
                ],
                execute_call_assertion=None,
            ),
        ]


class MockVpcClient(mock_data_utils.BaseMockClient):
    """mock腾讯云vpc客户端"""

    class VpcClient(mock_data_utils.BaseMockClient):
        def __init__(self, *args, **kwargs):
            resp = DescribeAddressTemplatesResponse()
            resp.TotalCount = 1
            resp.AddressTemplateSet = [{"AddressSet": ["127.0.0.1"]}]
            self.DescribeAddressTemplates = self.generate_magic_mock(
                mock_data_utils.MockReturn(
                    return_type=mock_data_utils.MockReturnType.RETURN_VALUE.value, return_obj=resp
                )
            )
            resp = ModifyAddressTemplateAttributeResponse()
            resp.RequestId = "123"
            self.ModifyAddressTemplateAttribute = self.generate_magic_mock(
                mock_data_utils.MockReturn(
                    return_type=mock_data_utils.MockReturnType.RETURN_VALUE.value, return_obj=resp
                )
            )


class TencentVpcConfigurePolicyComponentBaseTest(ConfigurePolicyComponentBaseTest):
    TENCENT_VPC_MOCK_CLIENT_PATH = "apps.node_man.policy.tencent_vpc_client.vpc_client"

    def setUp(self):
        models.GlobalSettings.set_config(
            models.GlobalSettings.KeyEnum.SECURITY_GROUP_TYPE.value, TencentVpcSecurityGroupFactory.SECURITY_GROUP_TYPE
        )
        os.environ["TXY_SECRETID"] = "test_secret_id"
        os.environ["TXY_SECRETKEY"] = "test_secret_key"
        os.environ["TXY_IP_TEMPLATES"] = "test_template"
        mock.patch(self.TENCENT_VPC_MOCK_CLIENT_PATH, MockVpcClient).start()
        super().setUp()

    def cases(self):
        return [
            ComponentTestCase(
                name="通过腾讯云配置策略",
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=bool(self.common_inputs["subscription_instance_ids"]),
                    outputs={
                        "add_ip_output": {"ip_list": ["127.0.0.1", "127.0.0.1"]},
                        "polling_time": 0,
                        "succeeded_subscription_instance_ids": self.common_inputs["subscription_instance_ids"],
                    },
                ),
                schedule_assertion=[
                    ScheduleAssertion(
                        success=True,
                        schedule_finished=True,
                        outputs={
                            "add_ip_output": {"ip_list": ["127.0.0.1", "127.0.0.1"]},
                            "polling_time": 0,
                            "succeeded_subscription_instance_ids": self.common_inputs["subscription_instance_ids"],
                        },
                    ),
                ],
                execute_call_assertion=None,
            ),
        ]
