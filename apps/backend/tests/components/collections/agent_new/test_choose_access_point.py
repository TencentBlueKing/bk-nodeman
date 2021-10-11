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
from typing import Optional

from apps.backend.components.collections.agent import ChooseAccessPointComponent
from apps.mock_data import utils as mock_data_utils
from pipeline.component_framework.test import (
    ComponentTestCase,
    ExecuteAssertion,
    Patcher,
)

from . import utils


def ping_time_selector(*args, **kwargs):
    return 1.0


class ChooseAccessPointTestCase(utils.AgentServiceBaseTestCase):

    ssh_man_mock_client: Optional[utils.SshManMockClient] = None

    def setUp(self) -> None:
        super().setUp()
        self.ssh_man_mock_client = utils.SshManMockClient(
            ssh_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.RETURN_VALUE.value, return_obj="close"
            ),
            send_cmd_return_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.SIDE_EFFECT.value, return_obj=ping_time_selector
            ),
        )

    def component_cls(self):
        return ChooseAccessPointComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试Agent选择接入点成功：Linux主机",
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=True,
                    outputs={"succeeded_subscription_instance_ids": self.common_inputs["subscription_instance_ids"]},
                ),
                schedule_assertion=None,
                execute_call_assertion=None,
                patchers=[Patcher(target=self.SSH_MAN_MOCK_PATH, return_value=self.ssh_man_mock_client)],
            )
        ]
