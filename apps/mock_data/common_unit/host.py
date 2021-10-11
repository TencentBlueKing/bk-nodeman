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
from apps.node_man import constants

from .. import utils

DEFAULT_HOST_ID = 1

DEFAULT_IP = "127.0.0.1"

HOST_MODEL_DATA = {
    "bk_host_id": DEFAULT_HOST_ID,
    "bk_biz_id": utils.DEFAULT_BK_BIZ_NAME,
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
