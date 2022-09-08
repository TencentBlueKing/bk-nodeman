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

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from apps.node_man import constants as node_man_constants
from apps.node_man.handlers import cmdb

from .. import constants, exceptions, types


class PermissionSer(serializers.Serializer):
    action = serializers.ChoiceField(
        help_text=_("权限类型"),
        choices=node_man_constants.IAM_ACTION_CHOICES,
        default=node_man_constants.IamActionType.agent_view,
    )


class PaginationSer(serializers.Serializer):
    start = serializers.IntegerField(help_text=_("数据起始位置"), required=False, default=0)
    page_size = serializers.IntegerField(
        help_text=_("拉取数据数量，不传或传 `-1` 表示拉取所有"),
        required=False,
        min_value=constants.CommonEnum.PAGE_RETURN_ALL_FLAG.value,
        max_value=500,
        default=constants.CommonEnum.PAGE_RETURN_ALL_FLAG.value,
    )


class ScopeSer(serializers.Serializer):
    scope_type = serializers.ChoiceField(help_text=_("资源范围类型"), choices=constants.ScopeType.list_choices())
    scope_id = serializers.CharField(help_text=_("资源范围ID"), min_length=1)
    # 最终只会使用 bk_biz_id
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"), required=False)

    def validate(self, attrs):
        attrs["bk_biz_id"] = int(attrs["scope_id"])
        return attrs


class MetaSer(ScopeSer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))

    def validate(self, attrs):
        return attrs


class TreeNodeSer(serializers.Serializer):
    object_id = serializers.CharField(help_text=_("节点类型ID"))
    instance_id = serializers.IntegerField(help_text=_("节点实例ID"))
    meta = MetaSer()


class HostSearchConditionSer(serializers.Serializer):
    ip = serializers.IPAddressField(label=_("内网IP"), required=False, protocol="ipv4")
    ipv6 = serializers.IPAddressField(label=_("内网IPv6"), required=False, protocol="ipv6")
    os_type = serializers.ChoiceField(label=_("操作系统类型"), required=False, choices=node_man_constants.OS_CHOICES)
    host_name = serializers.CharField(label=_("主机名称"), required=False, min_length=1)
    cloud_name = serializers.CharField(label=_("云区域名称"), required=False, min_length=1)
    alive = serializers.ChoiceField(
        label=_("Agent 存活状态"), required=False, choices=constants.AgentStatusType.list_choices()
    )
    content = serializers.CharField(
        label=_("模糊搜索内容（支持同时对`主机IP`/`主机名`/`操作系统`/`云区域名称`进行模糊搜索"), required=False, min_length=1
    )


class ScopeSelectorBaseSer(PermissionSer):
    all_scope = serializers.BooleanField(help_text=_("是否获取所有资源范围的拓扑结构，默认为 `false`"), required=False, default=False)
    scope_list = serializers.ListField(help_text=_("要获取拓扑结构的资源范围数组"), child=ScopeSer(), default=[], required=False)

    def validate(self, attrs):
        # TODO 提取到 PermissionClass
        user_biz_ids: typing.Set[int] = set(cmdb.CmdbHandler().biz_id_name({"action": attrs["action"]}).keys())
        if not attrs["all_scope"]:
            attrs["scope_list"] = [scope for scope in attrs["scope_list"] if scope["bk_biz_id"] in user_biz_ids]
            return attrs

        scope_list: types.ScopeList = []
        for biz_id in user_biz_ids:
            scope_list.append(
                {"scope_id": str(biz_id), "scope_type": constants.ScopeType.BIZ.value, "bk_biz_id": biz_id}
            )
        attrs["scope_list"] = scope_list
        return attrs


class QueryHostsBaseSer(PermissionSer, PaginationSer):
    search_condition = HostSearchConditionSer(required=False)

    # 适配原代码风格
    conditions = serializers.ListField(label=_("搜索条件"), required=False, child=serializers.DictField())

    def validate(self, attrs):
        attrs = super().validate(attrs)
        search_cond_map: typing.Dict[str, str] = {
            "ip": "inner_ip",
            "inner_ipv6": "inner_ipv6",
            "os_type": "os_type",
            "host_name": "bk_host_name",
            "cloud_name": "query",
            "alive": "status",
            "content": "query",
        }

        conditions: typing.List[types.Condition] = []
        for key, val in attrs.get("search_condition", {}).items():
            cond_key: str = search_cond_map[key]

            if key == "cloud_name":
                # 云区域名暂时只支持模糊搜索
                conditions.append({"key": cond_key, "value": val, "fuzzy_search_fields": ["bk_cloud_id"]})
            elif key == "content":
                conditions.append(
                    {
                        "key": cond_key,
                        "value": val,
                        "fuzzy_search_fields": constants.CommonEnum.DEFAULT_HOST_FUZZY_SEARCH_FIELDS.value
                        + ["os_type"],
                    }
                )
            elif key == "alive":
                # 转为数据库可识别的 Agent 状态
                if val == constants.AgentStatusType.ALIVE.value:
                    cond_vals: typing.List[str] = [node_man_constants.ProcStateType.RUNNING]
                else:
                    cond_vals: typing.List[str] = list(
                        set(node_man_constants.PROC_STATE_TUPLE) - {node_man_constants.ProcStateType.RUNNING}
                    )
                conditions.append({"key": cond_key, "value": cond_vals})
            else:
                conditions.append({"key": cond_key, "value": [val]})
        # 回写查询条件
        attrs["conditions"] = conditions
        return attrs


class HostInfoWithMetaSer(serializers.Serializer):

    meta = MetaSer()
    cloud_id = serializers.IntegerField(help_text=_("云区域 ID"), required=False)
    ip = serializers.IPAddressField(help_text=_("IPv4 协议下的主机IP"), required=False, protocol="ipv4")
    host_id = serializers.IntegerField(help_text=_("主机 ID，优先取 `host_id`，否则取 `ip` + `cloud_id`"), required=False)

    def validate(self, attrs):
        print(attrs)
        if not ("host_id" in attrs or ("ip" in attrs and "cloud_id" in attrs)):
            raise exceptions.SerValidationError(_("请传入 host_id 或者 cloud_id + ip"))
        return attrs
