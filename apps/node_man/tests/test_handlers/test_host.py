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
                "return_field": random.choice(["inner_ip", "inner_ipv6"]),
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
        self.assertEqual(list(result.keys()), ["running_count", "no_permission_count", "manual_statistics"])

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
            {
                "exclude_hosts": bk_host_ids[:100],
                "only_ip": True,
                "page": 1,
                "pagesize": page_size,
                "return_field": random.choice(["inner_ip", "inner_ipv6"]),
            },
            "admin",
        )
        for host in hosts["list"]:
            self.assertRegex(host, IP_REG)
        self.assertLessEqual(len(hosts["list"]), len(host_to_create) - 100)
        return hosts

    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_proxies(self):
        # 创建管控区域10个
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

        # 修改登录IP(自身外网IP已存在的情况)
        host_to_create, identity_to_create, _ = create_host(
            number=1, outer_ip="255.255.254", login_ip="255.255.255", bk_cloud_id=5, bk_host_id=10001
        )
        update_data = {"bk_host_id": host_to_create[0].bk_host_id, "login_ip": "255.255.254", "bk_cloud_id": 5}
        self.assertEqual(HostHandler().update_proxy_info(update_data), None)

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_ip_list(self):
        number = 10

        # 创建管控区域
        create_cloud_area(number)

        # 创建Host
        host_to_create, identity_to_create, _ = create_host(number)

        # 测试
        result = HostHandler.get_host_infos_gby_ip_key(
            [host.inner_ip for host in host_to_create], const.CmdbIpVersion.V4.value
        )

        self.assertEqual(len(result), number)

    # 测试精准(BT节点探测,数据压缩, status)查询
    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_accurate_conditions(self):
        number = 1000
        page_size = 10
        create_cloud_area(number, creator="admin")
        host_to_create, _, _ = create_host(number)
        hosts = HostHandler().list(
            {
                "pagesize": page_size,
                "page": 1,
                "conditions": [
                    {"key": "status", "value": ["RUNNING", "TERMINATED", "NOT_INSTALLED"]},
                    {"key": "bt_node_detection", "value": [0, 1]},
                    {"key": "enable_compression", "value": ["True", "False"]},
                ],
                "bk_cloud_id": [[0, 1][random.randint(0, 1)]],
                "only_ip": False,
                "bk_biz_id": [random.randint(27, 39), random.randint(27, 39)],
                "extra_data": ["identity_info", "job_result"],
            },
            "admin",
        )
        for host_ip in hosts["list"]:
            self.assertRegex(host_ip["inner_ip"], IP_REG)
        self.assertLessEqual(len(hosts["list"]), page_size)

    # 测试管控区域:IP、version、IP查询; 因创建主机的IP具有随机性，无法进行准确校验，以空数据作为校验的标准
    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_bk_cloud_ip(self):
        number = 1000
        page_size = 10
        create_cloud_area(number, creator="admin")
        host_to_create, _, _ = create_host(number)
        hosts = HostHandler().list(
            {
                "pagesize": page_size,
                "page": 1,
                "conditions": [
                    {"key": "version", "value": ["1"]},
                    {"key": "ip", "value": ["1.1.1.1"]},
                    {"key": "bk_cloud_ip", "value": ["0:1.1.1.1"]},
                ],
                "bk_cloud_id": [[0, 1][random.randint(0, 1)]],
                "only_ip": False,
                "bk_biz_id": [random.randint(27, 39), random.randint(27, 39)],
                "extra_data": ["identity_info", "job_result"],
            },
            "admin",
        )
        for host_ip in hosts["list"]:
            self.assertRegex(host_ip, IP_REG)
        self.assertLessEqual(len(hosts["list"]), page_size)

    # 启用数据压缩
    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_only_enable_compression(self):
        number = 100
        page_size = 10
        create_cloud_area(number, creator="admin")
        host_to_create, _, _ = create_host(number)
        hosts = HostHandler().list(
            {
                "pagesize": page_size,
                "page": 1,
                "conditions": [
                    {"key": "enable_compression", "value": ["True"]},
                ],
                "bk_cloud_id": [[0, 1][random.randint(0, 1)]],
                "only_ip": False,
                "bk_biz_id": [random.randint(27, 39), random.randint(27, 39)],
                "extra_data": ["identity_info", "job_result"],
            },
            "admin",
        )
        for host_ip in hosts["list"]:
            self.assertRegex(host_ip, IP_REG)
        self.assertLessEqual(len(hosts["list"]), page_size)

    # 停用数据压缩
    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_only_disable_compression(self):
        number = 100
        page_size = 10
        create_cloud_area(number, creator="admin")
        host_to_create, _, _ = create_host(number)
        hosts = HostHandler().list(
            {
                "pagesize": page_size,
                "page": 1,
                "conditions": [{"key": "enable_compression", "value": ["False"]}],
                "bk_cloud_id": [[0, 1][random.randint(0, 1)]],
                "only_ip": False,
                "bk_biz_id": [random.randint(27, 39), random.randint(27, 39)],
                "extra_data": ["identity_info", "job_result"],
            },
            "admin",
        )
        for host_ip in hosts["list"]:
            self.assertRegex(host_ip["inner_ip"], IP_REG)
        self.assertLessEqual(len(hosts["list"]), page_size)

    # 启用BT节点探测
    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_only_enable_bt_node_detection(self):
        number = 100
        page_size = 10
        create_cloud_area(number, creator="admin")
        host_to_create, _, _ = create_host(number)
        hosts = HostHandler().list(
            {
                "pagesize": page_size,
                "page": 1,
                "conditions": [{"key": "bt_node_detection", "value": [1]}],
                "bk_cloud_id": [[0, 1][random.randint(0, 1)]],
                "only_ip": False,
                "bk_biz_id": [random.randint(27, 39), random.randint(27, 39)],
                "extra_data": ["identity_info", "job_result"],
            },
            "admin",
        )
        for host_ip in hosts["list"]:
            self.assertRegex(host_ip, IP_REG)
        self.assertLessEqual(len(hosts["list"]), page_size)

    # 停用BT节点探测
    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_only_disable_bt_node_detection(self):
        number = 100
        page_size = 10
        create_cloud_area(number, creator="admin")
        host_to_create, _, _ = create_host(number)
        hosts = HostHandler().list(
            {
                "pagesize": page_size,
                "page": 1,
                "conditions": [{"key": "bt_node_detection", "value": [0]}],
                "bk_cloud_id": [[0, 1][random.randint(0, 1)]],
                "only_ip": False,
                "bk_biz_id": [random.randint(27, 39), random.randint(27, 39)],
                "extra_data": ["identity_info", "job_result"],
            },
            "admin",
        )
        for host_ip in hosts["list"]:
            self.assertRegex(host_ip["inner_ip"], IP_REG)
        self.assertLessEqual(len(hosts["list"]), page_size)

    # 测试管控区域ID:IP 遗失管控区域id的测试
    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_lose_bk_cloud_id(self):
        number = 1000
        page_size = 10
        create_cloud_area(number, creator="admin")
        host_to_create, _, _ = create_host(number)
        hosts = HostHandler().list(
            {
                "pagesize": page_size,
                "page": 1,
                "conditions": [
                    {"key": "bk_cloud_ip", "value": ["1.1.1.1"]},
                ],
                "bk_cloud_id": [[0, 1][random.randint(0, 1)]],
                "only_ip": False,
                "bk_biz_id": [random.randint(27, 39), random.randint(27, 39)],
                "extra_data": ["identity_info", "job_result"],
            },
            "admin",
        )
        for host_ip in hosts["list"]:
            self.assertRegex(host_ip, IP_REG)
        self.assertLessEqual(len(hosts["list"]), page_size)

    # 弥补之前未撰写的 host 精确搜索测试
    def test_acc_search_in_keywords_list(self):
        number = 1000
        page_size = 10
        create_cloud_area(number, creator="admin")
        host_to_create, _, _ = create_host(number)
        hosts = HostHandler().list(
            {
                "pagesize": page_size,
                "page": 1,
                "conditions": [
                    {"key": "inner_ip", "value": ["2.2.2.2"]},
                ],
                "bk_cloud_id": [[0, 1][random.randint(0, 1)]],
                "only_ip": False,
                "bk_biz_id": [random.randint(27, 39), random.randint(27, 39)],
                "extra_data": ["identity_info", "job_result"],
            },
            "admin",
        )
        for host_ip in hosts["list"]:
            self.assertRegex(host_ip, IP_REG)
        self.assertLessEqual(len(hosts["list"]), page_size)

    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_acc_bk_cloud_ip(self):
        page_size = 10
        for i in range(1, 11):
            create_host(1, bk_host_id=i, ip=f"1.1.1.{i}", bk_cloud_id=0)
        for j in range(1, 11):
            create_host(1, bk_host_id=j + 10, ip=f"1.1.1.{j}", bk_cloud_id=1)
        hosts = HostHandler().list(
            {
                "pagesize": page_size,
                "page": 1,
                "conditions": [
                    {"key": "bk_cloud_ip", "value": ["0:1.1.1.1", "1:1.1.1.1", "1.1.1.1"]},
                ],
                "bk_cloud_id": [[0, 1][random.randint(0, 1)]],
                "only_ip": False,
                "bk_biz_id": [k for k in range(27, 40)],
                "extra_data": ["identity_info", "job_result"],
            },
            "admin",
        )
        for host_ip in hosts["list"]:
            self.assertRegex(host_ip["inner_ip"], IP_REG)
        self.assertLessEqual(len(hosts["list"]), 2)
        self.assertLessEqual(len(hosts["list"]), page_size)

    # 数据压缩传递错误参数测试
    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_wrong_case_about_compression(self):
        number = 100
        page_size = 10
        create_cloud_area(number, creator="admin")
        host_to_create, _, _ = create_host(number)
        hosts = HostHandler().list(
            {
                "pagesize": page_size,
                "page": 1,
                "conditions": [{"key": "enable_compression", "value": ["False", 1, "true", 2, 0]}],
                "bk_cloud_id": [[0, 1][random.randint(0, 1)]],
                "only_ip": False,
                "bk_biz_id": [random.randint(27, 39), random.randint(27, 39)],
                "extra_data": ["identity_info", "job_result"],
            },
            "admin",
        )
        for host_ip in hosts["list"]:
            self.assertRegex(host_ip["inner_ip"], IP_REG)
        self.assertEqual(len(hosts["list"]), 0)
        self.assertLessEqual(len(hosts["list"]), page_size)

    # BT节点探测传递错误参数测试
    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_wrong_case_about_bt_node_detection(self):
        number = 100
        page_size = 10
        create_cloud_area(number, creator="admin")
        host_to_create, _, _ = create_host(number)
        hosts = HostHandler().list(
            {
                "pagesize": page_size,
                "page": 1,
                "conditions": [{"key": "bt_node_detection", "value": ["False", 1, "true", 2, 0, "hello"]}],
                "bk_cloud_id": [[0, 1][random.randint(0, 1)]],
                "only_ip": False,
                "bk_biz_id": [random.randint(27, 39), random.randint(27, 39)],
                "extra_data": ["identity_info", "job_result"],
            },
            "admin",
        )
        for host_ip in hosts["list"]:
            self.assertRegex(host_ip["inner_ip"], IP_REG)
        self.assertEqual(len(hosts["list"]), 0)
        self.assertLessEqual(len(hosts["list"]), page_size)

    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_export_cloud_area_colon_ip(self):
        number = 10
        create_host(number)
        params = {
            "pagesize": -1,
            "only_ip": False,
            "return_field": "cloud_ipv4",
            "conditions": [],
            "cloud_id_ip": {"ipv4": True},
        }
        res = HostHandler().list(params, "admin")
        self.assertLessEqual(len(res["list"]), 10)

        params = {
            "pagesize": -1,
            "only_ip": False,
            "return_field": "cloud_ipv4_with_brackets",
            "conditions": [],
            "cloud_id_ip": {"ipv4_with_brackets": True},
        }
        res = HostHandler().list(params, "admin")
        self.assertLessEqual(len(res["list"]), 10)

        create_host(1, bk_host_id=43420, ip="127.0.0.1")
        Host.objects.filter(bk_host_id=43420).update(inner_ipv6="0000:0000:0000:0000:0000:ffff:7f00:0001")
        params = {
            "pagesize": -1,
            "only_ip": False,
            "return_field": "cloud_ipv6_with_brackets",
            "conditions": [],
            "cloud_id_ip": {"ipv6": True},
        }
        res = HostHandler().list(params, "admin")
        self.assertLessEqual(len(res["list"]), 1)

        # 验证参数为False的情况
        params = {
            "pagesize": -1,
            "only_ip": False,
            "return_field": "cloud_ipv4",
            "conditions": [],
            "cloud_id_ip": {"ipv4": False},
        }
        res = HostHandler().list(params, "admin")
        self.assertEqual(len(res["list"]), 0)

    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_update_multi_outer_ip_proxy_info(self):
        host_to_create, identity_to_create, _ = create_host(
            number=1,
            outer_ip="255.255.258",
            login_ip="255.255.259",
            bk_cloud_id=5,
            bk_host_id=10002,
            node_type=const.NodeType.PROXY,
            ip="127.0.0.1",
        )
        update_data = {
            "bk_host_id": host_to_create[0].bk_host_id,
            "outer_ip": "255.255.260,255.255.261",
            "bk_cloud_id": 5,
        }
        self.assertEqual(HostHandler().update_proxy_info(update_data), None)
        proxy_extra_data = Host.objects.get(bk_host_id=10002)
        extra_data = proxy_extra_data.extra_data
        # 验证多外网IP存入extra_data中
        self.assertEqual(extra_data["bk_host_multi_outerip"], "255.255.260,255.255.261")
        # 验证传入多外网IP时，保存传入的第一个IP
        self.assertEqual(proxy_extra_data.outer_ip, "255.255.260")

    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_multi_outer_ip_proxies(self):
        number = 1
        create_cloud_area(number)
        host_to_create, identity_to_create, _ = create_host(
            number=1,
            outer_ip="255.255.251",
            login_ip="255.255.252",
            bk_cloud_id=1,
            bk_host_id=10003,
            node_type=const.NodeType.PROXY,
            ip="127.0.0.1",
        )
        update_data = {
            "bk_host_id": host_to_create[0].bk_host_id,
            "outer_ip": "255.255.256,255.255.257",
            "bk_cloud_id": 1,
        }
        HostHandler().update_proxy_info(update_data)
        result = HostHandler.proxies(number)
        # 如果是多IP场景返回多IP
        self.assertEqual(result[0]["outer_ip"], "255.255.256,255.255.257")

    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_get_topology_only_saas(self):
        page_size = 5
        number = 5
        host_to_create, process_to_create, _ = create_host(number)
        params = {"page": 1, "pagesize": page_size, "only_ip": False, "conditions": [], "source_saas": True}
        result = HostHandler().list(params, "admin")
        for host in result["list"]:
            self.assertLessEqual(len(host["topology"]), 1)
