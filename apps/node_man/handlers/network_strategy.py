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
from collections import defaultdict
from typing import Any, Dict, List, Union

from django.db.models import QuerySet
from django.utils.translation import ugettext as _

from apps.node_man import constants, exceptions, models


class NetworkStrategyHandler:
    @staticmethod
    def aggregate_host_info(host_info: List[Dict[str, Union[int, str]]], ip_type: str) -> List[Dict[str, Any]]:
        """
        :param host_info: 主机信息
        :param ip_type: ip类型
        :return: 聚合同云区域后的主机信息
        """
        ips_gby_bk_cloud_id: Dict[str, Any] = defaultdict(list)
        for item in host_info:
            key = item["bk_cloud_id"]
            ips_gby_bk_cloud_id[key].append(item[ip_type])

        result: List[Dict[str, Any]] = [
            {"bk_cloud_id": key, "ips": value} for key, value in ips_gby_bk_cloud_id.items()
        ]
        return result

    @staticmethod
    def get_ap_common_config(ap_obj: models.AccessPoint, partial: bool = False):
        """
        获取接入点公共配置
        :param ap_obj: 接入点对象
        :param partial: 是否只获取部分字段
        :return: 接入点名称，端口配置，任务服务器IP，数据服务器IP，文件服务器IP
        """
        ap_name: str = ap_obj.name
        port_config: Dict[str, int] = ap_obj.port_config
        if partial:
            return ap_name, port_config

        task_server: List[Dict[str, Any]] = ap_obj.taskserver
        data_server: List[Dict[str, Any]] = ap_obj.dataserver
        file_server: List[Dict[str, Any]] = ap_obj.btfileserver
        task_server_ips: str = ",".join([task_server_info["inner_ip"] for task_server_info in task_server])
        data_server_ips: str = ",".join([data_server_info["inner_ip"] for data_server_info in data_server])
        file_server_ips: str = ",".join([file_server_info["inner_ip"] for file_server_info in file_server])
        return ap_name, port_config, task_server_ips, data_server_ips, file_server_ips

    @staticmethod
    def get_gse_common_port(port_config: Dict[str, int]):
        """
        获取Agent与Proxy所需共同端口
        :param port_config: 端口配置字典
        :return: Agent与Proxy所需共同端口
        """
        io_port: int = port_config["io_port"]
        data_port: int = port_config["data_port"]
        bt_port: int = port_config["bt_port"]
        tracker_port: int = port_config["tracker_port"]
        return io_port, data_port, bt_port, tracker_port

    @staticmethod
    def structure_strategy_data(
        source_address: str, target_address: str, port: Union[int, str], protocol: str, use: str
    ):
        """
        构造策略数据字典
        :param source_address: 源地址
        :param target_address: 目标地址
        :param port: 端口
        :param protocol: 通信协议
        :param use: 用途
        :return: 策略数据
        """
        return {
            "source_address": source_address,
            "target_address": target_address,
            "port": str(port),
            "protocol": protocol,
            "use": use,
        }

    @staticmethod
    def port_use(node_type: str):
        """
        获取端口用途
        :param node_type: 节点类型
        :return: 各个端口的用途
        """
        # 构造用途映射
        use_map: Dict[str, str] = {
            key: str(value) for key, value in constants.UseType.get_member_value__alias_map().items()
        }
        task_serve: str = f"{use_map[constants.UseType.TASK_SERVE_PORT.value]}"
        data_serve: str = f"{use_map[constants.UseType.DATA_SERVE_PORT.value]}"
        file_transmit: str = f"{use_map[constants.UseType.FILE_TRANSMIT_PORT.value]}"
        if node_type == constants.NodeType.PAGENT:
            nginx_download_proxy_pass = (
                f"{use_map[constants.UseType.NGINX_DOWNLOAD.value]}/"
                f"{use_map[constants.UseType.NGINX_PROXY_PASS.value]}"
            )
            return nginx_download_proxy_pass, task_serve, data_serve, file_transmit
        elif node_type == constants.NodeType.PROXY:
            get_config: str = f"{use_map[constants.UseType.GET_CONFIG.value]}"
            report_log: str = f"{use_map[constants.UseType.REPORT_LOG.value]}"
            ssh_connect: str = f"{use_map[constants.UseType.SSH_CONNECT_PORT.value]}"
            return task_serve, data_serve, file_transmit, get_config, report_log, ssh_connect

    def install_agent_strategy(self, agent_info: List[Dict[str, Union[int, str]]]) -> List[Dict[str, Any]]:
        """
        InstallAgent网络策略
        :param agent_info: Agent信息
        :return: 策略数据
        """
        result = []
        # 聚合相同云区域的主机IP
        host_info: List[Dict[str, Any]] = self.aggregate_host_info(host_info=agent_info, ip_type="inner_ip")
        cloud_id_name_map, cloud_ap_id_map, ap_id_obj_map = self.get_cloud_info_and_ap_map()
        nginx_download_proxy_pass_port: str = (
            f"{constants.NginxPortType.NGINX_DOWNLOAD_PORT.value},"
            f"{constants.NginxPortType.NGINX_PROXY_PASS_PORT.value}"
        )
        # 获取通信协议
        tcp_value, udp_value, tcp_udp_values = self.list_communication_protocol()
        # 各个端口的用途
        nginx_download_proxy_pass, task_serve, data_serve, file_transmit = self.port_use(
            node_type=constants.NodeType.PAGENT
        )

        for host in host_info:
            bk_cloud_id: int = host["bk_cloud_id"]
            if bk_cloud_id == constants.DEFAULT_CLOUD:
                raise exceptions.DefaultCloudNotExistsNetworkStrategy(_("直连Agent端：与蓝鲸服务端双向全通,若存在策略限制,可新增管控区域来管理."))
            bk_cloud_name: str = cloud_id_name_map.get(str(bk_cloud_id))
            if not bk_cloud_name:
                raise exceptions.CloudNotExistError(_(f"不存在ID为: {bk_cloud_id} 的「管控区域」"))
            ap_id: int = cloud_ap_id_map[bk_cloud_id]
            ap_obj: models.AccessPoint = ap_id_obj_map.get(ap_id)
            if not ap_obj or ap_id == constants.DEFAULT_AP_ID:
                raise exceptions.ApIDNotExistsError(_("该云区域未选择接入点或原接入点不存在数据库中"))
            # 获取接入点名称，端口配置
            ap_name, port_config = self.get_ap_common_config(ap_obj=ap_obj, partial=True)
            io_port, data_port, bt_port, tracker_port = self.get_gse_common_port(port_config=port_config)
            bt_transfer_port_scope = f"{bt_port}-{tracker_port}"
            bt_port_start = port_config["bt_port_start"]
            bt_port_end = port_config["bt_port_end"]
            bt_port_scope = f"{bt_port_start}-{bt_port_end}"
            file_svr_port = port_config["file_svr_port"]
            host_queryset: QuerySet = models.Host.objects.filter(
                bk_cloud_id=bk_cloud_id, node_type=constants.NodeType.PROXY
            ).values("inner_ip")
            inner_ips: List[str] = [host["inner_ip"] for host in host_queryset]
            proxies_ips = ",".join(inner_ips)
            host_ips = ",".join(host["ips"])
            strategy_data = [
                self.structure_strategy_data(
                    host_ips, proxies_ips, nginx_download_proxy_pass_port, tcp_value, nginx_download_proxy_pass
                ),
                self.structure_strategy_data(host_ips, proxies_ips, io_port, tcp_value, task_serve),
                self.structure_strategy_data(host_ips, proxies_ips, data_port, tcp_value, data_serve),
                self.structure_strategy_data(host_ips, proxies_ips, file_svr_port, tcp_value, file_transmit),
                self.structure_strategy_data(host_ips, proxies_ips, bt_port, tcp_udp_values, file_transmit),
                self.structure_strategy_data(host_ips, proxies_ips, tracker_port, udp_value, file_transmit),
                self.structure_strategy_data(
                    proxies_ips, host_ips, bt_transfer_port_scope, tcp_udp_values, file_transmit
                ),
                self.structure_strategy_data(proxies_ips, host_ips, bt_port_scope, tcp_udp_values, file_transmit),
                self.structure_strategy_data(host_ips, host_ips, bt_transfer_port_scope, tcp_udp_values, file_transmit),
                self.structure_strategy_data(host_ips, host_ips, bt_port_scope, tcp_udp_values, file_transmit),
            ]
            key = f"{bk_cloud_name}-{ap_name}"
            result.append({"name": key, "strategy_data": strategy_data})

        return result

    def install_proxy_strategy(self, proxy_info: List[Dict[str, Union[int, str]]]) -> List[Dict[str, Any]]:
        """
        InstallProxy网络策略
        :param proxy_info: Proxy信息
        :return: 策略数据
        """
        result = []
        host_info = self.aggregate_host_info(host_info=proxy_info, ip_type="outer_ip")
        cloud_id_name_map, cloud_ap_id_map, ap_id_obj_map = self.get_cloud_info_and_ap_map()
        # 获取后台配置的公网IP信息
        nodeman_outer_ip, nginx_server_ip, blueking_external_saas_ip = self.get_network_strategy_config()
        # 获取所需端口
        ssh_connect_port = f"{constants.SSH_PORT} or {constants.LINUX_PORT}"
        http_port = constants.HttpPortType.HTTP_PORT.value
        https_port = constants.HttpPortType.HTTPS_PORT.value
        report_log_port = f"{http_port},{https_port}"
        # 获取通信协议
        tcp_value, udp_value, tcp_udp_values = self.list_communication_protocol()
        # 各个端口的用途
        task_serve, data_serve, file_transmit, get_config, report_log, ssh_connect = self.port_use(
            node_type=constants.NodeType.PROXY
        )
        for host in host_info:
            bk_cloud_id = host["bk_cloud_id"]
            if bk_cloud_id == constants.DEFAULT_CLOUD:
                raise exceptions.ProxyNotAvaliableError(_("直连区域不可安装Proxy"))
            bk_cloud_name: str = cloud_id_name_map.get(str(bk_cloud_id))
            if not bk_cloud_name:
                raise exceptions.CloudNotExistError(_(f"不存在ID为: {bk_cloud_id} 的「管控区域」"))
            ap_id: int = cloud_ap_id_map[bk_cloud_id]
            ap_obj: models.AccessPoint = ap_id_obj_map.get(ap_id)
            if not ap_obj or ap_id == constants.DEFAULT_AP_ID:
                raise exceptions.ApIDNotExistsError(_("该云区域未选择接入点或原接入点不存在数据库中"))
            # 获取接入点名称，端口配置，任务服务器IP，数据服务器IP，文件服务器IP
            ap_name, port_config, task_server_ips, data_server_ips, file_server_ips = self.get_ap_common_config(
                ap_obj=ap_obj, partial=False
            )
            io_port, data_port, bt_port, tracker_port = self.get_gse_common_port(port_config=port_config)
            file_topology_bind_port = port_config["file_topology_bind_port"]
            proxies_ips = ",".join(host["ips"])
            strategy_data = [
                self.structure_strategy_data(nodeman_outer_ip, proxies_ips, ssh_connect_port, tcp_value, ssh_connect),
                self.structure_strategy_data(proxies_ips, data_server_ips, io_port, tcp_value, task_serve),
                self.structure_strategy_data(proxies_ips, task_server_ips, data_port, tcp_value, data_serve),
                self.structure_strategy_data(
                    proxies_ips, file_server_ips, file_topology_bind_port, tcp_value, file_transmit
                ),
                self.structure_strategy_data(proxies_ips, nginx_server_ip, http_port, tcp_value, get_config),
                self.structure_strategy_data(
                    proxies_ips, blueking_external_saas_ip, report_log_port, tcp_value, report_log
                ),
                self.structure_strategy_data(proxies_ips, proxies_ips, bt_port, tcp_udp_values, file_transmit),
                self.structure_strategy_data(proxies_ips, proxies_ips, tracker_port, udp_value, file_transmit),
                self.structure_strategy_data(
                    proxies_ips, proxies_ips, file_topology_bind_port, tcp_value, file_transmit
                ),
            ]
            key = f"{bk_cloud_name}-{ap_name}"
            result.append({"name": key, "strategy_data": strategy_data})
        return result

    @staticmethod
    def get_network_strategy_config():
        """
        获取全局配置中的各项策略IP
        :return: 节点管理出口IP、nginx服务IP、蓝鲸外部版SAAS IP
        """
        network_strategy_config: Dict[str, Any] = models.GlobalSettings.get_config(
            key=models.GlobalSettings.KeyEnum.NETWORK_STRATEGY_CONFIG.value, default={}
        )
        network_strategy_config: Dict[str, str] = {
            key: ",".join(value) for key, value in network_strategy_config.items()
        }
        nodeman_outer_ip: str = network_strategy_config.get("nodeman_outer_ip", "")
        nginx_server_ip: str = network_strategy_config.get("nginx_server_ip", "")
        blueking_external_saas_ip: str = network_strategy_config.get("blueking_external_saas_ip", "")
        return nodeman_outer_ip, nginx_server_ip, blueking_external_saas_ip

    @staticmethod
    def list_communication_protocol():
        """
        列举通信协议
        """
        tcp_value = constants.PortProtocolType.TCP.value
        udp_value = constants.PortProtocolType.UDP.value
        tcp_udp_values = f"{tcp_value},{udp_value}"
        return tcp_value, udp_value, tcp_udp_values

    @staticmethod
    def get_cloud_info_and_ap_map():
        """
        :return: 云区域ID与云区域名称映射、云区域ID与接入点ID映射、接入点ID与接入点对象映射
        """
        cloud_id_name_map: Dict[str, str] = models.Cloud.cloud_id_name_map(get_cache=True)
        cloud_ap_id_map: Dict[int, int] = models.Cloud.cloud_ap_id_map()
        ap_id_obj_map: Dict[int, models.AccessPoint] = models.AccessPoint.ap_id_obj_map()
        return cloud_id_name_map, cloud_ap_id_map, ap_id_obj_map
