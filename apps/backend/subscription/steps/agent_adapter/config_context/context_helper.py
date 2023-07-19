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

import json
import random
import re
import typing
from dataclasses import asdict, dataclass, field

from django.conf import settings

from apps.backend.agent import tools
from apps.backend.utils.data_renderer import nested_render_data
from apps.node_man import constants, models

from ..base import AgentSetupInfo
from . import context_dataclass


@dataclass
class ConfigContextHelper:
    agent_setup_info: AgentSetupInfo
    host: models.Host
    node_type: str
    ap: models.AccessPoint
    proxies: typing.List[models.Host]
    install_channel: typing.Tuple[typing.Optional[models.Host], typing.Dict[str, typing.List]]

    context_dict: typing.Dict[str, typing.Any] = field(init=False)

    def __post_init__(self):
        # 优先使用构造数据，不存在构造数据再走 DB 查询
        # self.ap = self.ap or self.host.ap
        # # TODO 收敛到公共方法
        # if self.proxies is None:
        #     self.proxies = self.host.proxies
        # self.install_channel = self.install_channel or self.host.install_channel

        agent_config: typing.Dict[str, typing.Any] = self.ap.get_agent_config(self.host.os_type)
        gse_servers_info: typing.Dict[str, typing.Any] = tools.fetch_gse_servers_info(
            self.agent_setup_info, self.host, self.ap, self.proxies, self.install_channel
        )

        log_path: str = agent_config["log_path"]
        setup_path: str = agent_config["setup_path"]
        path_sep: str = (constants.LINUX_SEP, constants.WINDOWS_SEP)[self.host.os_type == constants.OsType.WINDOWS]

        cert_dir: str = path_sep.join([setup_path, self.node_type, "cert"])
        # Agent 侧证书
        agent_tls_ca_file: str = path_sep.join([cert_dir, constants.GseCert.CA.value])
        agent_tls_cert_file: str = path_sep.join([cert_dir, constants.GseCert.AGENT_CERT.value])
        agent_tls_key_file: str = path_sep.join([cert_dir, constants.GseCert.AGENT_KEY.value])
        agent_tls_password_file: str = path_sep.join([cert_dir, constants.GseCert.CERT_ENCRYPT_KEY.value])
        # Proxy 侧证书
        proxy_tls_ca_file: str = agent_tls_ca_file
        proxy_tls_password_file: str = agent_tls_password_file
        proxy_tls_cert_file: str = path_sep.join([cert_dir, constants.GseCert.SERVER_CERT.value])
        proxy_tls_key_file: str = path_sep.join([cert_dir, constants.GseCert.SERVER_KEY.value])
        proxy_tls_cli_cert_file: str = path_sep.join([cert_dir, constants.GseCert.API_CLIENT_CERT.value])
        proxy_tls_cli_key_file: str = path_sep.join([cert_dir, constants.GseCert.API_CLIENT_KEY.value])

        if self.host.os_type == constants.OsType.WINDOWS:
            # 去除引号
            log_path: str = json.dumps(log_path)[1:-1]
            agent_tls_ca_file: str = json.dumps(agent_tls_ca_file)[1:-1]
            agent_tls_cert_file: str = json.dumps(agent_tls_cert_file)[1:-1]
            agent_tls_key_file: str = json.dumps(agent_tls_key_file)[1:-1]
            agent_tls_password_file: str = json.dumps(agent_tls_password_file)[1:-1]
            proxy_tls_ca_file: str = json.dumps(proxy_tls_ca_file)[1:-1]
            proxy_tls_password_file: str = json.dumps(proxy_tls_password_file)[1:-1]
            proxy_tls_cert_file: str = json.dumps(proxy_tls_cert_file)[1:-1]
            proxy_tls_key_file: str = json.dumps(proxy_tls_key_file)[1:-1]
            proxy_tls_cli_cert_file: str = json.dumps(proxy_tls_cli_cert_file)[1:-1]
            proxy_tls_cli_key_file: str = json.dumps(proxy_tls_cli_key_file)[1:-1]

        # 社区版无需配置证书密码
        if settings.BKAPP_RUN_ENV == constants.BkappRunEnvType.CE.value:
            agent_tls_password_file = ""
            proxy_tls_password_file = ""

        if self.host.node_type == constants.NodeType.PROXY:
            # Agent 配置中 file data 的 endpoint 链接 proxy（可以是同台（自身）或同管控区域内其他 proxy 的 file data）
            file_hosts_for_agent: typing.List[str] = [self.host.inner_ip or self.host.inner_ipv6]
            data_hosts_for_agent: typing.List[str] = [self.host.inner_ip or self.host.inner_ipv6]
        else:
            # 其他情况取实际上游
            file_hosts_for_agent: typing.List[str] = gse_servers_info["bt_file_server_hosts"]
            data_hosts_for_agent: typing.List[str] = gse_servers_info["data_server_hosts"]

        contexts: typing.List[context_dataclass.GseConfigContext] = [
            context_dataclass.AgentConfigContext(
                run_mode=(constants.GseAgentRunMode.AGENT.value, constants.GseAgentRunMode.PROXY.value)[
                    self.host.node_type == constants.NodeType.PROXY
                ],
                cloud_id=self.host.bk_cloud_id,
                zone_id=self.ap.region_id,
                city_id=self.ap.city_id,
                # 管控区域为0, 且使用到Proxy场景的Agent需要设置为true
                # 暂时不考虑当直连区域的安装通道机器并不是 Proxy 的场景
                enable_static_access=["false", "true"][
                    all(
                        [
                            self.host.bk_cloud_id == constants.DEFAULT_CLOUD,
                            self.host.install_channel_id is not None,
                            self.host.node_type == constants.NodeType.AGENT,
                        ]
                    )
                ],
            ),
            context_dataclass.AccessConfigContext(
                cluster_endpoints=",".join(
                    [
                        f"{cluster_host}:{self.ap.port_config['io_port']}"
                        for cluster_host in gse_servers_info["task_server_hosts"]
                    ]
                ),
                data_endpoints=",".join(
                    [f"{data_host}:{self.ap.port_config['data_port']}" for data_host in data_hosts_for_agent]
                ),
                file_endpoints=",".join(
                    [f"{file_host}:{self.ap.port_config['file_svr_port']}" for file_host in file_hosts_for_agent]
                ),
            ),
            context_dataclass.AgentBaseConfigContext(
                tls_ca_file=agent_tls_ca_file,
                tls_cert_file=agent_tls_cert_file,
                tls_key_file=agent_tls_key_file,
                tls_password_file=agent_tls_password_file,
            ),
            context_dataclass.ProxyConfigContext(
                bind_port=self.ap.port_config["io_port"],
                tls_ca_file=proxy_tls_ca_file,
                tls_cert_file=proxy_tls_cert_file,
                tls_key_file=proxy_tls_key_file,
                tls_password_file=proxy_tls_password_file,
            ),
            context_dataclass.TaskConfigContext(),
            context_dataclass.DataConfigContext(
                ipc=agent_config.get("dataipc", "/var/run/ipc.state.report"),
                enable_compression=["false", "true"][self.host.extra_data.get("enable_compression")],
            ),
            context_dataclass.FileConfigContext(
                max_transfer_speed_mb_per_sec=self.host.extra_data.get("bt_speed_limit") or 100,
            ),
            context_dataclass.LogConfigContext(path=log_path),
            context_dataclass.DataMetricConfigContext(exporter_bind_port=self.ap.port_config["data_prometheus_port"]),
            context_dataclass.DataAgentConfigContext(
                tcp_bind_port=self.ap.port_config["data_port"],
                tls_ca_file=proxy_tls_ca_file,
                tls_cert_file=proxy_tls_cert_file,
                tls_key_file=proxy_tls_key_file,
                tls_password_file=proxy_tls_password_file,
            ),
            context_dataclass.DataProxyConfigContext(
                endpoints=",".join(
                    [
                        f"{data_host}:{self.ap.port_config['data_port']}"
                        for data_host in gse_servers_info["data_server_hosts"]
                    ]
                ),
                tls_ca_file=agent_tls_ca_file,
                tls_cert_file=agent_tls_cert_file,
                tls_key_file=agent_tls_key_file,
                tls_password_file=agent_tls_password_file,
            ),
            context_dataclass.FileAgentConfigContext(
                bind_port=self.ap.port_config["file_svr_port"],
                bind_port_v1=self.ap.port_config.get(
                    "file_svr_port_v1", constants.GSE_PORT_DEFAULT_VALUE["file_svr_port_v1"]
                ),
                advertise_ipv4=self.host.inner_ip or "",
                advertise_ipv6=self.host.inner_ipv6 or "",
                tls_ca_file=proxy_tls_ca_file,
                tls_cert_file=proxy_tls_cert_file,
                tls_key_file=proxy_tls_key_file,
                tls_password_file=proxy_tls_password_file,
            ),
            context_dataclass.FileProxyConfigContext(
                upstream_ip=random.choice(gse_servers_info["bt_file_server_hosts"] or [""]),
                upstream_port=self.ap.port_config.get(
                    "file_topology_bind_port", constants.GSE_PORT_DEFAULT_VALUE["file_topology_bind_port"]
                ),
                report_ip=self.host.outer_ip or self.host.outer_ipv6,
                report_port=self.ap.port_config.get(
                    "file_topology_bind_port", constants.GSE_PORT_DEFAULT_VALUE["file_topology_bind_port"]
                ),
            ),
            context_dataclass.FileBittorrentConfigContext(
                bind_port=self.ap.port_config["bt_port"], tracker_bind_port=self.ap.port_config["tracker_port"]
            ),
            context_dataclass.FileTopologyConfigContext(
                bind_port=self.ap.port_config.get(
                    "file_topology_bind_port", constants.GSE_PORT_DEFAULT_VALUE["file_topology_bind_port"]
                ),
                thrift_bind_port=self.ap.port_config["btsvr_thrift_port"],
                advertise_ip=self.host.inner_ip or self.host.inner_ipv6,
                tls_ca_file=agent_tls_ca_file,
                tls_password_file=proxy_tls_password_file,
                tls_svr_cert_file=proxy_tls_cert_file,
                tls_svr_key_file=proxy_tls_key_file,
                tls_cli_cert_file=proxy_tls_cli_cert_file,
                tls_cli_key_file=proxy_tls_cli_key_file,
            ),
            context_dataclass.FileCacheConfigContext(),
            context_dataclass.FileMetricConfigContext(
                exporter_bind_port=self.ap.port_config.get(
                    "file_metric_bind_port", constants.GSE_PORT_DEFAULT_VALUE["file_metric_bind_port"]
                )
            ),
        ]

        self.context_dict = {}
        for context in contexts:
            self.context_dict.update(asdict(context, dict_factory=context.dict_factory))

    def render(self, content: str) -> str:
        """
        渲染并返回配置
        :param content: 配置模板内容
        :return: 渲染后的配置
        """

        def _double(_matched) -> str:
            _env_name: str = str(_matched.group())
            return "{{ " + _env_name[2:-2] + " }}"

        content = re.sub(r"(__[0-9A-Z_]+__)", _double, content)
        return nested_render_data(content, self.context_dict)
