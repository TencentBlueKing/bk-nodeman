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
from django.test import TestCase

from apps.node_man import constants
from apps.node_man.exceptions import (
    DefaultCloudNotExistsNetworkStrategy,
    ProxyNotAvaliableError,
)
from apps.node_man.handlers.network_strategy import NetworkStrategyHandler
from apps.node_man.models import Cloud, GlobalSettings
from apps.node_man.tests.utils import create_ap, create_cloud_area, create_host


class TestNetworkStrategy(TestCase):
    @staticmethod
    def init_db():
        number = 2
        create_ap(number=number)
        create_cloud_area(number=number)
        Cloud.objects.filter(ap_id=constants.DEFAULT_AP_ID).update(ap_id=1)
        create_host(number=1, node_type=constants.NodeType.PROXY, bk_host_id=1, bk_cloud_id=1)
        create_host(number=1, node_type=constants.NodeType.PROXY, bk_host_id=2, bk_cloud_id=2)

    def test_install_strategy(self):
        self.init_db()
        host_info = [
            {"bk_cloud_id": 1, "host_ip": "127.0.0.1", "is_install_proxy_strategy": False},
            {"bk_cloud_id": 2, "host_ip": "127.0.0.2", "is_install_proxy_strategy": False},
            {"bk_cloud_id": 2, "host_ip": "127.0.0.3", "is_install_proxy_strategy": False},
        ]

        result = NetworkStrategyHandler().install_strategy(host_info=host_info)
        # 会聚合同云区域的信息
        self.assertEqual(len(result), 2)
        for res in result:
            self.assertEqual(len(res["agent_strategy_data"]), 10)
            self.assertEqual(res["agent_strategy_data"][0]["port"], "17980,17981")
        direct_host_info = [
            {"bk_cloud_id": 0, "host_ip": "127.0.0.1", "is_install_proxy_strategy": False},
        ]
        # 验证直连区域无需配置网络策略
        self.assertRaises(
            DefaultCloudNotExistsNetworkStrategy, NetworkStrategyHandler().install_strategy, direct_host_info
        )

        # proxy策略测试
        GlobalSettings.set_config(
            key=GlobalSettings.KeyEnum.NETWORK_STRATEGY_CONFIG.value,
            value={
                "nodeman_outer_ip": ["127.0.0.10"],
                "nginx_server_ip": ["127.0.0.11"],
                "blueking_external_saas_ip": ["127.0.0.12", "127.0.0.13"],
            },
        )
        host_info = [
            {"bk_cloud_id": 1, "host_ip": "127.0.0.1", "is_install_proxy_strategy": True},
            {"bk_cloud_id": 2, "host_ip": "127.0.0.2", "is_install_proxy_strategy": True},
            {"bk_cloud_id": 2, "host_ip": "127.0.0.3", "is_install_proxy_strategy": True},
        ]
        result = NetworkStrategyHandler().install_strategy(host_info=host_info)
        # 会聚合同云区域的信息
        self.assertEqual(len(result), 2)
        for res in result:
            self.assertEqual(len(res["proxy_strategy_data"]), 9)
            self.assertEqual(res["proxy_strategy_data"][1]["port"], "28668")
        direct_host_info = [
            {"bk_cloud_id": 0, "host_ip": "127.0.0.1", "is_install_proxy_strategy": True},
        ]
        # 验证直连区域不能安装proxy
        self.assertRaises(ProxyNotAvaliableError, NetworkStrategyHandler().install_strategy, direct_host_info)
