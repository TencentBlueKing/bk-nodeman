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
from copy import deepcopy
from typing import List

import mock

from apps.backend.api.constants import POLLING_INTERVAL
from apps.backend.components.collections.agent_new.components import (
    InstallPluginsComponent,
)
from apps.mock_data import common_unit
from apps.node_man import models
from apps.node_man.tests.utils import NodeApi
from pipeline.component_framework.test import (
    ComponentTestCase,
    ExecuteAssertion,
    ScheduleAssertion,
)

from . import utils


class InstallPluginsTestCase(utils.AgentServiceBaseTestCase):
    CASE_NAME = "测试子订阅安装插件成功"
    NODEMAN_API_MOCK_PATHS = [
        "common.api.NodeApi",
        "apps.backend.components.collections.subsubscription.NodeApi",
        "apps.backend.components.collections.agent_new.install_plugins.NodeApi",
    ]
    SUBSCRIPTION_ID = common_unit.subscription.DEFAULT_SUBSCRIPTION_ID
    EXECUTE_RESULT = True
    IS_FINISHED = True
    SCHEDULE_RESULT = True
    EXTRA_OUTPUT = {}

    @staticmethod
    def init_plugins():
        models.GsePluginDesc.objects.create(**common_unit.plugin.GSE_PLUGIN_DESC_MODEL_DATA)
        models.Packages.objects.create(**common_unit.plugin.PACKAGES_MODEL_DATA)

    def start_patch(self):
        class CustomNodeApi(NodeApi):
            @staticmethod
            def create_subscription(params):
                return {"subscription_id": self.SUBSCRIPTION_ID}

            @staticmethod
            def get_subscription_task_status(params):
                task_results = NodeApi.get_subscription_task_status(params)
                for task_result in task_results:
                    task_result["instance_info"]["host"]["bk_host_id"] = self.obj_factory.bk_host_ids[0]
                return task_results

        for nodeman_api_mock_path in self.NODEMAN_API_MOCK_PATHS:
            mock.patch(nodeman_api_mock_path, CustomNodeApi).start()

    def setUp(self) -> None:
        self.init_plugins()
        super().setUp()
        self.start_patch()

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        return self.common_inputs["subscription_instance_ids"]

    def component_cls(self):
        return InstallPluginsComponent

    def cases(self):
        return [
            ComponentTestCase(
                name=self.CASE_NAME,
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=self.EXECUTE_RESULT,
                    outputs={
                        "subscription_ids": [self.SUBSCRIPTION_ID],
                        "all_subscription_ids": [self.SUBSCRIPTION_ID],
                        "succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids(),
                    },
                ),
                schedule_assertion=ScheduleAssertion(
                    success=self.SCHEDULE_RESULT,
                    schedule_finished=self.IS_FINISHED,
                    outputs={
                        "subscription_ids": [self.SUBSCRIPTION_ID],
                        "all_subscription_ids": [self.SUBSCRIPTION_ID],
                        "succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids(),
                        **self.EXTRA_OUTPUT,
                    },
                ),
                execute_call_assertion=None,
            )
        ]

    @classmethod
    def tearDownClass(cls):
        mock.patch.stopall()
        super().tearDownClass()


class InstallPluginsNoSubTestCase(InstallPluginsTestCase):
    CASE_NAME = "测试无需创建子订阅"

    @staticmethod
    def init_plugins():
        pass

    def cases(self):
        return [
            ComponentTestCase(
                name=self.CASE_NAME,
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=self.EXECUTE_RESULT,
                    outputs={
                        "subscription_ids": [],
                        "all_subscription_ids": [],
                        "succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids(),
                    },
                ),
                schedule_assertion=[],
            )
        ]


class InstallPluginsFailedTestCase(InstallPluginsTestCase):
    CASE_NAME = "测试子订阅安装插件失败"
    SUBSCRIPTION_ID = common_unit.subscription.FAILED_SUBSCRIPTION_ID
    SCHEDULE_RESULT = False
    EXTRA_OUTPUT = {"succeeded_subscription_instance_ids": []}


class InstallPluginsCreateSubTaskFailedTestCase(InstallPluginsTestCase):
    CASE_NAME = "测试子订阅任务创建失败"
    SUBSCRIPTION_ID = common_unit.subscription.CREATE_TASK_FAILED_SUBSCRIPTION_ID
    SCHEDULE_RESULT = False
    EXTRA_OUTPUT = {"succeeded_subscription_instance_ids": [], "subscription_ids": []}


class InstallPluginsRunningTestCase(InstallPluginsTestCase):
    CASE_NAME = "测试子订阅安装插件运行中"
    SUBSCRIPTION_ID = common_unit.subscription.RUNNING_SUBSCRIPTION_ID
    IS_FINISHED = False
    EXTRA_OUTPUT = {"polling_time": POLLING_INTERVAL}


class InstallPluginEnableFilter(InstallPluginsTestCase):
    CASE_NAME = "测试子订阅安装插件启用过滤"
    EXTRA_OUTPUT = {"succeeded_subscription_instance_ids": [], "subscription_ids": []}

    @staticmethod
    def init_plugins():
        gse_plugin_desc_model_data_copy = deepcopy(common_unit.plugin.GSE_PLUGIN_DESC_MODEL_DATA)
        gse_plugin_desc_model_data_copy.update({"is_ready": False})
        models.GsePluginDesc.objects.create(**gse_plugin_desc_model_data_copy)
        models.Packages.objects.create(**common_unit.plugin.PACKAGES_MODEL_DATA)

    def cases(self):
        return [
            ComponentTestCase(
                name=self.CASE_NAME,
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=self.EXECUTE_RESULT,
                    outputs={
                        "subscription_ids": [],
                        "all_subscription_ids": [],
                        "succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids(),
                    },
                ),
                schedule_assertion=[],
            )
        ]
