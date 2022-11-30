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
import importlib
from typing import List, Optional

import mock

from apps.backend.components.collections.agent_new import bind_host_agent
from apps.backend.components.collections.agent_new.components import (
    BindHostAgentComponent,
)
from apps.exceptions import ApiResultError
from apps.mock_data import api_mkd
from apps.mock_data import utils as mock_data_utils
from apps.node_man import models
from common.api import CCApi
from pipeline.component_framework.test import ComponentTestCase, ExecuteAssertion

from . import utils


class BindHostAgentTestCase(utils.AgentServiceBaseTestCase):
    CC_API_MOCK_PATHS: List[str] = ["apps.backend.components.collections.agent_new.bind_host_agent.CCApi"]

    cc_api_mock_client: Optional[api_mkd.cmdb.utils.CCApiMockClient] = None

    @staticmethod
    def bind_host_agent_func(query_params):
        return None

    @classmethod
    def adjust_test_data_in_db(cls):
        """
        调整DB中的测试数据
        :return:
        """

        host_id__agent_id_map = {
            host_obj.bk_host_id: f"{host_obj.bk_cloud_id}:{host_obj.inner_ip}" for host_obj in cls.obj_factory.host_objs
        }
        for sub_inst in cls.obj_factory.sub_inst_record_objs:
            bk_host_id = sub_inst.instance_info["host"]["bk_host_id"]
            sub_inst.instance_info["host"]["bk_agent_id"] = host_id__agent_id_map[bk_host_id]
        models.SubscriptionInstanceRecord.objects.bulk_update(
            cls.obj_factory.sub_inst_record_objs, fields=["instance_info"]
        )

    @classmethod
    def get_default_case_name(cls) -> str:
        return BindHostAgentComponent.name

    def init_mock_clients(self):
        self.cc_api_mock_client = api_mkd.cmdb.utils.CCApiMockClient(
            bind_host_agent_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.SIDE_EFFECT.value, return_obj=self.bind_host_agent_func
            )
        )

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        return self.common_inputs["subscription_instance_ids"]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.adjust_test_data_in_db()

    def setUp(self) -> None:
        self.init_mock_clients()
        super().setUp()

    def cases(self):
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=bool(self.fetch_succeeded_sub_inst_ids()),
                    outputs={"succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids()},
                ),
                schedule_assertion=None,
                execute_call_assertion=None,
            )
        ]

    def component_cls(self):
        importlib.reload(bind_host_agent)
        BindHostAgentComponent.bound_service = bind_host_agent.BindHostAgentService
        for cc_api_mock_path in self.CC_API_MOCK_PATHS:
            mock.patch(cc_api_mock_path, self.cc_api_mock_client).start()
        return BindHostAgentComponent

    def assert_in_teardown(self):
        record = self.cc_api_mock_client.call_recorder.record
        bind_host_agent_query_params = record[CCApi.bind_host_agent][0].args[0]
        self.assertEqual(len(bind_host_agent_query_params["list"]), len(self.fetch_succeeded_sub_inst_ids()))

    def tearDown(self) -> None:
        self.assert_in_teardown()
        super().tearDown()


class BindHostAgentFailedTestCase(BindHostAgentTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return f"{BindHostAgentComponent.name}：接口报错"

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        return []

    @staticmethod
    def bind_host_agent_func(query_params):
        raise ApiResultError("GSE Agent ID' Field regular check failed")

    def assert_in_teardown(self):
        record = self.cc_api_mock_client.call_recorder.record
        self.assertFalse(record[CCApi.bind_host_agent][0].is_success)


class AgentIdNotExistedTestCase(BindHostAgentTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return f"{BindHostAgentComponent.name}：bk_agent_id 不存在"

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        return []

    def assert_in_teardown(self):
        record = self.cc_api_mock_client.call_recorder.record
        self.assertEqual(len(record[CCApi.bind_host_agent]), 0)

    @classmethod
    def adjust_test_data_in_db(cls):
        for sub_inst in cls.obj_factory.sub_inst_record_objs:
            sub_inst.instance_info["host"].pop("bk_agent_id", None)
        models.SubscriptionInstanceRecord.objects.bulk_update(
            cls.obj_factory.sub_inst_record_objs, fields=["instance_info"]
        )
