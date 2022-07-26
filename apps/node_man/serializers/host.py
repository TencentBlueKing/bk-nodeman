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
from apps.node_man import constants, tools
from apps.utils import basic


class HostSearchSerializer(serializers.Serializer):
    bk_biz_id = serializers.ListField(label=_("业务ID"), required=False, child=serializers.IntegerField())
    bk_host_id = serializers.ListField(label=_("主机ID"), required=False, child=serializers.IntegerField())
    bk_cloud_id = serializers.ListField(label=_("云区域ID"), required=False, child=serializers.IntegerField())
    version = serializers.ListField(label=_("Agent版本"), required=False, child=serializers.CharField())
    exclude_hosts = serializers.ListField(label=_("跨页全选排除主机"), required=False, child=serializers.IntegerField())
    conditions = serializers.ListField(label=_("搜索条件"), required=False, child=serializers.DictField())
    extra_data = serializers.ListField(label=_("额外信息"), required=False, child=serializers.CharField())
    page = serializers.IntegerField(label=_("当前页数"), required=False, default=1)
    pagesize = serializers.IntegerField(label=_("分页大小"), required=False, default=10)
    only_ip = serializers.BooleanField(label=_("只返回IP"), required=False, default=False)
    running_count = serializers.BooleanField(label=_("正在运行机器数"), required=False, default=False)


class ProxySerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(label=_("云区域ID"), required=True)


class BizProxySerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(label=_("业务ID"), required=True)


class HostUpdateSerializer(serializers.Serializer):
    bk_host_id = serializers.IntegerField(label=_("主机ID"))
    bk_cloud_id = serializers.IntegerField(label=_("云区域ID"), required=False)
    inner_ip = serializers.IPAddressField(label=_("内网IP"), required=False, protocol="ipv4")
    inner_ipv6 = serializers.IPAddressField(label=_("内网IPv6"), required=False, protocol="ipv6")
    outer_ip = serializers.IPAddressField(label=_("外网IP"), required=False, protocol="ipv4")
    outer_ipv6 = serializers.IPAddressField(label=_("外网IPv6"), required=False, protocol="ipv6")
    # 登录 IP & 数据 IP 支持多 IP 协议
    login_ip = serializers.IPAddressField(label=_("登录IP"), required=False, protocol="both")
    data_ip = serializers.IPAddressField(label=_("数据IP"), required=False, protocol="both")
    account = serializers.CharField(label=_("账号"), required=False)
    port = serializers.IntegerField(label=_("端口号"), required=False)
    ap_id = serializers.IntegerField(label=_("接入点ID"), required=False)
    auth_type = serializers.ChoiceField(label=_("认证类型"), choices=list(constants.AUTH_TUPLE), required=False)
    password = serializers.CharField(label=_("密码"), required=False)
    key = serializers.CharField(label=_("秘钥"), required=False)
    peer_exchange_switch_for_agent = serializers.IntegerField(label=_("加速设置"), required=False, default=1)
    bt_speed_limit = serializers.IntegerField(label=_("加速"), required=False)
    data_path = serializers.CharField(label=_("数据文件路径"), required=False)

    def validate(self, attrs):
        rsa_util = tools.HostTools.get_rsa_util()
        fields_need_encrypt = ["password", "key"]
        for field_need_encrypt in fields_need_encrypt:
            if field_need_encrypt not in attrs:
                continue
            attrs[field_need_encrypt] = tools.HostTools.decrypt_with_friendly_exc_handle(
                rsa_util=rsa_util, encrypt_message=attrs[field_need_encrypt], raise_exec=ValidationError
            )
        basic.ipv6_formatter(data=attrs, ipv6_field_names=["inner_ipv6", "outer_ipv6", "login_ip", "data_ip"])
        return attrs


class RemoveSerializer(serializers.Serializer):
    bk_host_id = serializers.ListField(label=_("主机ID"), required=False)
    is_proxy = serializers.BooleanField(label=_("是否针对代理"), required=True)
    bk_biz_id = serializers.ListField(label=_("业务ID"), required=False)
    version = serializers.ListField(label=_("Agent版本"), required=False)
    conditions = serializers.ListField(label=_("搜索条件"), required=False)
    exclude_hosts = serializers.ListField(label=_("跨页全选排除主机"), required=False)

    def validate(self, attrs):

        if attrs.get("exclude_hosts") is not None and attrs.get("bk_host_id") is not None:
            raise ValidationError(_("跨页全选模式下不允许传bk_host_id参数."))

        if attrs.get("exclude_hosts") is not None and attrs["is_proxy"] is True:
            raise ValidationError(_("不允许对代理执行跨页全选模式."))

        if attrs.get("exclude_hosts") is None and attrs.get("bk_host_id") is None:
            raise ValidationError(_("必须选择一种模式(【是否跨页全选】)"))

        return attrs


class SyncCmdbHostSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(label=_("业务ID"), required=True)
