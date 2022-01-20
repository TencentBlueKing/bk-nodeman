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


class BaseSerializer(serializers.Serializer):
    """
    用于安装节点管理校验
    """

    bk_cloud_id = serializers.IntegerField(label=_("云区域ID"))


class UpdateSerializer(BaseSerializer):
    """
    用于更新安装节点的验证
    """

    name = serializers.CharField(label=_("安装通道名称"))
    jump_servers = serializers.ListField(label=_("跳板机节点"))
    upstream_servers = serializers.DictField(label=_("上游节点"))
