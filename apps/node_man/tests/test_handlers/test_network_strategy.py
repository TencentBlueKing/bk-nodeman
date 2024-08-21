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

    def test_install_agent_strategy(self):
        self.init_db()
        host_info = [
            {"bk_cloud_id": 1, "inner_ip": "127.0.0.1"},
            {"bk_cloud_id": 2, "inner_ip": "127.0.0.2"},
            {"bk_cloud_id": 2, "inner_ip": "127.0.0.3"},
        ]

        result = NetworkStrategyHandler().install_agent_strategy(agent_info=host_info)
        # 会聚合同云区域的信息
        self.assertEqual(len(result), 2)
        for res in result:
            self.assertEqual(len(res["strategy_data"]), 10)
            self.assertEqual(res["strategy_data"][0]["port"], "17980,17981")
        direct_host_info = [
            {"bk_cloud_id": 0, "inner_ip": "127.0.0.1"},
        ]
        self.assertRaises(
            DefaultCloudNotExistsNetworkStrategy, NetworkStrategyHandler().install_agent_strategy, direct_host_info
        )

    def test_install_proxy_strategy(self):
        self.init_db()
        GlobalSettings.set_config(
            key=GlobalSettings.KeyEnum.NETWORK_STRATEGY_CONFIG.value,
            value={
                "nodeman_outer_ip": ["127.0.0.10"],
                "nginx_server_ip": ["127.0.0.11"],
                "blueking_external_saas_ip": ["127.0.0.12", "127.0.0.13"],
            },
        )
        host_info = [
            {"bk_cloud_id": 1, "outer_ip": "127.0.0.1"},
            {"bk_cloud_id": 2, "outer_ip": "127.0.0.2"},
            {"bk_cloud_id": 2, "outer_ip": "127.0.0.3"},
        ]
        result = NetworkStrategyHandler().install_proxy_strategy(proxy_info=host_info)
        # 会聚合同云区域的信息
        self.assertEqual(len(result), 2)
        for res in result:
            self.assertEqual(len(res["strategy_data"]), 9)
            self.assertEqual(res["strategy_data"][1]["port"], "28668")
        direct_host_info = [
            {"bk_cloud_id": 0, "outer_ip": "127.0.0.1"},
        ]

        self.assertRaises(ProxyNotAvaliableError, NetworkStrategyHandler().install_proxy_strategy, direct_host_info)
