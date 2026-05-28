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
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.utils import basic


class UpstreamServersSerializer(serializers.Serializer):
    """
    上游节点配置序列化器
    """
    taskserver = serializers.ListField(
        child=serializers.CharField(),
        label=_("任务服务器列表"),
        required=False,
        default=[]
    )
    btfileserver = serializers.ListField(
        child=serializers.CharField(),
        label=_("BT文件服务器列表"),
        required=False,
        default=[]
    )
    dataserver = serializers.ListField(
        child=serializers.CharField(),
        label=_("数据服务器列表"),
        required=False,
        default=[]
    )
    
    def validate_taskserver(self, value):
        """校验任务服务器列表"""
        return [basic.exploded_ip(ip) for ip in value]
    
    def validate_btfileserver(self, value):
        """校验BT文件服务器列表"""
        return [basic.exploded_ip(ip) for ip in value]
    
    def validate_dataserver(self, value):
        """校验数据服务器列表"""
        return [basic.exploded_ip(ip) for ip in value]


class BaseSerializer(serializers.Serializer):
    """
    用于安装节点管理校验
    """

    bk_cloud_id = serializers.IntegerField(label=_("管控区域ID"))


class UpdateSerializer(BaseSerializer):
    """
    用于更新安装节点的验证
    """

    name = serializers.CharField(label=_("安装通道名称"))
    jump_servers = serializers.ListField(label=_("跳板机节点"))
    upstream_servers = UpstreamServersSerializer(label=_("上游节点"))
    hidden = serializers.BooleanField(label=_("是否隐藏"), default=False)

    def validate(self, attrs):
        attrs["jump_servers"] = [basic.exploded_ip(jump_server) for jump_server in attrs["jump_servers"]]
        # upstream_servers 的校验已经在 UpstreamServersSerializer 中处理
        return attrs
