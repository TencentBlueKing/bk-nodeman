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
import random

from apps.mock_data.common_unit import host
from apps.node_man import constants

from ... import utils

CMDB_HOST_INFO = {
    "bk_host_id": host.DEFAULT_HOST_ID,
    "bk_agent_id": "",
    "bk_host_name": "",
    "bk_supplier_account": "0",
    "bk_cloud_id": constants.DEFAULT_CLOUD,
    "bk_addressing": constants.CmdbAddressingType.STATIC.value,
    "bk_host_innerip": host.DEFAULT_IP,
    "bk_host_innerip_v6": host.DEFAULT_IPV6,
    "bk_host_outerip": host.DEFAULT_IP,
    "bk_host_outerip_v6": host.DEFAULT_IPV6,
    "operator": utils.DEFAULT_USERNAME,
    "bk_bak_operator": utils.DEFAULT_USERNAME,
    "bk_cpu_module": "",
    "bk_isp_name": None,
    "bk_os_bit": "",
    "bk_os_name": "",
    "bk_os_type": constants.BK_OS_TYPE[constants.OsType.LINUX],
    "bk_os_version": "",
    "bk_province_name": None,
    "bk_state": None,
    "bk_state_name": None,
}

CMDB_BIZ_INFO = {
    "bk_biz_id": utils.DEFAULT_BK_BIZ_ID,
    "bk_biz_name": utils.DEFAULT_BK_BIZ_NAME,
    "bk_biz_maintainer": utils.DEFAULT_USERNAME,
}

CMDB_HOST_BIZ_RELATION = {
    "bk_host_id": host.DEFAULT_HOST_ID,
    "bk_biz_id": utils.DEFAULT_BK_BIZ_ID,
    "bk_module_id": random.randint(1, 100),
    "bk_set_id": random.randint(1, 100),
    "bk_supplier_account": constants.DEFAULT_SUPPLIER_ID,
}

LIST_HOSTS_WITHOUT_BIZ_DATA = {"count": 1, "info": [CMDB_HOST_INFO]}

SEARCH_BUSINESS_DATA = {"count": 1, "info": [CMDB_BIZ_INFO]}

ADD_HOST_TO_BUSINESS_IDLE_DATA = {"bk_host_ids": [CMDB_HOST_INFO["bk_host_id"]]}

BATCH_UPDATE_HOST_DATA = None
