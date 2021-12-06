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
import random
from unittest.mock import patch

from apps.node_man import constants
from apps.node_man.handlers.policy import PolicyHandler
from apps.node_man.models import GsePluginDesc, Subscription, SubscriptionStep
from apps.node_man.tests.utils import SEARCH_BUSINESS, NodeApi, cmdb_or_cache_biz
from apps.utils.unittest.testcase import CustomBaseTestCase


class TestPolicy(CustomBaseTestCase):
    EXEMPTED_FIELDS = ["id"]

    @classmethod
    def setUpTestData(cls):
        cls.plugin_obj = GsePluginDesc(
            name="processbeat",
            description="description",
            source_app_code="nodeman",
            category=constants.CategoryType.official,
        )
        cls.plugin_obj.save()
        cls.subscription_obj = Subscription(
            object_type=Subscription.ObjectType.HOST,
            node_type=Subscription.NodeType.INSTANCE,
            bk_biz_scope=[SEARCH_BUSINESS[0]["bk_biz_id"], SEARCH_BUSINESS[1]["bk_biz_id"]],
            name="2W",
            creator="admin",
            category=Subscription.CategoryType.POLICY,
            plugin_name=cls.plugin_obj.name,
        )
        cls.subscription_obj.save()

        cls.select_pkg_infos = [
            {
                "id": 1,
                "version": "1.0",
                "os": constants.OsType.LINUX.lower(),
                "cpu_arch": constants.CpuType.x86_64,
                "config_templates": [
                    {
                        "id": 595,
                        "version": "1",
                        "is_main": True,
                        "name": "processbeat.conf",
                    }
                ],
            }
        ]
        cls.pkg_params_list = [
            {"context": {}, "os_type": constants.OsType.LINUX.lower(), "cpu_arch": constants.CpuType.x86_64}
        ]

        cls.subscription_step_obj = SubscriptionStep(
            subscription_id=cls.subscription_obj.id,
            index=1,
            step_id=cls.plugin_obj.name,
            type=constants.SubStepType.PLUGIN,
            config={"details": cls.select_pkg_infos},
            params={"details": cls.pkg_params_list},
        )
        cls.subscription_step_obj.save()

        super().setUpTestData()

    def setUp(self) -> None:
        pass

    def test_retrieve_policy(self):
        policy_info = PolicyHandler.policy_info(policy_id=self.subscription_obj.id)

        policy_info_from_db = (
            Subscription.objects.filter(id=self.subscription_obj.id)
            .values("id", "name", "enable", "category", "plugin_name", "bk_biz_scope", "pid", "bk_biz_id")
            .first()
        )

        self.assertDataStructure(
            actual_data=policy_info,
            expected_data={
                **policy_info_from_db,
                "scope": {
                    "bk_biz_id": None,
                    "object_type": self.subscription_obj.object_type,
                    "node_type": self.subscription_obj.node_type,
                    "nodes": self.subscription_obj.nodes,
                },
                "plugin_info": {
                    "id": self.plugin_obj.id,
                    "name": self.plugin_obj.name,
                    "description": self.plugin_obj.description,
                    "source_app_code": self.plugin_obj.source_app_code,
                    "category": constants.CATEGORY_DICT[self.plugin_obj.category],
                    "deploy_type": self.plugin_obj.deploy_type,
                },
                "steps": [
                    {
                        "id": self.subscription_step_obj.step_id,
                        "type": self.subscription_step_obj.type,
                        "configs": self.select_pkg_infos,
                        "params": self.pkg_params_list,
                    }
                ],
            },
        )

    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("common.api.NodeApi.subscription_search_policy", NodeApi.subscription_search_policy)
    def test_search_policy(self):
        result = PolicyHandler.search_deploy_policy(
            query_params={
                "bk_biz_ids": self.subscription_obj.bk_biz_scope,
                "conditions": [],
                "only_root": True,
                "page": 1,
                "pagesize": 20,
            }
        )
        self.assertEqual(len(result["list"]), 1)

    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    def test_fetch_policy_topo(self):
        policy_topo = PolicyHandler.fetch_policy_topo(bk_biz_ids=[SEARCH_BUSINESS[0]["bk_biz_id"]])
        self.assertDataStructure(
            policy_topo,
            [
                {
                    "id": self.plugin_obj.name,
                    "name": self.plugin_obj.name,
                    "type": "plugin",
                    "children": [
                        {
                            "id": self.subscription_obj.id,
                            "name": self.subscription_obj.name,
                            "type": Subscription.CategoryType.POLICY,
                        }
                    ],
                }
            ],
        )

    def test_selected_preview(self):
        result = PolicyHandler.selected_preview(
            query_params={"policy_id": self.subscription_obj.id, "page": 1, "pagesize": 50, "with_hosts": True}
        )
        self.assertDataStructure(
            result,
            {
                "total": 0,
                "list": [],
                "agent_status_count": {"total": 0, "RUNNING": 0, "NOT_INSTALLED": 0, "TERMINATED": 0},
            },
        )

    @patch("apps.node_man.handlers.policy.CmdbHandler.check_biz_permission", lambda *args: None)
    @patch("common.api.NodeApi.create_subscription", NodeApi.create_subscription)
    def test_create_policy(self):
        result = PolicyHandler.create_deploy_policy(
            create_data={
                "name": "test",
                "scope": {
                    "object_type": "HOST",
                    "node_type": "INSTANCE",
                    "nodes": [
                        {
                            "bk_cloud_id": 0,
                            "bk_biz_id": 1,
                            "bk_host_id": random.randint(100, 10000),
                            "os_type": "LINUX",
                        }
                    ],
                },
                "steps": [
                    {
                        "id": "basereport",
                        "type": "PLUGIN",
                        "configs": [
                            {
                                "cpu_arch": "x86_64",
                                "creator": "admin",
                                "config_templates": [{}],
                                "version": "10.7.33",
                                "os": "linux",
                                "id": random.randint(100, 10000),
                            }
                        ],
                        "params": [{"cpu_arch": "x86_64", "os_type": "linux", "context": {}}],
                    }
                ],
            }
        )
        self.assertIsInstance(result["job_id"], int)
        self.assertIsInstance(result["subscription_id"], int)
        self.assertIsInstance(result["task_id"], int)

    @patch("apps.node_man.handlers.policy.CmdbHandler.check_biz_permission", lambda *args: None)
    @patch("common.api.NodeApi.subscription_update", NodeApi.subscription_update)
    def test_update_policy(self):
        result = PolicyHandler.update_policy(
            update_data={
                "scope": {
                    "object_type": "HOST",
                    "node_type": "INSTANCE",
                    "nodes": [
                        {
                            "bk_biz_id": 1,
                            "bk_host_id": 4,
                            "os_type": "LINUX",
                        }
                    ],
                },
                "steps": [
                    {
                        "id": "basereport",
                        "type": "PLUGIN",
                        "configs": [
                            {
                                "cpu_arch": "x86_64",
                                "creator": "admin",
                                "project": "basereport",
                                "config_templates": [{}],
                                "os": "linux",
                                "id": 64,
                            }
                        ],
                        "params": [{"cpu_arch": "x86_64", "os_type": "linux", "context": {}}],
                    }
                ],
            },
            policy_id=self.subscription_obj.id,
        )
        self.assertIsInstance(result["job_id"], int)
        self.assertIsInstance(result["subscription_id"], int)
        self.assertIsInstance(result["task_id"], int)

    @patch("common.api.NodeApi.plugin_retrieve", NodeApi.plugin_retrieve)
    def test_upgrade_preview(self):
        result = PolicyHandler.upgrade_preview(policy_id=self.subscription_obj.id)
        self.assertEqual(
            result,
            [
                {
                    "cpu_arch": "x86_64",
                    "os": "linux",
                    "latest_version": "1.11.36",
                    "current_version_list": [
                        {"cpu_arch": "x86_64", "os": "linux", "current_version": "1.0", "nodes_number": 0}
                    ],
                    "is_latest": False,
                    "version_scenario": "myprocessbeat: 主机进程信息采集器 - V1.11.36 \n 该版本支持蓝鲸监控",
                }
            ],
        )

    @patch("common.api.NodeApi.plugin_retrieve", NodeApi.plugin_retrieve)
    def test_plugin_preselection(self):
        PolicyHandler.plugin_preselection(
            plugin_id=self.plugin_obj.id,
            scope={
                "object_type": "HOST",
                "node_type": "INSTANCE",
                "nodes": [
                    {
                        "bk_biz_id": 1,
                        "bk_host_id": 4,
                        "os_type": "LINUX",
                    }
                ],
            },
        )
