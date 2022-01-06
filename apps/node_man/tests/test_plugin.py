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

from django.test import TestCase

from apps.node_man import constants as const
from apps.node_man.handlers.plugin import PluginHandler
from apps.node_man.models import (
    Packages,
    PluginConfigTemplate,
    ProcControl,
    ProcessStatus,
    Subscription,
    SubscriptionTask,
)
from apps.node_man.tests.utils import (
    IP_REG,
    SEARCH_BUSINESS,
    MockClient,
    NodeApi,
    cmdb_or_cache_biz,
    create_cloud_area,
    create_host,
)


class TestPlugin(TestCase):
    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_plugin_list(self):
        number = 1000
        page_size = 10

        create_cloud_area(number, creator="admin")
        host_to_create, _, _ = create_host(number)

        # 测试正常查询
        hosts = PluginHandler.list(
            {
                "pagesize": page_size,
                "page": 1,
                "only_ip": False,
                "conditions": [{"key": "status", "value": ["RUNNING"]}, {"key": "basereport", "value": ["1.10"]}],
                "bk_cloud_id": [[0, 1][random.randint(0, 1)]],
                "bk_biz_id": [random.randint(2, 7), random.randint(2, 7)],
                "extra_data": ["identity_info", "job_result"],
                "detail": True,
            },
        )
        for host in hosts["list"]:
            self.assertIn(host["bk_cloud_id"], [0, 1])
            self.assertIn(host["bk_biz_id"], [i for i in range(1, 10)])
        self.assertLessEqual(len(hosts["list"]), page_size)

    # 测试搜索查询
    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_plugin_list_search(self):
        number = 10
        page_size = 20
        create_cloud_area(number, creator="admin")
        # 创建主机
        host_to_create, _, _ = create_host(number)

        # 测试分支
        create_host(number=1, bk_host_id=11)
        process_to_create = []
        process_to_create.append(
            ProcessStatus(
                bk_host_id=11,
                name="pluginplugin",
                proc_type=const.ProcType.PLUGIN,
                version=f"{random.randint(1, 10)}",
                status="RUNNING",
                source_type="default",
            )
        )
        process_to_create.append(
            ProcessStatus(
                bk_host_id=11,
                name="pluginplugin2",
                proc_type=const.ProcType.PLUGIN,
                version=f"{random.randint(1, 10)}",
                status="RUNNING",
                source_type="default",
            )
        )
        ProcessStatus.objects.bulk_create(process_to_create)
        PluginHandler.list({"pagesize": page_size, "page": 1, "only_ip": False, "detail": True})

        # 测试主分支
        hosts = PluginHandler.list(
            {
                "pagesize": page_size,
                "page": 1,
                "only_ip": False,
                "status": ["RUNNING"],
                "version": [f"{random.randint(1, 10)}"],
                "bk_biz_id": [random.randint(2, 7), random.randint(2, 7)],
                "conditions": [
                    {"key": "ip", "value": ["1.1.1.1"]},
                    {"key": "bk_cloud_id", "value": [0, 1]},
                    {"key": "query", "value": ["直连"]},
                ],
                "extra_data": ["identity_info", "job_result"],
                "detail": True,
            }
        )
        for host in hosts["list"]:
            self.assertIn(host["bk_cloud_id"], [0, 1])
            self.assertIn(host["bk_biz_id"], [i for i in range(1, 10)])
        self.assertLessEqual(len(hosts["list"]), page_size)

    # 测试IP查询
    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_plugin_list_ip(self):
        number = 1000
        page_size = 10
        create_cloud_area(number, creator="admin")
        host_to_create, _, _ = create_host(number)
        hosts = PluginHandler.list(
            {
                "pagesize": page_size,
                "page": 1,
                "only_ip": True,
                "bk_cloud_id": [[0, 1][random.randint(0, 1)]],
                "bk_biz_id": [random.randint(2, 7), random.randint(2, 7)],
            },
        )
        for host in hosts["list"]:
            self.assertRegex(host, IP_REG)
        self.assertLessEqual(len(hosts["list"]), page_size)

    # 测试精准查询
    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_plugin_acc_search(self):
        number = 1000
        page_size = 10
        create_cloud_area(number, creator="admin")
        host_to_create, _, _ = create_host(number)
        hosts = PluginHandler.list(
            {
                "pagesize": page_size,
                "page": 1,
                "conditions": [
                    {"key": "status", "value": ["未知"]},
                    {"key": "version", "value": ["1"]},
                    {"key": "os_type", "value": ["Linux"]},
                    {"key": "query", "value": "直连"},
                ],
                "bk_cloud_id": [[0, 1][random.randint(0, 1)]],
                "only_ip": False,
                "bk_biz_id": [random.randint(2, 7), random.randint(2, 7)],
                "detail": True,
            },
        )
        for host in hosts["list"]:
            self.assertRegex(host, IP_REG)
        self.assertLessEqual(len(hosts["list"]), page_size)

    # 测试跨页全选
    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_plugin_list_span_page(self):
        number = 1000
        create_cloud_area(number, creator="admin")
        host_to_create, _, _ = create_host(number)
        bk_host_ids = [host.bk_host_id for host in host_to_create]
        hosts = PluginHandler.list(
            {
                "exclude_hosts": bk_host_ids[:100],
                "pagesize": -1,
                "page": 1,
                "only_ip": False,
                "running_count": True,
                "detail": True,
            },
        )
        for host in hosts["list"]:
            self.assertIn(host["bk_cloud_id"], [0, 1])
            self.assertIn(host["bk_biz_id"], [biz["bk_biz_id"] for biz in SEARCH_BUSINESS])
        self.assertLessEqual(len(hosts["list"]), len(host_to_create) - 100)

    # 测试操作类
    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    @patch("common.api.NodeApi.create_subscription", NodeApi.create_subscription)
    def test_plugin_operate(self):
        # 创建host
        create_cloud_area(3)
        create_host(number=1, bk_cloud_id=0, bk_host_id=1, node_type="AGENT")
        # 执行任务
        PluginHandler.operate(
            {
                "job_type": "MAIN_START_PLUGIN",
                "bk_host_id": [1],
                "plugin_params_list": [{"name": "pluginplugin", "version": "latest"}],
            },
            "admin",
            True,
        )
        # 跨页全选
        PluginHandler.operate(
            {
                "job_type": "MAIN_START_PLUGIN",
                "plugin_params_list": [{"name": "pluginplugin", "version": "latest"}],
                "exclude_hosts": [],
            },
            "admin",
            True,
        )

    # 测试package获取
    def test_get_packages(self):
        Packages(
            **{
                "id": 2,
                "pkg_name": "basereport-10.1.12.tgz",
                "version": "10.1.12",
                "module": "gse_plugin",
                "project": "basereport",
                "pkg_size": 4561957,
                "pkg_path": "/data/bkee/miniweb/download/linux/x86_64",
                "md5": "046779753b6709635db0c861a1b0020e",
                "pkg_mtime": "2019-11-01 20:46:52.404139",
                "pkg_ctime": "2019-11-01 20:46:52.404139",
                "location": "http://x.x.x.x/download/linux/x86_64",
                "os": "linux",
                "cpu_arch": "x86_64",
            }
        ).save()
        self.assertEqual(len(PluginHandler.get_packages("basereport", "linux")), 1)

    # 测试主机状态获取
    def test_get_process_status(self):
        number = 100
        host_created, _, _ = create_host(number)
        host_ids = [host.bk_host_id for host in host_created]
        self.assertEqual(len(PluginHandler.get_process_status(host_ids)), number)

    # 测试主机状态获取
    @patch("common.api.NodeApi.create_subscription", NodeApi.create_subscription)
    def test_create_subscription(self):
        result = PluginHandler.create_subscription(
            job_type="MAIN_JOB_PLUGIN", nodes=[123, 123], name="basereport", version="latest", keep_config=True
        )
        self.assertIsInstance(result["subscription_id"], int)
        self.assertIsInstance(result["task_id"], int)

    def test_get_statistics(self):
        host_count = 5
        create_host(host_count)
        statistics = PluginHandler.get_statistics()
        actual_host_count = sum([h["host_count"] for h in statistics])
        self.assertEqual(actual_host_count, host_count)

    # 测试主机订阅任务查询
    def test_get_host_subscription_plugins(self):
        # 构造所需数据
        plugin_name = "exceptionbeat"
        version = "v1.0.0"
        package = Packages(
            id=1,
            pkg_name=f"{plugin_name}-{version}.tgz",
            version=version,
            module="gse_plugin",
            project=plugin_name,
            pkg_size=14425833,
            pkg_path="/data/plugin",
            md5="66b0b2614eeda53510f94412eb396499",
            pkg_mtime="2000-01-01: 09:30:00",
            pkg_ctime="2000-01-01: 09:30:00",
            location="127.0.0.1",
        )
        package.save()
        proc_control = ProcControl(
            module="gse_plugin",
            project=plugin_name,
            plugin_package_id=package.id,
            install_path="/plugin/install",
            log_path="/plugin/log",
            data_path="/plugin/data",
            pid_path="/plugin/pid",
        )
        proc_control.save()
        proc_config_template = PluginConfigTemplate(
            plugin_name=plugin_name,
            plugin_version=version,
            name=f"{plugin_name}.conf",
            version=version,
            format="yaml",
            file_path="etc",
            content="",
            is_release_version=1,
            creator="admin",
            create_time="2000-01-01 09:30:00",
            source_app_code="bk_nodeman",
        )
        proc_config_template.save()
        subscription = Subscription(
            object_type=Subscription.ObjectType.HOST,
            node_type=Subscription.NodeType.INSTANCE,
            bk_biz_scope=[SEARCH_BUSINESS[0]["bk_biz_id"], SEARCH_BUSINESS[1]["bk_biz_id"]],
            nodes=[{"bk_host_id": 0}, {"bk_host_id": 1}],
            name="2W",
            creator="admin",
            category=Subscription.CategoryType.POLICY,
            plugin_name=plugin_name,
            pid=1,
        )
        subscription.save()
        subscription_task = SubscriptionTask(
            subscription_id=subscription.id,
            scope={"nodes": subscription.nodes},
            actions={},
        )
        subscription_task.save()
        host_list, process_list, _ = create_host(number=2)
        ProcessStatus.objects.all().update(
            name=plugin_name, source_id=subscription.id, source_type="subscription", version=version
        )

        # 验证是否成功拿到了主机下的插件状态
        result = PluginHandler.get_host_subscription_plugins([host.bk_host_id for host in host_list])
        for host in host_list:
            self.assertTrue(result[host.bk_host_id][plugin_name]["subscription_statistics"]["running"])
