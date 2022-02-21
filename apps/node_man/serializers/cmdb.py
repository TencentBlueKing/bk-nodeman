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

from apps.node_man.constants import IamActionType


class BizSerializer(serializers.Serializer):
    """
    用于云区域列表校验
    """

    action = serializers.ChoiceField(
        label=_("操作"),
        required=True,
        choices=[
            IamActionType.task_history_view,
            IamActionType.agent_view,
            IamActionType.agent_operate,
            IamActionType.proxy_operate,
            IamActionType.plugin_view,
            IamActionType.plugin_operate,
            IamActionType.strategy_create,
            IamActionType.strategy_view,
        ],
    )


class FetchTopoSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(label=_("业务ID"), required=False)
    action = serializers.CharField(required=False)


class FetchBizServiceTemplateSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(label=_("业务ID"))


class CmdbSearchTopoSerializer(serializers.Serializer):
    kw = serializers.CharField(label=_("搜索关键字"), min_length=1, max_length=256)
    bk_biz_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=0), label=_("业务ID列表"), min_length=1, required=False
    )
    action = serializers.CharField(required=False)
    page = serializers.IntegerField(label=_("当前页数"), required=False, min_value=1)
    pagesize = serializers.IntegerField(label=_("分页大小"), required=False, min_value=1)
