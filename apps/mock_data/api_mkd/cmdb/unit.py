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
import copy

from apps.mock_data.common_unit import host
from apps.node_man import constants

CMDB_HOST_INFO = {
    "bk_host_id": host.DEFAULT_HOST_ID,
    "bk_cloud_id": constants.DEFAULT_CLOUD,
    "bk_host_innerip": host.DEFAULT_IP,
    "bk_host_outerip": "",
}
CMDB_HOST_INFO_WITH_AGENT_ID = {
    "bk_host_id": host.DEFAULT_HOST_ID,
    "bk_cloud_id": constants.DEFAULT_CLOUD,
    "bk_host_innerip": host.DEFAULT_IP,
    "bk_host_outerip": host.DEFAULT_IP,
    "bk_host_innerip_v6": host.DEFAULT_IPv6,
    "bk_host_outerip_v6": host.DEFAULT_IPv6,
    "bk_agent_id": host.BK_AGENT_ID,
}

LIST_HOSTS_WITHOUT_BIZ_RESULT = {"count": 1, "info": [CMDB_HOST_INFO]}

LIST_HOSTS_WITHOUT_BIZ_WITH_AGENT_ID_RESULT = {"count": 1, "info": [CMDB_HOST_INFO_WITH_AGENT_ID]}


def mock_list_host_without_biz_result(*args, **kwargs):
    has_agent_id = kwargs.get("has_agent_id")
    if has_agent_id:
        host_info_template = CMDB_HOST_INFO_WITH_AGENT_ID
    else:
        host_info_template = CMDB_HOST_INFO
    host_infos = []
    check_by_bk_host_id = False
    bk_host_ids = []
    for rule in kwargs["host_property_filter"]["rules"]:
        if rule["field"] == "bk_host_id":
            bk_host_ids = rule["value"]
            check_by_bk_host_id = True
    if check_by_bk_host_id:
        for bk_host_id in bk_host_ids:
            host_info = copy.deepcopy(host_info_template)
            host_info["bk_host_id"] = bk_host_id
            host_infos.append(host_info)
    else:
        host_infos = [host_info_template]
    return {"count": len(host_infos), "info": host_infos}


def mock_list_host_without_biz_without_agent_id_result(*args, **kwargs):
    return mock_list_host_without_biz_result(has_agent_id=False, *args, **kwargs)


def mock_list_host_without_biz_with_agent_id_result(*args, **kwargs):
    return mock_list_host_without_biz_result(has_agent_id=True, *args, **kwargs)
