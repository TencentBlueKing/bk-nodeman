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
import logging
import time

import ujson as json
from blueapps.account.decorators import login_exempt
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from apps.backend.utils.data_renderer import nested_render_data
from apps.backend.utils.encrypted import GseEncrypted
from apps.node_man import constants, models
from apps.node_man.models import Host, JobSubscriptionInstanceMap, aes_cipher
from pipeline.service import task_service

logger = logging.getLogger("app")

DATA_TMPLATE = """
{
    "level":"error",
    "log": "{{ log_path }}",
    "password_keyfile": "{{ setup_path }}/proxy/cert/cert_encrypt.key",
    "cert":"{{ setup_path }}/proxy/cert",
    "runtimedata":"{{ setup_path }}/proxy/public/gse",
    "runmode":1,
    "datasvrip":"{{ inner_ip }}",
    "dbgipc":"{{ setup_path }}/public/gse/ipc.dbg.data",
    "dataflow":"{{ setup_path }}/proxy/etc/dataflow.conf",
    "prometheus_http_svr_ip":"0.0.0.0",
    "prometheus_datasvr_port": {{ data_prometheus_port }},
    "enableops": false,
    "zkhost": "",
    "dftregid": "{{ region_id }}",
    "dftcityid": "{{ city_id }}"
} """

DATALOFW_TMPLATE = """
{
    "receiver":[
      {
        "name":"r_agent",
        "protocol":1,
        "bind": "{{ inner_ip }}",
        "port": {{ data_port }},
        "cert":"{{ setup_path}}/proxy/cert",
        "protostack":2
      }
    ],
    "exporter":[
      {
        "name":"e_transfer_to_ds",
        "type":9,
        "cert":"{{ setup_path }}/proxy/cert",
        "proxyprotocol":"tcp",
        "connectionnum":4,
        "proxyversion":"v1",
        "heartbeat":true,
        "addresses":[
            {% for gse_outer_ip in taskserver_outer_ips%}
                {
                    "ip": "{{ gse_outer_ip }}",
                    "port": {{ data_port }}
                }{% if not loop.last %},{% endif %}
            {% endfor %}
        ]
      }
    ],
    "filters":[
    ],
    "channel":[
        {
            "name":"c_transfer_ds",
            "decode":5,
            "receiver":"r_agent",
            "exporter":[
                "e_transfer_to_ds"
            ]
        }
    ]
} """

AGENT_TEMPLATE = """
{
    "log": {{ log_path }},
    "logfilesize": 10,
    "logfilenum": 10,
    {%- if password_keyfile %}
    "password_keyfile": {{ password_keyfile }},
    {%- endif %}
    "cert": {{ cert }},
    "proccfg": {{ proccfg }},
    "procgroupcfg": {{ procgroupcfg }},
    "alarmcfgpath": {{ alarmcfgpath }},
    "dataipc": {{ dataipc }},
    "plugincfg": {{ plugincfg }},
    "pluginbin": {{ pluginbin }},
    "pluginipc": {{ pluginipc }},
    "runmode": 1,
    "alliothread": 8,
    "workerthread": 24,
    "level": "error",
    "ioport": {{ io_port }},
    "filesvrport": {{ file_svr_port }},
    "dataport": {{ data_port}},
    "btportstart": {{ bt_port_start }},
    "btportend": {{ bt_port_end }},
    "agentip": "{{ agentip }}",
    "identityip": "{{ identityip }}",
    {%- if region_id %}
    "dftregid": "{{ region_id }}",
    {%- endif %}
    {%- if city_id %}
    "dftcityid": "{{ city_id }}",
    {%- endif %}
    "bizid": {{ bk_supplier_id }},
    "cloudid": {{ bk_cloud_id }},
    "recvthread": 5,
    "timeout": 120,
    "tasknum": 100,
    "thriftport": {{ agent_thrift_port }},
    "trunkport": {{ trunk_port }},
    "dbproxyport": {{ db_proxy_port }},
    "apiserverport": {{ api_server_port }},
    "procport": {{ proc_port }},
    "peer_exchange_switch_for_agent": {{ peer_exchange_switch_for_agent }},
    {%- if bt_speed_limit %}
    "btSpeedLimit": {{ bt_speed_limit }},
    {%- endif -%}
    {% if is_designated_upstream_servers %}
    "btfileserver": [
        {%- for server in btfileserver_inner_ips%}
        {
            "ip": "{{ server }}",
            "port": {{ file_svr_port }}
        }{% if not loop.last %},{% endif %}
        {%- endfor %}
    ],
    "dataserver": [
        {%- for server in dataserver_inner_ips%}
        {
            "ip": "{{ server }}",
            "port": {{ data_port }}
        }{% if not loop.last %},{% endif %}
        {%- endfor %}
    ],
    "taskserver": [
        {%- for server in taskserver_inner_ips%}
        {
            "ip": "{{ server }}",
            "port": {{ io_port }}
        }{% if not loop.last %},{% endif %}
        {%- endfor %}
    ],
    {%- elif zkauth %}
    "zkhost": "{{ zkhost }}",
    "zkauth": "{{ zkauth }}",
    {%- else %}
    "zkhost": "{{ zkhost }}",
    {%- endif %}
    "btserver_is_bridge": 0,
    "btserver_is_report": 1
}
"""

PROXY_TEMPLATE = """
{
    "log": "{{ log_path }}",
    "logfilesize": 10,
    "logfilenum": 10,
    {%- if password_keyfile %}
    "password_keyfile": "{{ setup_path }}/proxy/cert/cert_encrypt.key",
    {%- endif %}
    "cert": "{{ setup_path }}/proxy/cert",
    "proccfg": "{{ setup_path }}/proxy/etc/procinfo.json",
    "procgroupcfg": "{{ setup_path }}/proxy/etc/procgroupinfo.json",
    "alarmcfgpath": "{{ setup_path }}/plugins/etc",
    "plugincfg": "{{ setup_path }}/proxy/etc/plugin_info.json",
    "pluginbin": "{{ setup_path }}/proxy/lib",
    "pluginipc": "{{ setup_path }}/proxy/data/ipc.plugin.manage",
    "dataipc": "{{ dataipc }}",
    "runmode": 0,
    "alliothread": 8,
    "workerthread": 24,
    "level": "error",
    "clean_script_files_maxhours": 72,
    "processstatusdataid":{{ process_status_dataid }},
    "processeventdataid":{{ process_event_dataid }},
    "ioport": {{ io_port }},
    "filesvrport": {{ file_svr_port }},
    "btportstart": {{ bt_port_start }},
    "btportend": {{ bt_port_end }},
    "proxylistenip": "{{ inner_ip }}",
    "agentip": "{{ inner_ip }}",
    "identityip": "{{ inner_ip }}",
    "peer_exchange_switch_for_agent": {{ peer_exchange_switch_for_agent }},
    {%- if bt_speed_limit %}
    "btSpeedLimit": {{ bt_speed_limit }},
    {%- endif %}
    "proxytaskserver": [
        {% for gse_outer_ip in taskserver_outer_ips%}
            {
                "ip": "{{ gse_outer_ip }}",
                "port": {{ io_port }}
            }{% if not loop.last %},{% endif %}
        {% endfor %}
    ],
    "btfileserver": [
        {% for proxy_server in proxy_servers%}
            {
                "ip": "{{ proxy_server }}",
                "port": {{ file_svr_port }}
            }{% if not loop.last %},{% endif %}
        {% endfor %}
    ],
    "dataserver": [
        {% for proxy_server in proxy_servers%}
            {
                "ip": "{{ proxy_server }}",
                "port": {{ data_port }}
            }{% if not loop.last %},{% endif %}
        {% endfor %}
    ],
    "taskserver": [
        {% for proxy_server in proxy_servers%}
            {
                "ip": "{{ proxy_server }}",
                "port": {{ io_port }}
            }{% if not loop.last %},{% endif %}
        {% endfor %}
    ],
    "bizid": {{ bk_supplier_id }},
    "cloudid": {{ bk_cloud_id }},
    "dftregid": "{{ region_id }}",
    "dftcityid": "{{ city_id }}",
    "btserver_is_bridge": 0,
    "btserver_is_report": 1
}"""

BTSVR_TEMPLATE = """
{
    "log": "{{ log_path }}",
    "logfilesize": 10,
    "logfilenum": 10,
    "runtimedata": "{{ data_path }}",
    {%- if password_keyfile %}
    "password_keyfile": "{{ setup_path }}/proxy/cert/cert_encrypt.key",
    {%- endif %}
    "cert": "{{ setup_path }}/proxy/cert",
    "alliothread": 8,
    "workerthread": 24,
    "level": "error",
    "filesvrport": {{ file_svr_port }},
    "btportstart": {{ bt_port_start }},
    "btportend": {{ bt_port_end }},
    "dftregid": "{{ region_id }}",
    "dftcityid": "{{ city_id }}",
    "btserver_is_bridge": 0,
    "btserver_is_report": 1,
    "btzkflag": 0,
    "filesvrthriftip": "0.0.0.0",
    "btServerInnerIP": [{"ip": "{{ inner_ip }}", "port": {{ btsvr_thrift_port }}}],
    // 该处填写 PROXY 所在的外网 ip
    "btServerOuterIP": [{"ip": "{{ outer_ip }}", "port": {{ btsvr_thrift_port }}}],

    // 以下填写 gse 所在的外网 ip
    "btfilesvrscfg": [
        {% for gse_outer_ip in btfileserver_outer_ips%}
            {
                "ip": "{{ gse_outer_ip }}",
                "compId": "0",
                "isTransmit": 0,
                "tcpPort": {{ file_svr_port }},
                "thriftPort": {{ btsvr_thrift_port }},
                "btPort": {{ bt_port }},
                "trackerPort": {{ tracker_port }}
            }{% if not loop.last %},{% endif %}
        {% endfor %}
    ],
    "dataid": 1000,
    "bizid": {{ bk_supplier_id }},
    "cloudid": {{ bk_cloud_id }}
}"""

OPTS_TEMPLATE = """
{
    "log": "{{ log_path }}",
    "logfilesize": 10,
    "logfilenum": 10,
    "runtimedata": "{{ data_path }}",
    "password_keyfile": "{{ setup_path }}/proxy/cert/cert_encrypt.key",
    "cert": "{{ setup_path }}/proxy/cert",
    "runmode": 8,
    "level": "info",
    "ping_chunck": 50,
    "ping_timeout": 20,
    "dataserver": [
        {% for gse_outer_ip in dataserver_outer_ips%}
            {
                "ip": "{{ gse_outer_ip }}",
                "port": 58725
            }{% if not loop.last %},{% endif %}
        {% endfor %}
    ],
    "identityip": "{{ inner_ip }}",
    "dataid": 1000,
    "bizid": {{ bk_supplier_id }},
    "cloudid": {{ bk_cloud_id }}
}"""

TRANSIT_TEMPLATE = """
{
    "log": "{{ log_path }}",
    "logfilesize": 10,
    "logfilenum": 10,
    "runtimedata": "{{ data_path }}",
    {%- if password_keyfile %}
    "password_keyfile": "{{ setup_path }}/proxy/cert/cert_encrypt.key",
    {%- endif %}
    "cert": "{{ setup_path }}/proxy/cert",
    "runmode": 4,
    "transitworker": 6,
    "level": "error",
    "bizid": {{ bk_supplier_id }},
    "cloudid": {{ bk_cloud_id }},
    "dataserver": [
        {% for gse_outer_ip in dataserver_outer_ips%}
            {
                "ip": "{{ gse_outer_ip }}",
                "port": {{ data_port }}
            }{% if not loop.last %},{% endif %}
        {% endfor %}
    ],
    "transitserver": [
        {"ip": "{{ inner_ip }}", "port": {{ data_port }}}
    ]
}"""

BSCP_TEMPLATE = """
# 下沉版会话链接服务相关配置
server:
    # 监听地址，IP不可以是本地localhost或0.0.0.0地址
    endpoint:
        ip: {{ ENDPOINT_IP }}
        # 默认59516
        port: {{ ENDPOINT_PORT }}

# 进程配置托管相关配置(本机sidecar模式)
sidecar:
    # 是否开启reload文件通知, 默认false
    fileReloadMode: {{ FILE_RELOAD_MODE }}

    # reload通知文件名称, 默认BSCP.reload
    fileReloadName: {{ FILE_RELOAD_NAME }}

    # 是否开启配置立即拉取, 默认true
    readyPullConfigs: {{ READY_PULL_CONFIGS }}

# 网关(BSCP API Server)相关配置
gateway:
    hostName: {{ GATEWAY_HOSTNAME }}
    # 默认8080
    port: {{ GATEWAY_PORT }}

# 本地实例服务相关配置
instance:
    # 是否开启（不可以和fileReloadMode同时开启）, 默认false
    open: {{ INSSVR_OPEN }}

    # HTTP接口配置
    httpEndpoint:
        # 默认39610
        port: {{ INS_HTTP_ENDPOINT_PORT }}

    # GRPC接口配置
    grpcEndpoint:
        # 默认39611
        port: {{ INS_GRPC_ENDPOINT_PORT }}

# 缓存相关配置
cache:
    # 生效信息文件记录路径, 默认bscp-cache/fcache/
    effectFileCachePath: {{ EFFECT_FILE_CACHE_PATH }}

    # 内容缓存路径, 默认bscp-cache/ccache/
    contentCachePath: {{ CONTENT_CACHE_PATH }}

    # 内容获取中间缓存路径, 默认bscp-cache/lcache/
    linkContentCachePath: {{ LINK_CONTENT_CACHE_PATH }}

    # 内容缓存清理路径, 默认/tmp
    contentExpiredPath: {{ CONTENT_EXPIRED_CACHE_PATH }}

# 日志相关配置
logger:
    # 日志保存路径, 默认bscp-log
    directory: {{ LOG_DIR }}

    # 日志级别, 默认3
    level: {{ LOG_LEVEL }}

    # 日志文件切割保留的最大数量, 默认5
    maxnum: {{ LOG_FILE_MAX_NUM }}

    # 日志文件切割单文件最大大小(MB), 默认200
    maxsize: {{ LOG_FILE_MAX_SIZE }}
"""

PLUGIN_INFO_TEMPLATE = """
{
    "plugin":[
        {
            "plugin_name":"bkbscp-gseplugin",
            "plugin_path":"{{ plugin_path }}",
            "plugin_type": 1,
            "service_id":1024
        }
    ]
}
"""


def is_designated_upstream_servers(host: models.Host):
    """判断是否指定上游节点"""
    # 非直连区域，使用proxy作为上游节点
    if host.bk_cloud_id != constants.DEFAULT_CLOUD:
        return True

    # 直连区域 AIX不支持zk，因此直接指定上游节点
    if host.bk_cloud_id == constants.DEFAULT_CLOUD and host.os_type == constants.OsType.AIX:
        return True

    # 指定了安装通道，直接使用安装通道的上游节点
    if host.install_channel_id:
        return True

    # 其它场景都无需指定上游节点
    return False


def generate_gse_config(bk_cloud_id, filename, node_type, inner_ip):
    host = Host.objects.get(bk_cloud_id=bk_cloud_id, inner_ip=inner_ip)
    agent_config = host.agent_config
    setup_path = agent_config["setup_path"]
    log_path = agent_config["log_path"]
    # 如果没有自定义则使用接入点默认配置
    data_path = host.extra_data.get("data_path") or agent_config["data_path"]

    taskserver_outer_ips = [server["outer_ip"] for server in host.ap.taskserver]
    btfileserver_outer_ips = [server["outer_ip"] for server in host.ap.btfileserver]
    dataserver_outer_ips = [server["outer_ip"] for server in host.ap.dataserver]

    jump_server, upstream_nodes = host.install_channel()
    taskserver_inner_ips = [server for server in upstream_nodes["taskserver"]]
    btfileserver_inner_ips = [server for server in upstream_nodes["btfileserver"]]
    dataserver_inner_ips = [server for server in upstream_nodes["dataserver"]]

    if host.os_type == constants.OsType.WINDOWS:
        path_sep = constants.WINDOWS_SEP
        dataipc = agent_config.get("dataipc", 47000)
    else:
        path_sep = constants.LINUX_SEP
        dataipc = agent_config.get("dataipc", "/var/run/ipc.state.report")

    template = {}
    context = {}
    port_config = host.ap.port_config
    if node_type in ["agent", "pagent"]:
        template = {"agent.conf": AGENT_TEMPLATE, "plugin_info.json": PLUGIN_INFO_TEMPLATE}[filename]
        # 路径使用json.dumps 主要是为了解决Windows路径，如 C:\gse —> C:\\gse

        password_keyfile = path_sep.join([setup_path, "agent", "cert", "cert_encrypt.key"])
        cert = path_sep.join([setup_path, "agent", "cert"])
        proccfg = path_sep.join([setup_path, "agent", "etc", "procinfo.json"])
        procgroupcfg = path_sep.join([setup_path, "agent", "etc", "procgroupinfo.json"])
        alarmcfgpath = path_sep.join([setup_path, "plugins", "etc"])
        plugincfg = path_sep.join([setup_path, "agent", "etc", "plugin_info.json"])
        pluginbin = path_sep.join([setup_path, "agent", "lib"])
        pluginipc = path_sep.join([setup_path, "agent", "data", "ipc.plugin.manage"])  # plugin_info.json 配置
        plugin_path = path_sep.join([setup_path, "agent", "lib", "libbkbscp-gseplugin.so"])
        if host.os_type.lower() == "windows":
            setup_path = json.dumps(setup_path)
            log_path = json.dumps(log_path)
            password_keyfile = json.dumps(password_keyfile)
            cert = json.dumps(cert)
            proccfg = json.dumps(proccfg)
            procgroupcfg = json.dumps(procgroupcfg)
            alarmcfgpath = json.dumps(alarmcfgpath)
            plugincfg = json.dumps(plugincfg)
            pluginbin = json.dumps(pluginbin)
            pluginipc = json.dumps(pluginipc)
        else:
            setup_path = f'"{setup_path}"'
            log_path = f'"{log_path}"'
            password_keyfile = f'"{password_keyfile}"'
            cert = f'"{cert}"'
            proccfg = f'"{proccfg}"'
            procgroupcfg = f'"{procgroupcfg}"'
            alarmcfgpath = f'"{alarmcfgpath}"'
            dataipc = f'"{dataipc}"'
            plugincfg = f'"{plugincfg}"'
            pluginbin = f'"{pluginbin}"'
            pluginipc = f'"{pluginipc}"'

        if settings.GSE_USE_ENCRYPTION:
            zk_auth = GseEncrypted.encrypted(f"{host.ap.zk_account}:{host.ap.zk_password}")
        else:
            zk_auth = f"{host.ap.zk_account}:{host.ap.zk_password}"

        context = {
            "setup_path": setup_path,
            "log_path": log_path,
            "agentip": inner_ip,
            "bk_supplier_id": 0,
            "bk_cloud_id": bk_cloud_id,
            "default_cloud_id": constants.DEFAULT_CLOUD,
            "identityip": inner_ip,
            "region_id": host.ap.region_id,
            "city_id": host.ap.city_id,
            "password_keyfile": False
            if settings.BKAPP_RUN_ENV == constants.BkappRunEnvType.CE.value
            else password_keyfile,
            "cert": cert,
            "proccfg": proccfg,
            "procgroupcfg": procgroupcfg,
            "alarmcfgpath": alarmcfgpath,
            "dataipc": dataipc,
            "plugincfg": plugincfg,
            "pluginbin": pluginbin,
            "pluginipc": pluginipc,
            "zkhost": ",".join(f'{zk_host["zk_ip"]}:{zk_host["zk_port"]}' for zk_host in host.ap.zk_hosts),
            "zkauth": zk_auth if host.ap.zk_account and host.ap.zk_password else "",
            "proxy_servers": [proxy.inner_ip for proxy in host.proxies],
            "peer_exchange_switch_for_agent": host.extra_data.get("peer_exchange_switch_for_agent", 1),
            "bt_speed_limit": host.extra_data.get("bt_speed_limit"),
            "io_port": port_config.get("io_port"),
            "file_svr_port": port_config.get("file_svr_port"),
            "trunk_port": port_config.get("trunk_port"),
            "db_proxy_port": port_config.get("db_proxy_port"),
            "data_port": port_config.get("data_port"),
            "bt_port_start": port_config.get("bt_port_start"),
            "bt_port_end": port_config.get("bt_port_end"),
            "agent_thrift_port": port_config.get("agent_thrift_port"),
            "api_server_port": port_config.get("api_server_port"),
            "proc_port": port_config.get("proc_port"),
            "plugin_path": plugin_path,
            "is_aix": host.os_type == constants.OsType.AIX,
            "taskserver_inner_ips": taskserver_inner_ips,
            "btfileserver_inner_ips": btfileserver_inner_ips,
            "dataserver_inner_ips": dataserver_inner_ips,
            "is_designated_upstream_servers": is_designated_upstream_servers(host),
        }

    if node_type == "proxy":
        # proxy 只能是Linux机器
        template = {
            "btsvr.conf": BTSVR_TEMPLATE,
            "opts.conf": OPTS_TEMPLATE,
            "agent.conf": PROXY_TEMPLATE,
            "transit.conf": TRANSIT_TEMPLATE,
            "plugin_info.json": PLUGIN_INFO_TEMPLATE,
            "dataflow.conf": DATALOFW_TMPLATE,
            "data.conf": DATA_TMPLATE,
        }[filename]

        context = {
            "password_keyfile": False if settings.BKAPP_RUN_ENV == constants.BkappRunEnvType.CE.value else True,
            "setup_path": setup_path,
            "log_path": log_path,
            "data_path": data_path,
            "bk_supplier_id": 0,
            "bk_cloud_id": bk_cloud_id,
            "taskserver_outer_ips": taskserver_outer_ips,
            "btfileserver_outer_ips": btfileserver_outer_ips,
            "dataserver_outer_ips": dataserver_outer_ips,
            "inner_ip": inner_ip,
            "outer_ip": host.outer_ip,
            "proxy_servers": [inner_ip],
            "region_id": host.ap.region_id,
            "city_id": host.ap.city_id,
            "dataipc": dataipc,
            "peer_exchange_switch_for_agent": host.extra_data.get("peer_exchange_switch_for_agent", 1),
            "bt_speed_limit": host.extra_data.get("bt_speed_limit"),
            "io_port": port_config.get("io_port"),
            "file_svr_port": port_config.get("file_svr_port"),
            "data_port": port_config.get("data_port"),
            "data_prometheus_port": port_config.get("data_prometheus_port"),
            "bt_port_start": port_config.get("bt_port_start"),
            "bt_port_end": port_config.get("bt_port_end"),
            "btsvr_thrift_port": port_config.get("btsvr_thrift_port"),
            "bt_port": port_config.get("bt_port"),
            "tracker_port": port_config.get("tracker_port"),
            "plugin_path": f"{setup_path}/proxy/lib/libbkbscp-gseplugin.so",
        }

    context.update(
        {
            "process_status_dataid": settings.GSE_PROCESS_STATUS_DATAID,
            "process_event_dataid": settings.GSE_PROCESS_EVENT_DATAID,
        }
    )
    return nested_render_data(template, context)


def generate_bscp_config(bk_cloud_id, inner_ip):
    host = Host.objects.get(bk_cloud_id=bk_cloud_id, inner_ip=inner_ip)
    bscp_config = host.ap.bscp_config
    context = {
        "ENDPOINT_IP": inner_ip,
        "ENDPOINT_PORT": bscp_config.get("ENDPOINT_PORT", 59516),
        "FILE_RELOAD_MODE": bscp_config.get("FILE_RELOAD_MODE", False),
        "FILE_RELOAD_NAME": bscp_config.get("FILE_RELOAD_NAME", "BSCP.reload"),
        "READY_PULL_CONFIGS": bscp_config.get("READY_PULL_CONFIGS", True),
        "GATEWAY_HOSTNAME": bscp_config.get("GATEWAY_HOSTNAME"),
        "GATEWAY_PORT": bscp_config.get("GATEWAY_PORT", 8080),
        "INSSVR_OPEN": bscp_config.get("INSSVR_OPEN", False),
        "INS_HTTP_ENDPOINT_PORT": bscp_config.get("INS_HTTP_ENDPOINT_PORT", 39610),
        "INS_GRPC_ENDPOINT_PORT": bscp_config.get("INS_GRPC_ENDPOINT_PORT", 39611),
        "EFFECT_FILE_CACHE_PATH": bscp_config.get("EFFECT_FILE_CACHE_PATH", "bscp-cache/fcache/"),
        "CONTENT_CACHE_PATH": bscp_config.get("CONTENT_CACHE_PATH", "bscp-cache/fcache/"),
        "LINK_CONTENT_CACHE_PATH": bscp_config.get("LINK_CONTENT_CACHE_PATH", "bscp-cache/fcache/"),
        "CONTENT_EXPIRED_CACHE_PATH": bscp_config.get("CONTENT_EXPIRED_CACHE_PATH", "/tmp"),
        "LOG_DIR": bscp_config.get("LOG_DIR", "log"),
        "LOG_LEVEL": bscp_config.get("LOG_LEVEL", 3),
        "LOG_FILE_MAX_NUM": bscp_config.get("LOG_FILE_MAX_NUM", 5),
        "LOG_FILE_MAX_SIZE": bscp_config.get("LOG_FILE_MAX_SIZE", 200),
    }
    return nested_render_data(BSCP_TEMPLATE, context)


@login_exempt
@csrf_exempt
def get_gse_config(request):
    """
    @api {POST} /get_gse_config/ 获取配置
    @apiName get_gse_config
    @apiGroup subscription
    """
    data = json.loads(request.body)

    bk_cloud_id = int(data.get("bk_cloud_id"))
    filename = data.get("filename")
    node_type = data.get("node_type")
    inner_ip = data.get("inner_ip")
    token = data.get("token")

    decrypted_token = _decrypt_token(token)
    if inner_ip != decrypted_token["inner_ip"] or bk_cloud_id != decrypted_token["bk_cloud_id"]:
        logger.error(
            "token[{token}] 非法, 请求参数为: {data}, token解析为: {decrypted_token}".format(
                token=token, data=data, decrypted_token=decrypted_token
            )
        )
        raise PermissionError("what are you doing?")

    if filename in ["bscp.yaml"]:
        config = generate_bscp_config(bk_cloud_id, inner_ip)
    else:
        config = generate_gse_config(bk_cloud_id, filename, node_type, inner_ip)

    return HttpResponse(config)


@login_exempt
@csrf_exempt
def report_log(request):
    """
    @api {POST} /report_log/ 上报日志
    @apiName report_log
    @apiGroup subscription
    @apiParam {object} request
    @apiParamExample {Json} 请求参数
    {
        "task_id": "node_id",
        "token": "",
        "logs": [
            {
                "timestamp": "1580870937",
                "level": "INFO",
                "step": "check_deploy_result",
                "log": "gse agent has been deployed successfully",
                "status": "DONE"
            }
        ]
    }
    """
    logger.info(f"[report_log]: {request.body}")
    data = json.loads(str(request.body, encoding="utf8").replace('\\"', "'").replace("\\", "/"))

    token = data.get("token")
    decrypted_token = _decrypt_token(token)

    if decrypted_token.get("task_id") != data["task_id"]:
        logger.error(f"token[{token}] 非法, task_id为:{data['task_id']}, token解析为: {decrypted_token}")
        raise PermissionError("what are you doing?")

    task_service.callback(data["task_id"], data["logs"])
    return JsonResponse({})


@login_exempt
@csrf_exempt
def job_callback(request):
    """
    作业平台回调，回调数据格式为:
    {
        "job_instance_id": 12345,
        "status": 2,
        "step_instance_list": [
            {
                "step_instance_id": 16271,
                "status": 3
            },
            {
                "step_instance_id": 16272,
                "status": 2
            }
        ]
    }
    """
    data = json.loads(request.body)
    logger.info("[job_callback] {}".format(request.body))
    job_sub_map = JobSubscriptionInstanceMap.objects.get(job_instance_id=data["job_instance_id"])
    task_service.callback(job_sub_map.node_id, data)
    return JsonResponse({})


def _decrypt_token(token: str) -> dict:
    """
    解析token
    """
    try:
        token_decrypt = aes_cipher.decrypt(token)
    except Exception as err:
        logger.error(f"{token}解析失败")
        raise err

    inner_ip, bk_cloud_id, task_id, timestamp = token_decrypt.split("|")
    return_value = {
        "inner_ip": inner_ip,
        "bk_cloud_id": int(bk_cloud_id),
        "task_id": task_id,
        "timestamp": timestamp,
    }
    # timestamp 超过1小时，认为是非法请求
    if time.time() - float(timestamp) > 3600:
        logger.error(f"token[{token}] 非法, timestamp超时不符合预期, {return_value}")
        raise PermissionError("what are you doing?")

    return return_value
