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

from django.utils.translation import ugettext_lazy as _

from ..base import BaseApi, DataAPI
from ..domains import GSE_APIGATEWAY_ROOT_V2


class _GseApi(BaseApi):
    MODULE = _("管控平台")

    def __init__(self):
        self.operate_proc = DataAPI(
            method="POST",
            url=GSE_APIGATEWAY_ROOT_V2 + "operate_proc_v2/",
            module=self.MODULE,
            description="进程操作",
        )
        self.operate_proc_multi = DataAPI(
            method="POST",
            url=GSE_APIGATEWAY_ROOT_V2 + "operate_proc_multi/",
            module=self.MODULE,
            description="批量进程操作",
        )
        self.get_proc_operate_result = DataAPI(
            method="POST",
            url=GSE_APIGATEWAY_ROOT_V2 + "get_proc_operate_result_v2/",
            module=self.MODULE,
            description="查询进程操作结果",
        )
        self.get_proc_status = DataAPI(
            method="POST",
            url=GSE_APIGATEWAY_ROOT_V2 + "get_proc_status_v2/",
            module=self.MODULE,
            description="查询进程状态信息",
        )
        self.sync_proc_status = DataAPI(
            method="POST",
            url=GSE_APIGATEWAY_ROOT_V2 + "sync_proc_status/",
            module=self.MODULE,
            description="同步进程状态信息",
        )
        self.update_proc_info = DataAPI(
            method="POST",
            url=GSE_APIGATEWAY_ROOT_V2 + "update_proc_info/",
            module=self.MODULE,
            description="更新进程信息",
        )
        self.get_agent_info = DataAPI(
            method="POST",
            url=GSE_APIGATEWAY_ROOT_V2 + "get_agent_info/",
            module=self.MODULE,
            description="获取Agent版本信息",
        )
        self.get_agent_status = DataAPI(
            method="POST",
            url=GSE_APIGATEWAY_ROOT_V2 + "get_agent_status/",
            module=self.MODULE,
            description="获取Agent状态",
        )
        self.v2_cluster_list_agent_state = DataAPI(
            method="POST",
            url=GSE_APIGATEWAY_ROOT_V2 + "api/v2/cluster/list_agent_state/",
            module=self.MODULE,
            description="GSE2.0-获取Agent状态",
        )
        self.v2_cluster_list_agent_info = DataAPI(
            method="POST",
            url=GSE_APIGATEWAY_ROOT_V2 + "api/v2/cluster/list_agent_info/",
            module=self.MODULE,
            description="GSE2.0-查询Agent详情列表信息",
        )
        self.v2_proc_get_proc_status_v2 = DataAPI(
            method="POST",
            url=GSE_APIGATEWAY_ROOT_V2 + "api/v2/proc/get_proc_status_v2/",
            module=self.MODULE,
            description="GSE2.0-查询进程状态信息",
        )
        self.v2_proc_operate_proc_multi = DataAPI(
            method="POST",
            url=GSE_APIGATEWAY_ROOT_V2 + "api/v2/proc/operate_proc_multi/",
            module=self.MODULE,
            description="GSE2.0-批量进程操作",
        )
        self.v2_proc_get_proc_operate_result_v2 = DataAPI(
            method="POST",
            url=GSE_APIGATEWAY_ROOT_V2 + "api/v2/proc/get_proc_operate_result_v2/",
            module=self.MODULE,
            description="GSE2.0-查询进程操作结果",
        )
        self.v2_proc_upgrade_to_agent_id = DataAPI(
            method="POST",
            url=GSE_APIGATEWAY_ROOT_V2 + "api/v2/proc/upgrade_to_agent_id/",
            module=self.MODULE,
            description="将基于Host IP的配置升级到基于Agent-ID的配置",
        )
