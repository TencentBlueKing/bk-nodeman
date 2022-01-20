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


class ListSerializer(serializers.Serializer):
    """
    用于云区域列表校验
    """

    with_default_area = serializers.BooleanField(label=_("是否返回直连区域"), required=False, default=False)


class EditSerializer(serializers.Serializer):
    """
    用于创建和更新云区域的验证
    """

    bk_cloud_name = serializers.CharField(label=_("云区域名称"))
    isp = serializers.CharField(label=_("云服务商"))
    ap_id = serializers.IntegerField(label=_("接入点ID"))
