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

from apps.node_man.constants import GSE_PORT_DEFAULT_VALUE, IamActionType
from apps.node_man.handlers.iam import IamHandler
from apps.node_man.models import AccessPoint
from apps.utils.local import get_request_username


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

    class Meta:
        model = AccessPoint
        exclude = ("zk_password",)


class UpdateOrCreateSerializer(serializers.ModelSerializer):
    """
    创建AP
    """

    class ServersSerializer(serializers.Serializer):
        inner_ip = serializers.CharField(label=_("内网IP"))
        outer_ip = serializers.CharField(label=_("外网IP"))

    class ZKSerializer(serializers.Serializer):
        zk_ip = serializers.CharField(label=_("ZK IP地址"))
        zk_port = serializers.CharField(label=_("ZK 端口"))

    btfileserver = serializers.ListField(child=ServersSerializer())
    dataserver = serializers.ListField(child=ServersSerializer())
    taskserver = serializers.ListField(child=ServersSerializer())
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

    class Meta:
        fields = "__all__"
        model = AccessPoint
