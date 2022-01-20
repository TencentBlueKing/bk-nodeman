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
from rest_framework import serializers

from apps.exceptions import ValidationError
from apps.node_man import constants
from apps.node_man.serializers import base


class NodeSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField()
    bk_inst_id = serializers.IntegerField()
    bk_obj_id = serializers.CharField()


class HostSearchSerializer(serializers.Serializer):
    bk_biz_id = serializers.ListField(label=_("业务ID"), required=False)
    action = serializers.CharField(required=False)
    bk_host_id = serializers.ListField(label=_("主机ID"), required=False)
    conditions = serializers.ListField(label=_("搜索条件"), required=False)
    scope = base.ScopeSerializer(label=_("主机范围"), required=False)
    nodes = serializers.ListField(label=_("拓扑节点列表"), child=NodeSerializer(), required=False)
    page = serializers.IntegerField(label=_("当前页数"), required=False, default=1)
    pagesize = serializers.IntegerField(label=_("分页大小"), required=False, default=10)
    exclude_hosts = serializers.ListField(label=_("跨页全选排除主机"), required=False)
    agent_status_count = serializers.BooleanField(label=_("仅返回Agent统计状态"), required=False, default=False)
    return_all_node_type = serializers.BooleanField(label=_("返回所有节点类型"), required=False, default=True)


class HostAgentStatusSerializer(serializers.Serializer):
    nodes = serializers.ListField(label=_("拓扑节点列表"), child=serializers.DictField(), required=True)
    action = serializers.CharField(required=False, default=constants.IamActionType.agent_view)

    def validate(self, data):
        # 校验节点数据
        for node in data["nodes"]:
            if "bk_biz_id" in node and "bk_inst_id" in node and "bk_obj_id" in node:
                continue
            # 兼容业务节点查询主机
            if "bk_biz_id" in node and node.get("bk_obj_id") == "biz":
                node["bk_inst_id"] = node["bk_biz_id"]
                continue
            raise ValidationError(_("查询节点属性组合必须为(bk_biz_id, bk_inst_id, bk_obj_id)"))
        return data


class NodeCountSerializer(HostAgentStatusSerializer):
    pass
