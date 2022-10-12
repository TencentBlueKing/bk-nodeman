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
import typing
from dataclasses import asdict, dataclass, field

from apps.backend.agent import tools
from apps.backend.utils.data_renderer import nested_render_data
from apps.node_man import constants, models

GSE_AGENT_CONFIG = """
{
    "run_mode": {{ run_mode }},
    "cloud_id": {{ cloud_id }},
    "zone_id": "{{ zone_id }}",
    "city_id": "{{ city_id }}",
    "access": {
        "cluster_endpoints": "{{ access.cluster_endpoints }}",
        "data_endpoints": "{{ access.data_endpoints }}",
        "file_endpoints": "{{ access.file_endpoints }}"
    },
    "base": {
        "tls_ca_file": "{{ base.tls_ca_file }}",
        "tls_cert_file": "{{ base.tls_cert_file }}",
        "tls_key_file": "{{ base.tls_key_file }}",
        "tls_passwd_file": "{{ base.tls_passwd_file }}",
        "processor_num": {{ base.processor_num }},
        "processor_size": {{ base.processor_size }}
    },
    {%- if proxy %}
    "proxy": {
        "tls_ca_file": "{{ proxy.tls_ca_file }}",
        "tls_cert_file": "{{ proxy.tls_cert_file }}",
        "tls_key_file": "{{ proxy.tls_key_file }}",
        "tls_passwd_file": "{{ proxy.tls_passwd_file }}",
        "bind_ip": "{{ proxy.bind_ip }}",
        "bind_port": {{ proxy.bind_port }},
        "thread_num": {{ proxy.thread_num }}
    },
    {%- endif %}
    "task": {
        "proc_event_data_id": {{ task.proc_event_data_id }},
        "concurrence_count": {{ task.concurrence_count }},
        "queue_wait_timeout_ms": {{ task.queue_wait_timeout_ms }},
        "executor_queue_size": {{ task.executor_queue_size }},
        "schedule_queue_size": {{ task.schedule_queue_size }},
        "host_code_page_name": "{{ task.host_code_page_name }}",
        "script_file_clean_batch_count": {{ task.script_file_clean_batch_count }},
        "script_file_clean_starup_clock_time": {{ task.script_file_clean_starup_clock_time }},
        "script_file_expire_time_hour": {{ task.script_file_expire_time_hour }},
        "script_file_prefix": "{{ task.script_file_prefix }}"
    },
    "data": {
        "ipc_file": "{{ data.ipc_file }}",
        "ipc_thread_num": {{ data.ipc_thread_num }}
    },
    "logger": {
        "path": "{{ logger.path }}",
        "level": "{{ logger.level }}",
        "filesize_mb": {{ logger.filesize_mb }},
        "filenum": {{ logger.filenum }},
        "rotate": {{ logger.rotate }},
        "flush_interval_ms": {{ logger.flush_interval_ms }}
    },
    "extra_config_directory": "{{ extra_config_directory }}"
}
"""


@dataclass
class AgentAccessConfigContext:

    # 等价于 taskserver，格式：host:port(多个以逗号分隔)
    cluster_endpoints: str
    # 等价于 dataserver，格式：host:port(多个以逗号分隔)
    data_endpoints: str
    # 等价于 btfileserver，格式：host:port(多个以逗号分隔)
    file_endpoints: str


@dataclass
class AgentBaseConfigContext:
    # {{ setup_path }}/{{ node_type }}/cert/gseca.crt
    tls_ca_file: str = ""
    # {{ setup_path }}/{{ node_type }}/cert/gse_agent.crt
    tls_cert_file: str = ""
    # {{ setup_path }}/{{ node_type }}/cert/gse_agent.key
    tls_key_file: str = ""

    # -- 以上为猜测值 --

    # {{ setup_path }}/{{ node_type }}/cert/cert_encrypt.key
    tls_passwd_file: str = ""
    # 等价 recvthread
    processor_num: int = 5
    processor_size: int = 4096


@dataclass
class AgentProxyConfigContext:

    # 等价于 io_port
    bind_port: int

    # {{ setup_path }}/{{ node_type }}/cert/gseca.crt
    tls_ca_file: str = ""
    # {{ setup_path }}/{{ node_type }}/cert/gse_agent.crt
    tls_cert_file: str = ""
    # {{ setup_path }}/{{ node_type }}/cert/gse_agent.key
    tls_key_file: str = ""

    # -- 以上为猜测值 --

    # {{ setup_path }}/{{ node_type }}/cert/cert_encrypt.key
    tls_passwd_file: str = ""

    thread_num: int = 4

    bind_ip: str = "::"


@dataclass
class AgentTaskConfigContext:
    proc_event_data_id: int = 1100008
    concurrence_count: int = 100
    queue_wait_timeout_ms: int = 10000
    executor_queue_size: int = 4096
    schedule_queue_size: int = 4096
    host_code_page_name: str = "utf8"
    script_file_clean_batch_count: int = 100
    script_file_clean_starup_clock_time: int = 0
    script_file_expire_time_hour: int = 72
    script_file_prefix: str = "bk_gse_script_"


@dataclass
class AgentDataConfigContext:
    ipc_file: str
    ipc_thread_num: int = 4


@dataclass
class AgentLoggerConfigContext:
    path: str
    level: str = "WARN"
    filesize_mb: int = 200
    filenum: int = 10
    rotate: int = 0
    flush_interval_ms: int = 1000


@dataclass
class AgentConfigContext:
    run_mode: int
    cloud_id: int
    zone_id: str
    city_id: str
    access: AgentAccessConfigContext
    base: AgentBaseConfigContext
    proxy: typing.Optional[AgentProxyConfigContext]
    task: AgentTaskConfigContext
    data: AgentDataConfigContext
    logger: AgentLoggerConfigContext
    extra_config_directory: str = ""

    def __post_init__(self):
        # Agent 模式下无需渲染 Proxy json object
        if self.run_mode in [constants.GseAgentRunMode.AGENT.value]:
            self.proxy = None


@dataclass
class AgentConfigContextHelper:
    host: models.Host
    node_type: str
    ap: typing.Optional[models.AccessPoint] = None
    proxies: typing.Optional[typing.List[models.Host]] = None
    install_channel: typing.Tuple[typing.Optional[models.Host], typing.Dict[str, typing.List]] = None

    context: AgentConfigContext = field(init=False)
    context_dict: typing.Dict[str, typing.Any] = field(init=False)

    def __post_init__(self):
        # 优先使用构造数据，不存在构造数据再走 DB 查询
        self.ap = self.ap or self.host.ap
        if self.proxies is None:
            self.proxies = self.host.proxies
        self.install_channel = self.install_channel or self.host.install_channel

        agent_config: typing.Dict[str, typing.Any] = self.ap.get_agent_config(self.host.os_type)
        gse_servers_info: typing.Dict[str, typing.Any] = tools.fetch_gse_servers_info(
            self.host, self.ap, self.proxies, self.install_channel
        )

        log_path: str = agent_config["log_path"]
        setup_path: str = agent_config["setup_path"]
        path_sep: str = (constants.LINUX_SEP, constants.WINDOWS_SEP)[self.host.os_type == constants.OsType.WINDOWS]
        base_tls_ca_file: str = path_sep.join([setup_path, self.node_type, "cert", "gseca.crt"])
        base_tls_cert_file: str = path_sep.join([setup_path, self.node_type, "cert", "gse_agent.crt"])
        base_tls_key_file: str = path_sep.join([setup_path, self.node_type, "cert", "gse_agent.key"])

        if self.host.os_type == constants.OsType.WINDOWS:
            # 去除引号
            log_path: str = json.dumps(log_path)[1:-1]
            base_tls_ca_file: str = json.dumps(base_tls_ca_file)[1:-1]
            base_tls_cert_file: str = json.dumps(base_tls_cert_file)[1:-1]
            base_tls_key_file: str = json.dumps(base_tls_key_file)[1:-1]
        else:
            pass

        # 构造上下文
        self.context = AgentConfigContext(
            run_mode=(constants.GseAgentRunMode.AGENT.value, constants.GseAgentRunMode.PROXY.value)[
                self.host.node_type == constants.NodeType.PROXY
            ],
            cloud_id=self.host.bk_cloud_id,
            zone_id=self.ap.region_id,
            city_id=self.ap.city_id,
            access=AgentAccessConfigContext(
                cluster_endpoints=",".join(
                    [
                        f"{cluster_host}:{self.ap.port_config['io_port']}"
                        for cluster_host in gse_servers_info["task_server_hosts"]
                    ]
                ),
                data_endpoints=",".join(
                    [
                        f"{data_host}:{self.ap.port_config['data_port']}"
                        for data_host in gse_servers_info["data_server_hosts"]
                    ]
                ),
                file_endpoints=",".join(
                    [
                        f"{file_host}:{self.ap.port_config['file_svr_port']}"
                        for file_host in gse_servers_info["bt_file_server_hosts"]
                    ]
                ),
            ),
            base=AgentBaseConfigContext(
                tls_ca_file=base_tls_ca_file, tls_cert_file=base_tls_cert_file, tls_key_file=base_tls_key_file
            ),
            proxy=AgentProxyConfigContext(bind_port=self.ap.port_config["io_port"]),
            task=AgentTaskConfigContext(),
            data=AgentDataConfigContext(ipc_file=agent_config.get("dataipc", "/var/run/ipc.state.report")),
            logger=AgentLoggerConfigContext(path=log_path),
        )

        self.context_dict = asdict(self.context)

    def render(self, content: str) -> str:
        """
        渲染并返回配置
        :param content: 配置模板内容
        :return: 渲染后的配置
        """
        return nested_render_data(content, self.context_dict)
