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
from apps.node_man import constants, models

from .. import utils

DEFAULT_HOST_ID = 1

DEFAULT_IP = "127.0.0.1"

PROXY_INNER_IP = "1.1.1.1"

AP_MODEL_DATA = {
    "id": 1,
    "name": "默认接入点",
    "ap_type": "system",
    "region_id": "test",
    "city_id": "test",
    "btfileserver": [{"inner_ip": DEFAULT_IP, "outer_ip": DEFAULT_IP}],
    "dataserver": [{"inner_ip": DEFAULT_IP, "outer_ip": DEFAULT_IP}],
    "taskserver": [{"inner_ip": DEFAULT_IP, "outer_ip": DEFAULT_IP}],
    "zk_hosts": [{"zk_ip": DEFAULT_IP, "zk_port": "2181"}],
    "zk_account": "zk_account",
    "zk_password": "zk_password",
    "package_inner_url": f"http://{DEFAULT_IP}:80/download",
    "package_outer_url": f"http://{DEFAULT_IP}:80/download",
    "nginx_path": "",
    "agent_config": {
        "linux": {
            "dataipc": "/var/run/ipc.state.report",
            "log_path": "/var/log/gse",
            "run_path": "/var/run/gse",
            "data_path": "/var/lib/gse",
            "temp_path": "/tmp",
            "setup_path": "/usr/local/gse",
            "hostid_path": "/var/lib/gse/host/hostid",
        },
        "windows": {
            "dataipc": 47000,
            "log_path": "c:\\gse\\logs",
            "run_path": "c:\\gse\\logs",
            "data_path": "c:\\gse\\data",
            "temp_path": "C:\\tmp",
            "setup_path": "c:\\gse",
            "hostid_path": "C:\\gse\\data\\host\\hostid",
        },
    },
    "status": None,
    "description": "GSE默认接入点",
    "is_enabled": True,
    "is_default": True,
    "creator": ["admin"],
    "port_config": constants.GSE_PORT_DEFAULT_VALUE,
    "proxy_package": [
        "gse_client-windows-x86.tgz",
        "gse_client-windows-x86_64.tgz",
        "gse_client-linux-x86.tgz",
        "gse_client-linux-x86_64.tgz",
        "gse_client-aix-powerpc.tgz",
    ],
    "outer_callback_url": f"http://{DEFAULT_IP}:10300/backend",
}


CLOUD_MODEL_DATA = {
    "bk_cloud_id": constants.DEFAULT_CLOUD,
    "bk_cloud_name": constants.DEFAULT_CLOUD_NAME,
    "ap_id": constants.DEFAULT_AP_ID,
    "isp": "Tencent",
    "creator": [utils.DEFAULT_USERNAME],
    "is_visible": True,
    "is_deleted": False,
}

HOST_MODEL_DATA = {
    "bk_host_id": DEFAULT_HOST_ID,
    "bk_biz_id": utils.DEFAULT_BK_BIZ_ID,
    "bk_cloud_id": constants.DEFAULT_CLOUD,
    "inner_ip": DEFAULT_IP,
    "outer_ip": DEFAULT_IP,
    "login_ip": DEFAULT_IP,
    "data_ip": DEFAULT_IP,
    "os_type": constants.OsType.LINUX,
    "cpu_arch": constants.CpuType.x86_64,
    "node_type": constants.NodeType.AGENT,
    "node_from": constants.NodeFrom.NODE_MAN,
    "ap_id": constants.DEFAULT_AP_ID,
    "upstream_nodes": [],
    "is_manual": False,
    "extra_data": {"bt_speed_limit": None, "peer_exchange_switch_for_agent": 1},
}

IDENTITY_MODEL_DATA = {
    "bk_host_id": DEFAULT_HOST_ID,
    "auth_type": constants.AuthType.PASSWORD,
    "account": "root",
    "password": "password",
    "port": 22,
    "key": "password:::key",
    "extra_data": {},
    # 密码保留天数
    "retention": 1,
}


PROCESS_STATUS_MODEL_DATA = {
    "bk_host_id": DEFAULT_HOST_ID,
    "name": models.ProcessStatus.GSE_AGENT_PROCESS_NAME,
    "status": constants.ProcStateType.RUNNING,
    "version": "1.0.0",
    "proc_type": constants.ProcType.AGENT,
    "is_latest": True,
    "source_type": models.ProcessStatus.SourceType.DEFAULT,
}
