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


class AgentInfoSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(label=_("管控区域ID"))
    inner_ip = serializers.IPAddressField(label=_("内网IP"), protocol="ipv4")


class ProxyInfoSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(label=_("管控区域ID"))
    outer_ip = serializers.IPAddressField(label=_("出口IP"), protocol="ipv4")


class InstallAgentStrategySerializer(serializers.Serializer):
    agent_info = serializers.ListField(label=_("Agent主机信息"), child=AgentInfoSerializer())


class InstallProxyStrategySerializer(serializers.Serializer):
    proxy_info = serializers.ListField(label=_("Proxy主机信息"), child=ProxyInfoSerializer())
