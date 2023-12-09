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

from apps.backend.subscription.steps.agent_adapter.base import AgentSetupTools
from apps.exceptions import ValidationError
from apps.node_man.constants import (
    GSE_PORT_DEFAULT_VALUE,
    GSE_V2_PORT_DEFAULT_VALUE,
    IamActionType,
    OsType,
)
from apps.node_man.handlers.iam import IamHandler
from apps.node_man.models import AccessPoint
from apps.utils import basic
from apps.utils.local import get_request_username
from env.constants import GseVersion


class ListSerializer(serializers.ModelSerializer):
    """
    AP返回数据
    """

    id = serializers.IntegerField(label=_("接入点ID"))
    name = serializers.CharField(label=_("接入点名称"))
    ap_type = serializers.CharField(label=_("接入点类型"))
    region_id = serializers.CharField(label=_("区域id"))
    city_id = serializers.CharField(label=_("城市id"))
    btfileserver = serializers.JSONField(label=_("GSE BT文件服务器列表"))
    dataserver = serializers.JSONField(label=_("GSE 数据服务器列表"))
    taskserver = serializers.JSONField(label=_("GSE 任务服务器列表"))
    zk_hosts = serializers.JSONField(label=_("ZK服务器列表"))
    zk_account = serializers.CharField(label=_("ZK账号"))
    package_inner_url = serializers.CharField(label=_("安装包内网地址"))
    package_outer_url = serializers.CharField(label=_("安装包外网地址"))
    agent_config = serializers.JSONField(label=_("Agent配置信息"))
    status = serializers.CharField(label=_("接入点状态"))
    description = serializers.CharField(label=_("接入点描述"), allow_blank=True)
    is_enabled = serializers.BooleanField(label=_("是否启用"))
    is_default = serializers.BooleanField(label=_("是否默认接入点，不可删除"))
    proxy_package = serializers.JSONField(label=_("Proxy上的安装包"))
    file_cache_dirs = serializers.SerializerMethodField(label=_("文件缓存目录"))

    def to_representation(self, instance):
        ret = super(ListSerializer, self).to_representation(instance)
        perms = IamHandler().fetch_policy(
            get_request_username(),
            [IamActionType.ap_edit, IamActionType.ap_delete, IamActionType.ap_create, IamActionType.ap_view],
        )
        ret["permissions"] = {
            "edit": ret["id"] in perms[IamActionType.ap_edit],
            "delete": ret["id"] in perms[IamActionType.ap_delete],
            "view": ret["id"] in perms[IamActionType.ap_view],
        }
        return ret

    def get_file_cache_dirs(self, instance):
        is_legacy: bool = instance.gse_version == GseVersion.V1.value
        data_path: str = AgentSetupTools.generate_default_file_cache_dir(
            path=instance.agent_config[OsType.LINUX.lower()]["setup_path"], is_legacy=is_legacy
        )
        return data_path

    class Meta:
        model = AccessPoint
        exclude = ("zk_password",)


class UpdateOrCreateSerializer(serializers.ModelSerializer):
    """
    创建AP
    """

    class ServersSerializer(serializers.Serializer):
        class ServerInnerSerializer(serializers.Serializer):
            inner_ip = serializers.CharField(label=_("内网IP"), required=False)
            inner_ipv6 = serializers.CharField(label=_("内网IPv6"), required=False)
            bk_host_id = serializers.IntegerField(label=_("主机ID"), required=False)

            def validate(self, attrs):
                inner_ip = attrs.get("inner_ip")
                inner_ipv6 = attrs.get("inner_ipv6")
                if not attrs.get("inner_ip") and not attrs.get("inner_ipv6") and not attrs.get("bk_host_id"):
                    raise ValidationError(_("请求参数必须包含 inner_ip inner_ipv6 or bk_host_id"))
                if inner_ip and not basic.is_v4(inner_ip):
                    raise ValidationError(_("请求参数 inner_ip 不是有效的IP地址"))
                if inner_ipv6 and not basic.is_v6(inner_ipv6):
                    raise ValidationError(_("请求参数 inner_ipv6 不是有效的IP 地址"))
                return attrs

        class ServerOuterSerializer(serializers.Serializer):
            outer_ip = serializers.CharField(label=_("外网IP"), required=False)
            outer_ipv6 = serializers.CharField(label=_("外网IPv6"), required=False)
            bk_host_id = serializers.IntegerField(label=_("主机ID"), required=False)

            def validate(self, attrs):
                outer_ip = attrs.get("outer_ip")
                outer_ipv6 = attrs.get("outer_ipv6")
                if not attrs.get("outer_ip") and not attrs.get("outer_ipv6") and not attrs.get("bk_host_id"):
                    raise ValidationError(_("请求参数必须包含 outer_ip outer_ipv6 or bk_host_id"))
                if outer_ip and not basic.is_v4(outer_ip):
                    raise ValidationError(_("请求参数 outer_ip 不是有效的IP地址"))
                if outer_ipv6 and not basic.is_v6(outer_ipv6):
                    raise ValidationError(_("请求参数 outer_ipv6 不是有效的IP 地址"))
                return attrs

        inner_ips = serializers.ListField(label=_("内网IP信息"), required=False, child=ServerInnerSerializer())
        outer_ips = serializers.ListField(label=_("外网IP信息"), required=False, child=ServerOuterSerializer())

        def validate(self, attrs):
            if not attrs.get("inner_ips") and not attrs.get("outer_ips"):
                raise ValidationError(_("请求参数 inner_ips, outer_ips 不可同时为空"))

            for attr in attrs.keys():
                attrs[attr] = list({frozenset(d.items()): d for d in attrs[attr]}.values())

            # 检查是否同时包含 ipv4 和 ipv6
            for attr in attrs.keys():
                v4_attr = attr.replace("ips", "ip")
                v6_attr = attr.replace("ips", "ipv6")
                v4_items = [item for item in attrs[attr] if item.get(v4_attr)]
                v6_items = [item for item in attrs[attr] if item.get(v6_attr)]
                if v4_items and v6_items:
                    raise ValidationError(_(f"{attr} 中不能同时包括 {v4_attr} 和 {v6_attr}"))

            return attrs

    class ZKSerializer(serializers.Serializer):
        zk_ip = serializers.CharField(label=_("ZK IP地址"))
        zk_port = serializers.CharField(label=_("ZK 端口"))

    btfileserver = ServersSerializer()
    dataserver = ServersSerializer()
    taskserver = ServersSerializer()
    zk_hosts = serializers.ListField(child=ZKSerializer())
    zk_account = serializers.CharField(label=_("ZK账号"), required=False, allow_blank=True)
    zk_password = serializers.CharField(label=_("ZK密码"), required=False, allow_blank=True)
    agent_config = serializers.DictField(label=_("Agent配置"))
    description = serializers.CharField(label=_("接入点描述"), allow_blank=True)
    creator = serializers.JSONField(_("接入点创建者"), required=False)
    port_config = serializers.DictField(default=GSE_PORT_DEFAULT_VALUE)
    proxy_package = serializers.ListField()
    bscp_config = serializers.DictField(_("BSCP配置"), required=False)
    outer_callback_url = serializers.CharField(label=_("节点管理外网回调地址"), required=False, allow_blank=True)
    callback_url = serializers.CharField(label=_("节点管理内网回调地址"), required=False, allow_blank=True)

    def validate(self, data):
        gse_version_list: typing.List[str] = list(set(AccessPoint.objects.values_list("gse_version", flat=True)))
        # 存量接入点版本全部为V2新建/更新版本也为V2版本
        if GseVersion.V1.value not in gse_version_list:
            data["gse_version"] = GseVersion.V2.value
            data["port_config"] = GSE_V2_PORT_DEFAULT_VALUE
        return data

    class Meta:
        fields = "__all__"
        model = AccessPoint
