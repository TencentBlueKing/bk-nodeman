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
import typing
from dataclasses import dataclass

from apps.node_man import constants


class ConfigContextMeta:
    """
    配置上下文元类
    上下文配置生成规则：{SYSTEM_ID}{FIELD_NAME_SEP}{MODULE_ID}{NAME}，全大写
    """

    # 系统 ID
    SYSTEM_ID: str = ""
    # 系统上下文模块 ID
    MODULE_ID: str = ""
    # 变量名分隔符
    FIELD_NAME_SEP: str = "_"


class GseConfigContextMeta(ConfigContextMeta):
    SYSTEM_ID: str = "BK_GSE"


@dataclass
class GseConfigContext(GseConfigContextMeta):
    def dict_factory(self, kv_tuple_list: typing.List[typing.Tuple[str, typing.Any]]) -> typing.Dict[str, typing.Any]:
        """

        :param kv_tuple_list:
        :return:
        """
        dict_data: typing.Dict[str, typing.Any] = {}
        for k, v in kv_tuple_list:
            # 字段名称组成，不能包含空串
            k_group: typing.List[str] = list(filter(None, [self.SYSTEM_ID, self.MODULE_ID, k]))
            # 通过给定分隔符生成新字段名
            dict_data[self.FIELD_NAME_SEP.join(k_group).upper()] = v
        return dict_data


@dataclass
class TlsBaseConfigContext:
    """
    Agent 侧证书配置
    tls_ca_file - {{ setup_path }}/{{ node_type }}/cert/gseca.crt
    tls_cert_file - {{ setup_path }}/{{ node_type }}/cert/gse_agent.crt
    tls_key_file - {{ setup_path }}/{{ node_type }}/cert/gse_agent.key

    Server 侧证书配置
    tls_ca_file - {{ setup_path }}/{{ node_type }}/cert/gseca.crt
    tls_cert_file - {{ setup_path }}/{{ node_type }}/cert/gse_server.crt
    tls_key_file - {{ setup_path }}/{{ node_type }}/cert/gse_server.key
    """

    tls_ca_file: str = ""
    tls_cert_file: str = ""
    tls_key_file: str = ""
    # 待映射，目前看这个配置没有启用
    tls_passwd_file: str = ""


@dataclass
class AgentConfigContext(GseConfigContext):
    run_mode: int
    cloud_id: int
    zone_id: str
    city_id: str
    extra_config_directory: str = ""

    def __post_init__(self):
        # Agent 模式下无需渲染 Proxy json object
        if self.run_mode in [constants.GseAgentRunMode.AGENT.value]:
            self.proxy = None


@dataclass
class AccessConfigContext(GseConfigContext):
    MODULE_ID = "ACCESS"

    # 等价于 taskserver，格式：host:port(多个以逗号分隔)
    cluster_endpoints: str
    # 等价于 dataserver，格式：host:port(多个以逗号分隔)
    data_endpoints: str
    # 等价于 btfileserver，格式：host:port(多个以逗号分隔)
    file_endpoints: str


@dataclass
class AgentBaseConfigContext(GseConfigContext, TlsBaseConfigContext):
    """
    备注：
    - 配置 Agent 侧证书
    """

    MODULE_ID = "AGENT_BASE"

    # 等价 recvthread
    processor_num: int = 5
    processor_size: int = 4096


@dataclass
class ProxyConfigContext(GseConfigContext, TlsBaseConfigContext):
    """
    备注：
    - 配置 Server 侧证书
    """

    MODULE_ID = "PROXY"

    # 等价于 io_port
    bind_port: int = 0

    thread_num: int = 4

    bind_ip: str = "::"


@dataclass
class TaskConfigContext(GseConfigContext):
    MODULE_ID = "TASK"

    proc_event_data_id: int = 1100008
    concurrence_count: int = 100
    queue_wait_timeout_ms: int = 10000
    executor_queue_size: int = 4096
    schedule_queue_size: int = 4096
    host_code_page_name: str = "utf8"
    script_file_clean_batch_count: int = 100
    script_file_clean_startup_clock_time: int = 0
    script_file_expire_time_hour: int = 72
    script_file_prefix: str = "bk_gse_script_"


@dataclass
class DataConfigContext(GseConfigContext):
    MODULE_ID = "DATA"

    ipc: str
    ipc_recv_thread_num: int = 4


@dataclass
class LogConfigContext(GseConfigContext):
    MODULE_ID = "LOG"

    path: str
    level: str = "WARN"
    filesize_mb: int = 200
    filenum: int = 10
    rotate: int = 0
    flush_interval_ms: int = 1000


@dataclass
class DataMetricConfigContext(GseConfigContext):
    MODULE_ID = "DATA_METRIC"

    exporter_port: int
    exporter_ip: str = "::"


@dataclass
class DataAgentConfigContext(GseConfigContext, TlsBaseConfigContext):
    """
    备注：
    - 配置 Server 侧的证书
    """

    MODULE_ID = "DATA_AGENT"

    tcp_bind_port: int = 0
    tcp_bind_ip: str = "::"

    tcp_server_thread_num: int = 32
    tcp_server_max_message_size: int = 10485760


@dataclass
class DataProxyConfigContext(GseConfigContext, TlsBaseConfigContext):
    """
    备注：
    - 配置 Agent 侧的证书
    """

    MODULE_ID = "DATA_PROXY"

    endpoints: str = ""
