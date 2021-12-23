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
import random
from unittest.mock import patch

from django.test import TestCase

from apps.node_man import constants as const
from apps.node_man.exceptions import (
    ApIDNotExistsError,
    HostIDNotExists,
    HostNotExists,
    IpInUsedError,
    PwdCheckError,
)
from apps.node_man.handlers.host import HostHandler
from apps.node_man.models import Host
from apps.node_man.tests.utils import (
    IP_REG,
    SEARCH_BUSINESS,
    MockClient,
    cmdb_or_cache_biz,
    create_cloud_area,
    create_host,
)


class TestHost(TestCase):
    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_host_list(self):
        number = 1000
        page_size = 10

        create_cloud_area(number, creator="admin")
        host_to_create, _, _ = create_host(number)

        # 测试正常查询
        hosts = HostHandler().list(
            {
                "pagesize": page_size,
                "page": 1,
                "only_ip": False,
                "status": ["RUNNING"],
                "version": [f"{random.randint(1, 10)}"],
                "bk_cloud_id": [[0, 1][random.randint(0, 1)]],
                "bk_biz_id": [random.randint(2, 7), random.randint(2, 7)],
                "extra_data": ["identity_info", "job_result"],
            },
            "admin",
        )
        for host in hosts["list"]:
            self.assertIn(host["bk_cloud_id"], [0, 1])
            self.assertIn(host["bk_biz_id"], [i for i in range(1, 10)])
        self.assertLessEqual(len(hosts["list"]), page_size)

    # 测试搜索查询
    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_host_list_search(self):
        number = 1000
        page_size = 10
        create_cloud_area(number, creator="admin")
        host_to_create, _, _ = create_host(number)
        hosts = HostHandler().list(
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
            },
            "admin",
        )
        for host in hosts["list"]:
            self.assertIn(host["bk_cloud_id"], [0, 1])
            self.assertIn(host["bk_biz_id"], [i for i in range(1, 10)])
        self.assertLessEqual(len(hosts["list"]), page_size)

    # 测试IP查询
    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_host_list_ip(self):
        number = 1000
        page_size = 10
        create_cloud_area(number, creator="admin")
        host_to_create, _, _ = create_host(number)
        hosts = HostHandler().list(
            {
                "pagesize": page_size,
                "page": 1,
                "only_ip": True,
                "bk_cloud_id": [[0, 1][random.randint(0, 1)]],
                "bk_biz_id": [random.randint(2, 7), random.randint(2, 7)],
            },
            "admin",
        )
        for host in hosts["list"]:
            self.assertRegex(host, IP_REG)
        self.assertLessEqual(len(hosts["list"]), page_size)

    # 测试精准查询
    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_host_acc_search(self):
        number = 1000
        page_size = 10
        create_cloud_area(number, creator="admin")
        host_to_create, _, _ = create_host(number)
        hosts = HostHandler().list(
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
            },
            "admin",
        )
        for host in hosts["list"]:
            self.assertRegex(host, IP_REG)
        self.assertLessEqual(len(hosts["list"]), page_size)

    # 测试running count
    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_host_list_span_page_running_count(self):
        number = 1000
        create_cloud_area(number, creator="admin")
        host_to_create, _, _ = create_host(number)
        bk_host_ids = [host.bk_host_id for host in host_to_create]
        result = HostHandler().list(
            {"exclude_hosts": bk_host_ids[:100], "pagesize": -1, "page": 1, "running_count": True}, "admin"
        )
        self.assertEqual(list(result.keys()), ["running_count", "no_permission_count"])

    # 测试跨页全选
    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_host_list_span_page(self):
        number = 1000
        create_cloud_area(number, creator="admin")
        host_to_create, _, _ = create_host(number)
        bk_host_ids = [host.bk_host_id for host in host_to_create]
        hosts = HostHandler().list(
            {"exclude_hosts": bk_host_ids[:100], "pagesize": -1, "page": 1, "only_ip": False, "running_count": False},
            "admin",
        )
        for host in hosts["list"]:
            self.assertIn(host["bk_cloud_id"], [0, 1])
            self.assertIn(host["bk_biz_id"], [biz["bk_biz_id"] for biz in SEARCH_BUSINESS])
        self.assertLessEqual(len(hosts["list"]), len(host_to_create) - 100)

    # 测试只需要IP
    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_host_list_only_ip(self):
        number = 1000
        page_size = -1
        create_cloud_area(number, creator="admin")
        host_to_create, _, _ = create_host(number)
        bk_host_ids = [host.bk_host_id for host in host_to_create]
        hosts = HostHandler().list(
            {"exclude_hosts": bk_host_ids[:100], "only_ip": True, "page": 1, "pagesize": page_size}, "admin"
        )
        for host in hosts["list"]:
            self.assertRegex(host, IP_REG)
        self.assertLessEqual(len(hosts["list"]), len(host_to_create) - 100)
        return hosts

    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_proxies(self):
        # 创建云区域10个
        number = 10
        bk_cloud_ids = create_cloud_area(number)

        # 创建主机
        for index, bk_cloud_id in enumerate(bk_cloud_ids):
            create_host(number=1, bk_host_id=index, bk_cloud_id=bk_cloud_id)

        # 大于1台
        create_host(
            number=1, bk_host_id=1111, bk_cloud_id=bk_cloud_ids[0], node_type="PAGENT", upstream_nodes=["1.1.1.1"]
        )
        create_host(
            number=1, bk_host_id=1112, bk_cloud_id=bk_cloud_ids[0], node_type="PAGENT", upstream_nodes=["1.1.1.1"]
        )

        # 检查结果
        for bk_cloud_id in bk_cloud_ids:
            result = HostHandler().proxies(bk_cloud_id)

            proxies_number = Host.objects.filter(bk_cloud_id=bk_cloud_id, node_type=const.NodeType.PROXY).count()

            self.assertEqual(len(result), proxies_number)

            for proxy in result:
                self.assertEqual(proxy["bk_cloud_id"], bk_cloud_id)

    # 测试主机更新
    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_host_update(self):
        number = 10
        create_cloud_area(number)
        host_to_create, identity_to_create, _ = create_host(number, bk_cloud_id=1)
        for host in host_to_create:
            update_data = {
                "bk_host_id": host.bk_host_id,
                "bk_cloud_id": host.bk_cloud_id,
                "ap_id": -1,
                "bk_biz_id": random.randint(2, 7),
                "os_type": "Linux",
                "inner_ip": host.inner_ip,
                "account": "root",
                "port": random.randint(3000, 4000),
                "bk_biz_scope": [random.randint(1, 132), random.randint(321, 342)],
                "auth_type": "PASSWORD",
                "password": f"{random.randint(1, 132) * random.randint(1, 132)}",
            }
            HostHandler().update_proxy_info(update_data)

        # HostID是否正确
        update_data = {
            "bk_host_id": 756876589576,
            "bk_cloud_id": 1,
            "ap_id": -1,
            "bk_biz_id": random.randint(2, 7),
            "os_type": "Linux",
            "inner_ip": "127.0.0.1",
            "account": "root",
            "port": random.randint(3000, 4000),
            "bk_biz_scope": [random.randint(1, 132), random.randint(321, 342)],
            "auth_type": "PASSWORD",
            "password": f"{random.randint(1, 132) * random.randint(1, 132)}",
        }
        self.assertRaises(HostIDNotExists, HostHandler().update_proxy_info, update_data)

        # 接入点是否存在
        update_data = {
            "bk_host_id": 1,
            "bk_cloud_id": 2,
            "ap_id": 123,
            "bk_biz_id": random.randint(2, 7),
            "os_type": "Linux",
            "account": "root",
            "port": random.randint(3000, 4000),
            "bk_biz_scope": [random.randint(1, 132), random.randint(321, 342)],
            "auth_type": "PASSWORD",
            "password": f"{random.randint(1, 132) * random.randint(1, 132)}",
        }
        self.assertRaises(ApIDNotExistsError, HostHandler().update_proxy_info, update_data)

        host_to_create, identity_to_create, _ = create_host(1, bk_host_id=5324523, auth_type="PASSWORD")
        # 认证信息校验测试
        update_data = {
            "bk_host_id": host_to_create[0].bk_host_id,
            "bk_cloud_id": 2,
            "bk_biz_id": random.randint(2, 7),
            "os_type": "Linux",
            "account": "root",
            "bk_biz_scope": [random.randint(1, 132), random.randint(321, 342)],
            "auth_type": "KEY",
            "password": "",
        }
        self.assertRaises(PwdCheckError, HostHandler().update_proxy_info, update_data)

        host_to_create, identity_to_create, _ = create_host(1, ip="127.0.0.1", bk_host_id=654645645)
        # Cloud信息的CMDB校验
        update_data = {"bk_host_id": host_to_create[0].bk_host_id, "bk_cloud_id": 5, "outer_ip": "127.0.0.1"}
        HostHandler().update_proxy_info(update_data)
        self.assertEqual(
            list(Host.objects.filter(bk_host_id=host_to_create[0].bk_host_id).values_list("bk_cloud_id", "inner_ip"))[
                0
            ],
            (5, "127.0.0.1"),
        )
        # 外网占用
        create_host(number=1, outer_ip="255.255.255.255", bk_cloud_id=5, bk_host_id=9999)
        update_data = {"bk_host_id": host_to_create[0].bk_host_id, "outer_ip": "255.255.255.255", "bk_cloud_id": 5}
        self.assertRaises(IpInUsedError, HostHandler().update_proxy_info, update_data)

        # 登录IP占用
        create_host(number=1, login_ip="255.255.255.255", bk_cloud_id=5, bk_host_id=10000)
        update_data = {"bk_host_id": host_to_create[0].bk_host_id, "login_ip": "255.255.255.255", "bk_cloud_id": 5}
        self.assertRaises(IpInUsedError, HostHandler().update_proxy_info, update_data)

    # 测试主机移除
    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    @patch("apps.node_man.handlers.cmdb.get_request_username", return_value="admin")
    def test_host_remove(self, *args, **kwargs):
        number = 1000
        create_cloud_area(number, creator="admin")
        host_to_create, identity_to_create, _ = create_host(number)
        proxies_ids = [host.bk_host_id for host in host_to_create if host.node_type == const.NodeType.PROXY]
        agent_or_pagent_ids = [host.bk_host_id for host in host_to_create if host.node_type != const.NodeType.PROXY]
        # 非跨页全选模式
        HostHandler().remove_host({"is_proxy": False, "bk_host_id": agent_or_pagent_ids})
        HostHandler().remove_host({"is_proxy": True, "bk_host_id": proxies_ids})

        # 跨页全选模式
        HostHandler().remove_host({"is_proxy": False, "exclude_hosts": agent_or_pagent_ids})
        HostHandler().remove_host({"is_proxy": True, "exclude_hosts": proxies_ids})

    # 测试无权限删除主机的情况
    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    @patch("apps.node_man.handlers.cmdb.get_request_username", return_value="admin")
    def test_host_remove_host_not_exist(self, *args, **kwargs):
        # 通过超管账号创建一批主机
        number = 10
        bk_cloud_ids = create_cloud_area(number, creator="admin")
        host_to_create, identity_to_create, _ = create_host(number)
        # 主机不存在
        self.assertRaises(
            HostNotExists,
            HostHandler().remove_host,
            {"is_proxy": False, "bk_cloud_id": bk_cloud_ids[0], "bk_host_id": [11]},
        )

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_ip_list(self):
        number = 10

        # 创建云区域
        create_cloud_area(number)

        # 创建Host
        host_to_create, identity_to_create, _ = create_host(number)

        # 测试
        result = HostHandler().ip_list([host.inner_ip for host in host_to_create])

        self.assertEqual(len(result), number)
