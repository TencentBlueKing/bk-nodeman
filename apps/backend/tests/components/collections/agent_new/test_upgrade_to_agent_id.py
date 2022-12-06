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
from typing import Callable, Dict, List

import mock

from apps.adapters.api import gse
from apps.backend.components.collections.agent_new.components import (
    UpgradeToAgentIDComponent,
)
from apps.mock_data import api_mkd
from apps.mock_data import utils as mock_data_utils
from apps.node_man import models
from env.constants import GseVersion
from pipeline.component_framework.test import ComponentTestCase, ExecuteAssertion

from . import utils


class UpgradeToAgentIDTestCaseMixin:
    GSE_API_MOCK_PATHS: List[str] = ["apps.backend.components.collections.agent_new.upgrade_to_agent_id.GseApiHelper"]
    GSE_VERSION = GseVersion.V2.value
    upgrade_to_agent_id_func: Callable[[Dict], Dict] = lambda: {"success": [], "failed": []}

    @classmethod
    def setup_obj_factory(cls):
        """设置 obj_factory"""
        cls.obj_factory.init_host_num = 5

    @classmethod
    def get_default_case_name(cls) -> str:
        return UpgradeToAgentIDComponent.name

    @classmethod
    def adjust_test_data_in_db(cls):
        """
        调整DB中的测试数据
        :return:
        """
        for host_obj in cls.obj_factory.host_objs:
            host_obj.bk_agent_id = f"{host_obj.bk_cloud_id}:{host_obj.inner_ip}"
        models.Host.objects.bulk_update(cls.obj_factory.host_objs, fields=["bk_agent_id"])

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.adjust_test_data_in_db()

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        return self.common_inputs["subscription_instance_ids"]

    def component_cls(self):
        return UpgradeToAgentIDComponent

    def init_mock_clients(self):
        self.gse_api_mock_client = api_mkd.gse.utils.GseApiMockClient(
            v2_proc_upgrade_to_agent_id_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.SIDE_EFFECT.value, return_obj=self.upgrade_to_agent_id_func
            )
        )

    def setUp(self) -> None:
        self.init_mock_clients()
        for gse_api_mock_path in self.GSE_API_MOCK_PATHS:
            mock.patch(
                gse_api_mock_path,
                gse.get_gse_api_helper(self.GSE_VERSION)(
                    version=self.GSE_VERSION, gse_api_obj=self.gse_api_mock_client
                ),
            ).start()
        super().setUp()


class UpgradeToAgentIDSuccessTestCase(UpgradeToAgentIDTestCaseMixin, utils.AgentServiceBaseTestCase):
    @staticmethod
    def upgrade_to_agent_id_func(params):
        return {
            "success": [f'{host_info["bk_cloud_id"]}:{host_info["ip"]}' for host_info in params["hosts"]],
            "failed": [],
        }

    @classmethod
    def get_default_case_name(cls) -> str:
        return "升级Agent-ID全部成功"

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


class UpgradeToAgentIDFailedTestCase(UpgradeToAgentIDTestCaseMixin, utils.AgentServiceBaseTestCase):
    @staticmethod
    def upgrade_to_agent_id_func(params):
        return {
            "success": [],
            "failed": [f'{host_info["bk_cloud_id"]}:{host_info["ip"]}' for host_info in params["hosts"]],
        }

    @classmethod
    def get_default_case_name(cls) -> str:
        return "升级Agent-ID全部失败"

    def cases(self):
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=False,
                    outputs={"succeeded_subscription_instance_ids": []},
                ),
                schedule_assertion=None,
                execute_call_assertion=None,
            )
        ]


class UpgradeToAgentIDHalfSuccessTestCase(UpgradeToAgentIDTestCaseMixin, utils.AgentServiceBaseTestCase):
    @staticmethod
    def upgrade_to_agent_id_func(params):
        hosts = sorted(params["hosts"], key=lambda host: host["ip"])
        # mock 前一半的主机为失败，后一半为成功
        half_index = int(len(hosts) / 2)
        return {
            "success": [f'{host_info["bk_cloud_id"]}:{host_info["ip"]}' for host_info in hosts[:half_index]],
            "failed": [f'{host_info["bk_cloud_id"]}:{host_info["ip"]}' for host_info in hosts[half_index:]],
        }

    @classmethod
    def get_default_case_name(cls) -> str:
        return "升级Agent-ID部分成功部分失败"

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        # 最终成功的订阅实例只有前一半
        return self.common_inputs["subscription_instance_ids"][: int(self.obj_factory.init_host_num / 2)]

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


class UpgradeToAgentIDWithV1GseTestCase(UpgradeToAgentIDTestCaseMixin, utils.AgentServiceBaseTestCase):
    GSE_VERSION = GseVersion.V1.value

    @classmethod
    def get_default_case_name(cls) -> str:
        return "V1 GSE API 无 upgrade_to_agent_id，执行失败"

    def cases(self):
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=False,
                    outputs={},
                ),
                schedule_assertion=None,
                execute_call_assertion=None,
            )
        ]
