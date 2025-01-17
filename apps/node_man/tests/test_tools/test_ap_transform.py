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

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.mock_data.common_unit.host import (
    AP_MODEL_DATA,
    DEFAULT_HOST_ID,
    DEFAULT_IP,
    DEFAULT_IPV6,
)
from apps.node_man import models
from apps.node_man.utils.endpoint import Endpoint, EndPointTransform
from apps.utils.basic import exploded_ip
from apps.utils.unittest.testcase import CustomAPITestCase
from env.constants import GseVersion


class TestApTransform(TestCase):
    def mock_outer_ipv6(self, ipv6: str):
        return DEFAULT_IPV6.replace("6", "A")

    def setUp(self):
        test_data_list = [
            {
                "name": "公有云接入点",
                "ap_type": "system",
                "region_id": "2",
                "city_id": "30",
                "gse_version": "V2",
                "btfileserver": [
                    {"inner_ip": "127.0.0.120", "outer_ip": "127.0.0.20", "inner_ipv6": None, "outer_ipv6": None},
                    {
                        "inner_ip": "127.0.0.27",
                        "outer_ip": "127.0.0.27",
                        "inner_ipv6": None,
                        "outer_ipv6": None,
                    },
                ],
                "dataserver": [
                    {"inner_ip": "127.0.0.120", "outer_ip": "127.0.0.120", "inner_ipv6": None, "outer_ipv6": None},
                    {
                        "inner_ip": "127.0.0.27",
                        "outer_ip": "127.0.0.27",
                        "inner_ipv6": None,
                        "outer_ipv6": None,
                    },
                ],
                "taskserver": [
                    {"inner_ip": "127.0.0.120", "outer_ip": "127.0.0.120", "inner_ipv6": None, "outer_ipv6": None},
                    {
                        "inner_ip": "127.0.0.27",
                        "outer_ip": "127.0.0.27",
                        "inner_ipv6": None,
                        "outer_ipv6": None,
                    },
                ],
                "zk_hosts": [{"zk_ip": "127.0.0.190", "zk_port": "2182"}],
                "zk_account": "",
                "zk_password": "",
                "package_inner_url": "http://nodeman.test.com/download/prod",
                "package_outer_url": "http://127.0.0.161/download/",
                "nginx_path": "/data/bkee/public/bknodeman/download",
                "agent_config": {
                    "linux": {
                        "dataipc": "/usr/local/gse/agent/data/ipc.state.report",
                        "log_path": "/var/log/gse",
                        "run_path": "/var/run/gse",
                        "data_path": "/var/lib/gse",
                        "temp_path": "/tmp",
                        "setup_path": "/usr/local/gse",
                        "hostid_path": "/var/lib/gse/host/hostid",
                    },
                    "windows": {
                        "dataipc": 27002,
                        "log_path": "C:\\gse\\logs",
                        "run_path": "C:\\gse\\data",
                        "data_path": "C:\\gse\\data",
                        "temp_path": "C:\\Temp",
                        "setup_path": "C:\\gse",
                        "hostid_path": "C:\\gse\\data\\host\\hostid",
                    },
                },
                "status": None,
                "description": "GSE2_上海外网",
                "is_enabled": True,
                "is_default": True,
                "creator": ["admin"],
                "port_config": {
                    "bt_port": 20020,
                    "io_port": 28668,
                    "data_port": 28625,
                    "proc_port": 50000,
                    "trunk_port": 48329,
                    "bt_port_end": 60030,
                    "tracker_port": 20030,
                    "bt_port_start": 60020,
                    "db_proxy_port": 58859,
                    "file_svr_port": 28925,
                    "api_server_port": 50002,
                    "file_svr_port_v1": 58926,
                    "agent_thrift_port": 48669,
                    "btsvr_thrift_port": 58931,
                    "data_prometheus_port": 29402,
                    "file_metric_bind_port": 29404,
                    "file_topology_bind_port": 28930,
                },
                "proxy_package": ["gse_client-windows-x86_64.tgz", "gse_client-linux-x86_64.tgz"],
                "outer_callback_url": "",
                "callback_url": "",
            },
            {
                "name": "公有云接入点_v1",
                "ap_type": "system",
                "region_id": "test",
                "city_id": "test",
                "gse_version": "V1",
                "btfileserver": [
                    {
                        "inner_ip": "127.0.0.198",
                        "outer_ip": "127.0.0.69",
                        "inner_ipv6": None,
                        "outer_ipv6": None,
                    },
                    {
                        "inner_ip": "127.0.0.198",
                        "outer_ip": "127.0.0.76",
                        "inner_ipv6": None,
                        "outer_ipv6": None,
                    },
                ],
                "dataserver": [
                    {
                        "inner_ip": "127.0.0.198",
                        "outer_ip": "127.0.0.69",
                        "inner_ipv6": None,
                        "outer_ipv6": None,
                    },
                    {
                        "inner_ip": "127.0.0.198",
                        "outer_ip": "127.0.0.76",
                        "inner_ipv6": None,
                        "outer_ipv6": None,
                    },
                ],
                "taskserver": [
                    {
                        "inner_ip": "127.0.0.198",
                        "outer_ip": "127.0.0.69",
                        "inner_ipv6": None,
                        "outer_ipv6": None,
                    },
                    {
                        "inner_ip": "127.0.0.198",
                        "outer_ip": "127.0.0.76",
                        "inner_ipv6": None,
                        "outer_ipv6": None,
                    },
                ],
                "zk_hosts": [{"zk_ip": DEFAULT_IP, "zk_port": "2182"}],
                "zk_account": "noneed",
                "zk_password": "noneed",
                "package_inner_url": "http://nodeman.test.com/download/prod-oa",
                "package_outer_url": "http://127.0.0.1/download/prod-oa",
                "nginx_path": "/data/bkee/public/bknodeman/download/prod-oa",
                "agent_config": {
                    "linux": {
                        "dataipc": "/usr/local/gse/agent/data/ipc.state.report",
                        "log_path": "/var/log/gse",
                        "run_path": "/var/run/gse",
                        "data_path": "/var/lib/gse",
                        "temp_path": "/tmp",
                        "setup_path": "/usr/local/gse",
                        "hostid_path": "/var/lib/gse/host/hostid",
                    },
                    "windows": {
                        "dataipc": "47000",
                        "log_path": "C:\\gse\\logs",
                        "run_path": "C:\\gse\\data",
                        "data_path": "C:\\gse\\data",
                        "temp_path": "C:\\Temp",
                        "setup_path": "C:\\gse",
                        "hostid_path": "C:\\gse\\data\\host\\hostid",
                    },
                },
                "status": None,
                "description": "专用Proxy请勿选择",
                "is_enabled": True,
                "is_default": False,
                "creator": ["admin"],
                "port_config": {
                    "bt_port": 10020,
                    "io_port": 48668,
                    "data_port": 58625,
                    "proc_port": 50000,
                    "trunk_port": 48329,
                    "bt_port_end": 60030,
                    "tracker_port": 10030,
                    "bt_port_start": 60020,
                    "db_proxy_port": 58859,
                    "file_svr_port": 58925,
                    "api_server_port": 50002,
                    "agent_thrift_port": 48669,
                    "btsvr_thrift_port": 58930,
                    "data_prometheus_port": 59402,
                },
                "proxy_package": [
                    "gse_client-windows-x86_64.tgz",
                    "gse_client-linux-x86_64.tgz",
                    "gse_client-linux-aarch64.tgz",
                ],
                "outer_callback_url": "",
                "callback_url": "",
            },
            {
                "name": "GSE2_IPV6",
                "ap_type": "system",
                "region_id": "2",
                "city_id": "30",
                "gse_version": "V2",
                "btfileserver": [
                    {
                        "inner_ip": "",
                        "outer_ip": "",
                        "inner_ipv6": DEFAULT_IPV6,
                        "outer_ipv6": self.mock_outer_ipv6(DEFAULT_IPV6),
                    },
                    {
                        "inner_ip": "",
                        "outer_ip": "",
                        "inner_ipv6": DEFAULT_IPV6,
                        "outer_ipv6": self.mock_outer_ipv6(DEFAULT_IPV6),
                    },
                ],
                "dataserver": [
                    {
                        "inner_ip": "",
                        "outer_ip": "",
                        "inner_ipv6": DEFAULT_IPV6,
                        "outer_ipv6": self.mock_outer_ipv6(DEFAULT_IPV6),
                    },
                    {
                        "inner_ip": "",
                        "outer_ip": "",
                        "inner_ipv6": DEFAULT_IPV6,
                        "outer_ipv6": self.mock_outer_ipv6(DEFAULT_IPV6),
                    },
                ],
                "taskserver": [
                    {
                        "inner_ip": "",
                        "outer_ip": "",
                        "inner_ipv6": DEFAULT_IPV6,
                        "outer_ipv6": self.mock_outer_ipv6(DEFAULT_IPV6),
                    },
                    {
                        "inner_ip": "",
                        "outer_ip": "",
                        "inner_ipv6": DEFAULT_IPV6,
                        "outer_ipv6": self.mock_outer_ipv6(DEFAULT_IPV6),
                    },
                ],
                "zk_hosts": [{"zk_ip": DEFAULT_IP, "zk_port": "2182"}],
                "zk_account": "noneed",
                "zk_password": "noneed",
                "package_inner_url": "http://nodeman.test.com/download/prod-oa",
                "package_outer_url": "http://127.0.0.1/download/",
                "nginx_path": "/data/bkee/public/bknodeman/download/",
                "agent_config": {
                    "linux": {
                        "dataipc": "/usr/local/gse/agent/data/ipc.state.report",
                        "log_path": "/var/log/gse",
                        "run_path": "/var/run/gse",
                        "data_path": "/var/lib/gse",
                        "temp_path": "/tmp",
                        "setup_path": "/usr/local/gse",
                        "hostid_path": "/var/lib/gse/host/hostid",
                    },
                    "windows": {
                        "dataipc": 27002,
                        "log_path": "C:\\gse\\logs",
                        "run_path": "C:\\gse\\data",
                        "data_path": "C:\\gse\\data",
                        "temp_path": "C:\\Temp",
                        "setup_path": "C:\\gse",
                        "hostid_path": "C:\\gse\\data\\host\\hostid",
                    },
                },
                "status": None,
                "description": "专用Proxy请勿选择",
                "is_enabled": True,
                "is_default": False,
                "creator": ["admin"],
                "port_config": {
                    "bt_port": 20020,
                    "io_port": 28668,
                    "data_port": 28625,
                    "proc_port": 50000,
                    "trunk_port": 48329,
                    "bt_port_end": 60030,
                    "tracker_port": 20030,
                    "bt_port_start": 60020,
                    "db_proxy_port": 58859,
                    "file_svr_port": 28925,
                    "api_server_port": 50002,
                    "file_svr_port_v1": 58926,
                    "agent_thrift_port": 48669,
                    "btsvr_thrift_port": 58931,
                    "file_metric_bind_port": 29404,
                    "file_topology_bind_port": 28930,
                },
                "proxy_package": ["gse_client-windows-x86_64.tgz", "gse_client-linux-x86_64.tgz"],
                "outer_callback_url": "",
                "callback_url": "",
            },
            {
                "name": "内外网相同接入点",
                "ap_type": "system",
                "region_id": "2",
                "city_id": "30",
                "gse_version": "V2",
                "btfileserver": [
                    {"inner_ip": "127.0.0.120", "outer_ip": "127.0.0.120", "inner_ipv6": None, "outer_ipv6": None},
                ],
                "dataserver": [
                    {"inner_ip": "127.0.0.120", "outer_ip": "127.0.0.120", "inner_ipv6": None, "outer_ipv6": None},
                    {
                        "inner_ip": "127.0.0.27",
                        "outer_ip": "127.0.0.27",
                        "inner_ipv6": None,
                        "outer_ipv6": None,
                    },
                ],
                "taskserver": [
                    {"inner_ip": "127.0.0.120", "outer_ip": "127.0.0.120", "inner_ipv6": None, "outer_ipv6": None},
                    {
                        "inner_ip": "127.0.0.27",
                        "outer_ip": "127.0.0.27",
                        "inner_ipv6": None,
                        "outer_ipv6": None,
                    },
                ],
                "zk_hosts": [{"zk_ip": "127.0.0.190", "zk_port": "2182"}],
                "zk_account": "",
                "zk_password": "",
                "package_inner_url": "http://nodeman.test.com/download/prod",
                "package_outer_url": "http://127.0.0.161/download/",
                "nginx_path": "/data/bkee/public/bknodeman/download",
                "agent_config": {
                    "linux": {
                        "dataipc": "/usr/local/gse/agent/data/ipc.state.report",
                        "log_path": "/var/log/gse",
                        "run_path": "/var/run/gse",
                        "data_path": "/var/lib/gse",
                        "temp_path": "/tmp",
                        "setup_path": "/usr/local/gse",
                        "hostid_path": "/var/lib/gse/host/hostid",
                    },
                    "windows": {
                        "dataipc": 27002,
                        "log_path": "C:\\gse\\logs",
                        "run_path": "C:\\gse\\data",
                        "data_path": "C:\\gse\\data",
                        "temp_path": "C:\\Temp",
                        "setup_path": "C:\\gse",
                        "hostid_path": "C:\\gse\\data\\host\\hostid",
                    },
                },
            },
        ]

        for ap_data in test_data_list:
            models.AccessPoint.objects.update_or_create(**ap_data)

    def test_ap_transform(self):
        gse_v1_ap = models.AccessPoint.objects.get(gse_version=GseVersion.V1.value, name="公有云接入点_v1")
        self.assertEqual(
            EndPointTransform().transform(gse_v1_ap.taskserver),
            {
                "inner_ip_infos": [{"ip": "127.0.0.198"}],
                "outer_ip_infos": [{"ip": "127.0.0.69"}, {"ip": "127.0.0.76"}],
            },
        )

        gse_v2_ap = models.AccessPoint.objects.get(gse_version=GseVersion.V2.value, name="公有云接入点")
        self.assertEqual(
            EndPointTransform().transform(gse_v2_ap.btfileserver),
            {
                "inner_ip_infos": [{"ip": "127.0.0.120"}, {"ip": "127.0.0.27"}],
                "outer_ip_infos": [{"ip": "127.0.0.20"}, {"ip": "127.0.0.27"}],
            },
        )
        outer_and_inner_same_ip_ap = models.AccessPoint.objects.get(name="内外网相同接入点")
        self.assertEqual(
            EndPointTransform().transform(outer_and_inner_same_ip_ap.btfileserver),
            {
                "inner_ip_infos": [{"ip": "127.0.0.120"}],
                "outer_ip_infos": [{"ip": "127.0.0.120"}],
            },
        )

    def test_transfrom_command(self):
        # 调用 django command transform_ap_data 进行数据转换
        default_ap_id = models.AccessPoint.objects.get(name="默认接入点").id
        # 因为默认的接入点已经经过转换，所以这里需要先把默认接入点的数据转换为旧的格式
        call_command("transform_ap_data", transform_endpoint_to_legacy=True, transform_ap_id=default_ap_id)
        default_ap_obj = models.AccessPoint.objects.get(name="默认接入点")
        self.assertEqual(
            default_ap_obj.taskserver,
            [
                {
                    "inner_ip": "",
                    "outer_ip": "",
                }
            ],
        )
        # 把所有的接入点都转换一遍， 转换为新的格式
        call_command("transform_ap_data", transform=True, all_ap=True)
        for ap in models.AccessPoint.objects.all():
            self.assertTrue(isinstance(ap.taskserver, dict))

        gse_v1_ap = models.AccessPoint.objects.get(gse_version="V1", name="公有云接入点_v1")
        self.assertEqual(
            gse_v1_ap.btfileserver,
            {
                "inner_ip_infos": [{"ip": "127.0.0.198"}],
                "outer_ip_infos": [{"ip": "127.0.0.69"}, {"ip": "127.0.0.76"}],
            },
        )
        v6_ap_obj = models.AccessPoint.objects.get(name="GSE2_IPV6")
        self.assertEqual(
            v6_ap_obj.btfileserver,
            {
                "inner_ip_infos": [{"ip": DEFAULT_IPV6}],
                "outer_ip_infos": [{"ip": self.mock_outer_ipv6(DEFAULT_IPV6)}],
            },
        )

        # 转换回旧的数据
        call_command("transform_ap_data", transform_endpoint_to_legacy=True, transform_ap_id=gse_v1_ap.id)
        self.assertEqual(
            #  转换回旧的数据，并且过滤为 None 的字段
            models.AccessPoint.objects.get(id=gse_v1_ap.id).btfileserver,
            [
                {
                    "inner_ip": "127.0.0.198",
                    "outer_ip": "127.0.0.69",
                },
                {
                    "inner_ip": "127.0.0.198",
                    "outer_ip": "127.0.0.76",
                },
            ],
        )
        call_command("transform_ap_data", transform=True, transform_ap_id=gse_v1_ap.id)
        self.assertEqual(
            models.AccessPoint.objects.get(id=gse_v1_ap.id).btfileserver,
            {
                "inner_ip_infos": [{"ip": "127.0.0.198"}],
                "outer_ip_infos": [{"ip": "127.0.0.69"}, {"ip": "127.0.0.76"}],
            },
        )

        # 校验参数
        self.assertRaises(
            CommandError, call_command, "transform_ap_data", transform_endpoint_to_legacy=True, transform=True
        )
        self.assertRaises(
            CommandError, call_command, "transform_ap_data", transform_endpoint_to_legacy=True, transform=False
        )
        self.assertRaises(
            CommandError,
            call_command,
            "transform_ap_data",
            transform_endpoint_to_legacy=True,
            transform=False,
            all_ap=True,
            transform_ap_id=gse_v1_ap.id,
        )

    def test_transform_with_host_id(self):
        ap = models.AccessPoint.objects.get(name="公有云接入点_v1")
        ap_btfileserver = ap.btfileserver
        for server in ap_btfileserver:
            server.update(bk_host_id=DEFAULT_HOST_ID)
        models.AccessPoint.objects.filter(name="公有云接入点_v1").update(btfileserver=ap_btfileserver)
        call_command("transform_ap_data", transform=True, transform_ap_id=ap.id)
        self.assertEqual(
            models.AccessPoint.objects.get(id=ap.id).btfileserver,
            {
                "inner_ip_infos": [{"ip": "127.0.0.198", "bk_host_id": DEFAULT_HOST_ID}],
                "outer_ip_infos": [
                    {"ip": "127.0.0.69", "bk_host_id": DEFAULT_HOST_ID},
                    {"ip": "127.0.0.76", "bk_host_id": DEFAULT_HOST_ID},
                ],
            },
        )

        # test ap endpoint
        self.assertEqual(
            models.AccessPoint.objects.get(id=ap.id).file_endpoint_info.outer_hosts, ["127.0.0.69", "127.0.0.76"]
        )
        self.assertEqual(models.AccessPoint.objects.get(id=ap.id).file_endpoint_info.inner_hosts, ["127.0.0.198"])
        self.assertEqual(
            models.AccessPoint.objects.get(id=ap.id).file_endpoint_info.inner_endpoints,
            [Endpoint(v4="127.0.0.198", v6=None, host_id=DEFAULT_HOST_ID)],
        )


class ApViewTransformTestCase(CustomAPITestCase):
    TEST_AP_NAME = "CUSTOM_AP"
    CREATE_URL = "/api/ap/"

    def setUp(self):
        ap_data = deepcopy(AP_MODEL_DATA)
        ap_data["name"] = self.TEST_AP_NAME
        self.ap_data = ap_data

    def test_ap_create(self):
        self.client.post(path=self.CREATE_URL, data=self.ap_data)
        ap = models.AccessPoint.objects.get(name=self.TEST_AP_NAME)
        self.assertEqual(ap.name, self.TEST_AP_NAME)
        self.assertEqual(ap.taskserver, AP_MODEL_DATA["taskserver"])

    def test_mix_ip_ap_create(self):
        self.ap_data["taskserver"] = {"inner_ip_infos": [{"ip": DEFAULT_IP}, {"ip": DEFAULT_IPV6}]}
        result = self.client.post(self.CREATE_URL, self.ap_data)
        self.assertFalse(result["result"])
        self.assertEqual(result["message"], "inner_ip_infos 中不能同时包括 ipv4 和 ipv6（3800001）")

        # 支持 taskserver v6 & fileserver v4 混合
        mix_server_ap_data = deepcopy(self.ap_data)
        mix_server_ap_data["taskserver"] = {"inner_ip_infos": [{"ip": DEFAULT_IPV6}]}
        result = self.client.post(self.CREATE_URL, mix_server_ap_data)
        self.assertTrue(result["result"])

    def test_multi_v4_ap_create(self):
        # 支持多个 v4 地址
        self.ap_data["taskserver"] = {
            "inner_ip_infos": [{"ip": DEFAULT_IP}, {"ip": DEFAULT_IP.replace("1", "2")}],
            "outer_ip_infos": [{"ip": DEFAULT_IP}, {"ip": DEFAULT_IP.replace("1", "2")}],
        }
        result = self.client.post(self.CREATE_URL, self.ap_data)
        self.assertTrue(result["result"])
        ap = models.AccessPoint.objects.get(name=self.TEST_AP_NAME)
        self.assertEqual(
            ap.taskserver,
            {
                "inner_ip_infos": [{"ip": DEFAULT_IP}, {"ip": DEFAULT_IP.replace("1", "2")}],
                "outer_ip_infos": [{"ip": DEFAULT_IP}, {"ip": DEFAULT_IP.replace("1", "2")}],
            },
        )

    def test_multi_v6_ap_create(self):
        # 支持多个 v6 地址
        self.ap_data["taskserver"] = {"inner_ip_infos": [{"ip": DEFAULT_IPV6}, {"ip": DEFAULT_IPV6.replace("1", "2")}]}
        result = self.client.post(self.CREATE_URL, self.ap_data)
        self.assertTrue(result["result"])

    def test_v4_v6_mix_ap_create(self):
        # 支持同一个 server inner & outer v4 v6 混合
        self.ap_data["taskserver"] = {
            "inner_ip_infos": [{"ip": DEFAULT_IP}],
            "outer_ip_infos": [{"ip": DEFAULT_IPV6}],
        }
        result = self.client.post(self.CREATE_URL, self.ap_data)
        self.assertTrue(result["result"])
        ap = models.AccessPoint.objects.get(name=self.TEST_AP_NAME)
        self.assertEqual(
            ap.taskserver,
            {
                "inner_ip_infos": [{"ip": DEFAULT_IP}],
                "outer_ip_infos": [{"ip": exploded_ip(DEFAULT_IPV6)}],
            },
        )

    def test_filter_ip_ap_crete(self):
        # 支持过滤掉重复 ip
        self.ap_data["taskserver"] = {"inner_ip_infos": [{"ip": DEFAULT_IP}, {"ip": DEFAULT_IP}]}
        result = self.client.post(self.CREATE_URL, self.ap_data)
        self.assertTrue(result["result"])
        self.assertEqual(
            result["data"]["taskserver"]["inner_ip_infos"],
            [{"ip": DEFAULT_IP}],
        )

    def test_illegal_ip_ap_create(self):
        # 支持 v4 / v6 IP格式检测
        self.ap_data["taskserver"] = {"inner_ips": [{"inner_ip": "11"}]}
        self.assertFalse(self.client.post(self.CREATE_URL, self.ap_data)["result"])
        self.ap_data["taskserver"] = {"inner_ips": [{"inner_ip": DEFAULT_IP}, {"inner_ip": "11"}]}
        self.assertFalse(self.client.post(self.CREATE_URL, self.ap_data)["result"])
        self.ap_data["taskserver"] = {"inner_ips": [{"inner_ipv6": DEFAULT_IP}]}
        self.assertFalse(self.client.post(self.CREATE_URL, self.ap_data)["result"])

    def test_update_ap(self):
        update_ap_name = "默认update ap"
        self.ap_data["taskserver"] = {"inner_ip_infos": [{"ip": "111.1.1.1"}]}
        self.ap_data["name"] = "默认update ap"
        ap_id = models.AccessPoint.objects.get(name="默认接入点").id
        update_url = f"/api/ap/{ap_id}/"
        result = self.client.put(update_url, self.ap_data)
        self.assertTrue(result["result"])
        ap_obj = models.AccessPoint.objects.get(name=update_ap_name)
        self.assertEqual(ap_obj.taskserver, {"inner_ip_infos": [{"ip": "111.1.1.1"}]})

    def test_ap_retrieve(self):
        self.test_ap_create()
        ap_id = models.AccessPoint.objects.get(name=self.TEST_AP_NAME).id
        retrieve_url = f"/api/ap/{ap_id}/"
        result = self.client.get(retrieve_url)
        self.assertTrue(result["result"])
        self.assertEqual(result["data"]["name"], self.TEST_AP_NAME)
        self.assertEqual(result["data"]["taskserver"], AP_MODEL_DATA["taskserver"])

    def test_ap_test(self):
        ap_tes_url: str = "/api/ap/test/"
        test_ap_data: dict = {
            "btfileserver": {"inner_ip_infos": [{"ip": DEFAULT_IP}], "outer_ip_infos": [{"ip": "127.0.0.2"}]},
            "taskserver": {"inner_ip_infos": [{"ip": DEFAULT_IP}], "outer_ip_infos": [{"ip": "127.0.0.2"}]},
            "dataserver": {"inner_ip_infos": [{"ip": DEFAULT_IP}], "outer_ip_infos": [{"ip": "127.0.0.2"}]},
            "package_inner_url": "http://127.0.0.1/download/",
            "package_outer_url": "http://127.0.0.2/download/",
        }
        result = self.client.post(ap_tes_url, test_ap_data)
        self.assertFalse(result["data"]["test_result"])
        self.assertEqual(result["data"]["test_logs"][1]["log"], f"Ping {DEFAULT_IP} 正常")
