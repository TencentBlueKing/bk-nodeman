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
from collections import ChainMap
from typing import Any, Callable, Dict, List, Optional

import mock

from apps.backend.api.constants import POLLING_INTERVAL
from apps.backend.components.collections.agent_new import components
from apps.mock_data import api_mkd
from apps.mock_data import utils as mock_data_utils
from apps.mock_data.api_mkd.cmdb import unit
from pipeline.component_framework.test import (
    ComponentTestCase,
    ExecuteAssertion,
    ScheduleAssertion,
)

from . import utils


class GetAgentIDTestCaseMixin:
    CLIENT_V2_MOCK_PATHS: List[str] = [
        "apps.backend.components.collections.agent_new.get_agent_id.client_v2",
    ]
    list_hosts_without_biz_func: Optional[Callable] = None
    cmdb_mock_client: Optional[api_mkd.cmdb.utils.CMDBMockClient] = None

    def init_mock_clients(self):
        self.cmdb_mock_client = api_mkd.cmdb.utils.CMDBMockClient(
            list_hosts_without_biz_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.SIDE_EFFECT.value,
                return_obj=self.list_hosts_without_biz_func,
            )
        )

    @classmethod
    def setup_obj_factory(cls):
        """设置 obj_factory"""
        cls.obj_factory.init_host_num = 10

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        return self.common_inputs["subscription_instance_ids"]

    def structure_common_inputs(self) -> Dict[str, Any]:
        common_inputs = super().structure_common_inputs()
        return {**common_inputs}

    def structure_common_outputs(self, polling_time: Optional[int] = None, **extra_kw) -> Dict[str, Any]:
        """
        构造原子返回数据
        :param polling_time: 轮询时间
        :param extra_kw: 额外需要添加的数据
        :return:
        """
        base_common_outputs = {
            "succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids(),
        }
        if polling_time is not None:
            base_common_outputs["polling_time"] = polling_time

        return dict(ChainMap(extra_kw, base_common_outputs))

    def component_cls(self):
        return components.GetAgentIDComponent

    def setUp(self) -> None:
        self.init_mock_clients()
        for client_v2_mock_path in self.CLIENT_V2_MOCK_PATHS:
            mock.patch(client_v2_mock_path, self.cmdb_mock_client).start()
        super().setUp()


class GetAgentIDFailedTestCase(GetAgentIDTestCaseMixin, utils.AgentServiceBaseTestCase):
    list_hosts_without_biz_func = unit.mock_list_host_without_biz_result

    @classmethod
    def get_default_case_name(cls) -> str:
        return "查询 Agent ID 失败"

    def cases(self):
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=bool(self.fetch_succeeded_sub_inst_ids()),
                    outputs=self.structure_common_outputs(polling_time=0),
                ),
                schedule_assertion=[
                    ScheduleAssertion(
                        success=True,
                        schedule_finished=False,
                        outputs=self.structure_common_outputs(polling_time=POLLING_INTERVAL),
                    )
                ],
                execute_call_assertion=None,
            )
        ]


class GetAgentIDSucceededTestCase(GetAgentIDTestCaseMixin, utils.AgentServiceBaseTestCase):
    list_hosts_without_biz_func = unit.mock_list_host_without_biz_with_agent_id_result

    @classmethod
    def get_default_case_name(cls) -> str:
        return "查询 Agent ID 成功"

    def cases(self):
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=bool(self.fetch_succeeded_sub_inst_ids()),
                    outputs=self.structure_common_outputs(polling_time=0),
                ),
                schedule_assertion=[
                    ScheduleAssertion(
                        success=True,
                        schedule_finished=True,
                        outputs=self.structure_common_outputs(polling_time=0),
                    )
                ],
                execute_call_assertion=None,
            )
        ]


class GetAgentIDTimeoutTestCase(GetAgentIDTestCaseMixin, utils.AgentServiceBaseTestCase):
    list_hosts_without_biz_func = unit.mock_list_host_without_biz_result

    @classmethod
    def get_default_case_name(cls) -> str:
        return "查询 Agent ID 超时"

    def setUp(self) -> None:
        super().setUp()
        mock.patch(
            "apps.backend.components.collections.agent_new.get_agent_id.POLLING_TIMEOUT",
            POLLING_INTERVAL - 1,
        ).start()

    def cases(self):
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=bool(self.fetch_succeeded_sub_inst_ids()),
                    outputs=self.structure_common_outputs(polling_time=0),
                ),
                schedule_assertion=[
                    ScheduleAssertion(
                        success=False,
                        schedule_finished=True,
                        outputs=self.structure_common_outputs(polling_time=0, succeeded_subscription_instance_ids=[]),
                    )
                ],
                execute_call_assertion=None,
            )
        ]
