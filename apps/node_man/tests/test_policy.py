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

from django.forms import model_to_dict

from apps.backend.subscription.constants import MAX_RETRY_TIME
from apps.node_man import constants
from apps.node_man.handlers.policy import PolicyHandler
from apps.node_man.models import (
    GsePluginDesc,
    Host,
    Packages,
    ProcessStatus,
    Subscription,
    SubscriptionStep,
)
from apps.node_man.tests.utils import (
    SEARCH_BUSINESS,
    TOPO_ORDER,
    NodeApi,
    cmdb_or_cache_biz,
    create_host,
)
from apps.utils.unittest.testcase import CustomBaseTestCase


def get_instances_by_scope(scope):
    host_id = scope["nodes"][0]["bk_host_id"]
    host = Host.objects.filter(bk_host_id=host_id)
    instance_key = f"host|instance|host|{host_id}"
    instances = {
        instance_key: {
            "host": list(host.values())[0],
            "scope": [{"ip": host.first().inner_ip, "bk_cloud_id": host.first().bk_cloud_id, "bk_supplier_id": 0}],
            "process": {},
            "service": None,
        }
    }

    return instances


def mock_batch_call(func, params_list, get_data):
    """
    mock掉并发接口为单线程接口
    并发接口会出现测试数据丢失情况
    """
    result = []
    for params in params_list:
        result.append(get_data(func(**params)))

    return result


class TestPolicy(CustomBaseTestCase):
    exempted_fields = ["id"]

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
            nodes=[{"bk_host_id": 0}, {"bk_host_id": 1}],
            name="2W",
            creator="admin",
            category=Subscription.CategoryType.POLICY,
            plugin_name=cls.plugin_obj.name,
            pid=1,
        )
        cls.subscription_obj.save()

        cls.select_pkg_infos = [
            {
                "id": 1,
                "version": "1.0",
                "os": constants.OsType.LINUX.lower(),
                "cpu_arch": constants.CpuType.x86_64,
                "project": cls.plugin_obj.name,
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

        cls.package_obj = Packages(
            id=1,
            pkg_name=f"{cls.plugin_obj.name}-{cls.select_pkg_infos[0]['version']}.tgz",
            version=cls.select_pkg_infos[0]["version"],
            module="gse_plugin",
            project=cls.plugin_obj.name,
            pkg_size=14425833,
            pkg_path="/data/plugin",
            md5="66b0b2614eeda53510f94412eb396499",
            pkg_mtime="2000-01-01: 09:30:00",
            pkg_ctime="2000-01-01: 09:30:00",
            location="127.0.0.1",
        )
        cls.package_obj.save()

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

    @patch("apps.backend.subscription.tasks.CmdbHandler.get_topo_order", lambda: TOPO_ORDER)
    @patch("apps.backend.subscription.tasks.tools.get_instances_by_scope", get_instances_by_scope)
    @patch("apps.backend.subscription.tools.request_multi_thread", mock_batch_call)
    def test_migrate_preview(self):
        host, process, identity = create_host(number=1)
        host[0].status = "NOT_INSTALLED"
        query_params = {
            "category": "policy",
            "steps": [
                {
                    "id": "processbeat",
                    "type": "PLUGIN",
                    "params": self.pkg_params_list,
                    "configs": self.select_pkg_infos,
                }
            ],
            "scope": {"object_type": "HOST", "node_type": "INSTANCE", "nodes": [{**host[0].__dict__}]},
        }

        # 验证变更动作
        result = PolicyHandler.migrate_preview(query_params)[0]
        self.assertEqual(result["action_id"], constants.JobType.MAIN_INSTALL_PLUGIN)

    def create_custom_hosts(self, number):
        """
        创建host和process数据
        """
        host, process, identity = create_host(number=number)
        ProcessStatus.objects.all().update(
            retry_times=MAX_RETRY_TIME + 1,
            source_id=self.subscription_obj.id,
            name=self.plugin_obj.name,
            is_latest=True,
        )

        return host, process, identity

    def create_custom_sub(self, process):
        """
        用于创建第二优先级的策略数据
        """
        subscription = {**model_to_dict(self.subscription_obj), "id": 999, "name": "sub_test"}
        proc = {**model_to_dict(process), "source_id": 999, "is_latest": False, "name": self.plugin_obj.name}
        ProcessStatus(**proc).save()
        Subscription(**subscription).save()

    @patch("common.api.NodeApi.run_subscription_task", NodeApi.run_subscription_task)
    @patch("apps.node_man.tools.policy.CmdbHandler.get_topo_order", lambda: TOPO_ORDER)
    def test_policy_operate(self):
        host, process, _ = self.create_custom_hosts(number=2)

        # 测试action为start
        result = PolicyHandler.policy_operate(self.subscription_obj.id, constants.PolicyOpType.START)
        self.assertIsInstance(result["job_id"], int)

        # 测试action为retry_abnormal
        result = PolicyHandler.policy_operate(self.subscription_obj.id, constants.PolicyOpType.RETRY_ABNORMAL)
        actions = result["param"]["actions"]
        self.assertEqual(actions, {self.plugin_obj.name: constants.JobType.MAIN_INSTALL_PLUGIN})

        # 测试action为STOP/STOP_AND_DELETE
        result = PolicyHandler.policy_operate(self.subscription_obj.id, constants.PolicyOpType.STOP)
        actions = result["param"]["actions"]
        self.assertEqual(actions, {self.plugin_obj.name: constants.JobType.MAIN_STOP_PLUGIN})

        # 测试action为delete(测试灰度策略删除)
        self.create_custom_sub(process[0])
        result = PolicyHandler.policy_operate(self.subscription_obj.id, constants.PolicyOpType.DELETE)
        actions = result["operate_results"][0]["param"]["actions"]
        self.assertEqual(actions, {self.plugin_obj.name: constants.JobType.MAIN_INSTALL_PLUGIN})

    @patch(
        "apps.node_man.handlers.host_v2.CmdbHandler.biz_id_name",
        lambda *args: {biz["bk_biz_id"]: biz["bk_biz_name"] for biz in SEARCH_BUSINESS},
    )
    @patch("apps.node_man.handlers.host_v2.CmdbHandler.get_topo_order", lambda: TOPO_ORDER)
    def test_rollback_preview(self):
        host, process, _ = self.create_custom_hosts(number=1)
        query_params = {"page": 1, "pagesize": 10, "scope": self.subscription_obj.scope}

        # 测试策略回滚，主机失去掌控
        result = PolicyHandler.rollback_preview(self.subscription_obj.id, query_params)
        self.assertEqual(result["list"][0]["target_policy"]["type"], constants.PolicyRollBackType.LOSE_CONTROL)

        # 测试策略回滚，第二优先级作为主策略
        self.create_custom_sub(process[0])
        result = PolicyHandler.rollback_preview(self.subscription_obj.id, query_params)
        self.assertEqual(result["list"][0]["target_policy"]["type"], constants.PolicyRollBackType.TRANSFER_TO_ANOTHER)

    @patch("apps.node_man.handlers.policy.concurrent.batch_call", mock_batch_call)
    def test_fetch_policy_abnormal_info(self):
        self.create_custom_hosts(number=2)
        policy_ids = [self.subscription_obj.id]

        # 测试非正常主机信息
        result = PolicyHandler.fetch_policy_abnormal_info(policy_ids)
        self.assertEqual(result[self.subscription_obj.id]["abnormal_host_count"], len(self.subscription_obj.nodes))
