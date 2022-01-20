# _*_ coding: utf-8 _*_
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

from apps.node_man.constants import IAM_ACTION_DICT


class PermissionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        label=_("操作类型"),
        required=True,
        choices=list(IAM_ACTION_DICT.keys()),
    )
    instance_id = serializers.IntegerField(label=_("实例ID"), required=False)
    instance_name = serializers.CharField(label=_("实例名称"), required=False)


class ApplyPermissionSerializer(serializers.Serializer):
    apply_info = PermissionSerializer(label=_("申请权限信息"), many=True, required=True)
