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
from enum import Enum
from typing import Dict

from django.utils.translation import ugettext_lazy as _

from apps.utils.enum import EnhanceEnum


class CommonEnum(EnhanceEnum):
    SEP = ":"
    PAGE_RETURN_ALL_FLAG = -1
    DEFAULT_HOST_FUZZY_SEARCH_FIELDS = ["bk_cloud_id", "inner_ip", "inner_ipv6", "bk_host_name"]
    DEFAULT_HOST_FIELDS = [
        "bk_biz_id",
        "bk_host_id",
        "bk_agent_id",
        "bk_cloud_id",
        "inner_ip",
        "inner_ipv6",
        "bk_host_name",
        "os_type",
        "status",
    ]

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {
            cls.SEP: _("字段分隔符"),
            cls.PAGE_RETURN_ALL_FLAG: _("全量返回标志"),
            cls.DEFAULT_HOST_FUZZY_SEARCH_FIELDS: _("默认模糊查询字段"),
            cls.DEFAULT_HOST_FIELDS: _("主机列表默认返回字段"),
        }


class ScopeType(EnhanceEnum):
    """作用域类型"""

    BIZ = "biz"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.BIZ: _("业务")}


class ObjectType(EnhanceEnum):
    """CMDB 拓扑节点类型"""

    BIZ = "biz"
    SET = "set"
    MODULE = "module"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.BIZ: _("业务"), cls.SET: _("集群"), cls.MODULE: _("模块")}


class AgentStatusType(EnhanceEnum):
    """对外展示的 Agent 状态"""

    ALIVE = 1
    NO_ALIVE = 0

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.ALIVE: _("存活"), cls.NO_ALIVE: _("未存活")}
