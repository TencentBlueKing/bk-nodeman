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

from apps.node_man import constants

AGENT_PKG_VERSION = "1.7.16"

AGENT_PKG_HEAD_NAME = "gse_agent_ee"

AGENT_PKG_SUFFIX_NAME = "tgz"

AGENT_PKG_NAME = (
    f"gse_client-{constants.NodeType.AGENT.lower()}-"
    f"{constants.CpuType.x86_64}-{AGENT_PKG_VERSION}.{AGENT_PKG_SUFFIX_NAME}"
)

AGENT_MEDIUM = "test"

AGENT_MEDIUM_DESC = "测试使用"

PROXY_CONFIG_FILE_NAME = "btsrv.conf"

AGENT_CONFIG_FILE_NAME = "agent.conf"

CERT_PKG_NAME = "cert_ee-1.2.5_blueking.tgz"

AGENT_PLATFORM_BIN_FILES = ["gse_agent", "izip", "gsectl", "iunzip"]

PROXY_PLATFORM_BIN_FILES = ["gse_agent", "gse_data", "izip", "gsectl", "iunzip", "gse_btsvr"]

CERT_FILES = [
    "license_prv.key",
    "gse_agent.crt",
    "platform.key",
    "data_platform.cert",
    "data_platform.key",
    "gse_server.key",
    "gseca.crt",
    "passwd.txt",
    "gse_esb_api_client.key",
    "license_cert.cert",
    "gse_server.crt",
    "gse_api_client.key",
    "platform.cert",
    "gse_agent.key",
    "gse_job_api_client.p12",
    "job_ca.crt",
    "job_server.p12",
    "cert_encrypt.key",
    "job_esb_api_client.key",
    "job_esb_api_client.crt",
    "gse_api_client.crt",
    "gse_esb_api_client.crt",
]

AGENT_PLATFORM_DIRS = [
    f"{constants.NodeType.AGENT.lower()}_{os_type.lower()}_{cpu_arch}"
    for os_type in constants.OS_TUPLE
    for cpu_arch in constants.CPU_TUPLE
]

AGENT_CONFIG_TEMPLATE = """
{
    "log":"/var/log/gse",
    "password_keyfile":"{{ bk_gse_agent_home }}/agent/cert/cert_encrypt.key",
    "cert":"{{ bk_gse_agent_home }}/agent/cert",
    "proccfg":"{{ bk_gse_agent_home }}/agent/etc/procinfo.json",
    "procgroupcfg":"{{ bk_gse_agent_home }}/agent/etc/procgroupinfo.json",
    "dbgipc":"{{ bk_gse_agent_home }}/agent/data/ipc.dbg.agent",
    "dataipc":"/var/run/ipc.state.report",
    "runmode":1,
    "alliothread":8,
    "workerthread":24,
    "level":"error",
    "ioport":48668,
    "filesvrport":58925,
    "dataport":58625,
    "btportstart": 60020,
    "btportend": 60030,
    "clean_script_files_beginhour":0,
    "clean_script_files_maxhours":72,
    "clean_script_files_stepcount":100,
    "agentip":"{{ agent_lan_ip }}",
    "identityip":"{{ external_ip }}",
    "hostid_path":"{{ bk_gse_host_id }}",
    "zkhost":"{{ bk_gse_zk_address }} ",
    "zkauth":"{{ bk_gse_zk_auth }}",
    "dftregid":"test",
    "dftcityid":"test"
}
"""

PROXY_BTSVR_CONFIG_TEMPLATE = """
 {
     "log":"/var/log/gse",
     "runtimedata":"/var/lib/gse",
     "password_keyfile":"{{ bk_gse_agent_home }}/proxy/cert/cert_encrypt.key",
     "cert":"{{ bk_gse_agent_home }}/proxy/cert",
     "dbgipc":"{{ bk_gse_agent_home }}/proxy/data/ipc.dbg.btsvr",
     "alliothread":8,
     "workerthread":24,
     "level":"error",
     "filesvrport":58925,
     "btportstart": 60020,
     "btportend": 60030,
     "dftregid":"test",
     "dftcityid":"test",
     "btserver_is_bridge":0,
     "btserver_is_report":1,
     "btzkflag":0,
     "filesvrthriftip":"0.0.0.0",
     "btServerInnerIP":[{"ip":"{{ agent_lan_ip }}","port":58930}],
     // 该处填写 PROXY 所在的外网 ip
     "btServerOuterIP":[ {"ip":"{{ proxy_wan_ip }}","port":58930} ],

     // 以下填写 gse 所在的外网 ip
     "btfilesvrscfg": [
         {"ip":"{{ gse_wan_ip0 }}","compId":"0","isTransmit":0,"tcpPort":58925,"thriftPort":58930,
         "btPort":10020,"trackerPort":10030},
         {"ip":"{{ gse_wan_ip0 }}","compId":"0","isTransmit":0,"tcpPort":58925,"thriftPort":58930,
         "btPort":10020,"trackerPort":10030}
     ],

     "dataid":1000,
     "bizid":{{ biz_id }},
     "cloudid": {{ cloud_id }}
 }"""


AGENT_YAML_CONFIG = f"medium: {AGENT_MEDIUM}\nversion: {AGENT_PKG_VERSION}\ndesc: {AGENT_MEDIUM_DESC}"
