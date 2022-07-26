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

from apps.mock_data.node_man_mkd.cloud.api import CLOUD_LIST_RESPONSE
from apps.mock_data.node_man_mkd.host.api import (
    HOST_PROXY_RESPONSE,
    HOST_SEARCH_RESPONSE,
)
from apps.mock_data.node_man_mkd.plugin.api import PLUGIN_SEARCH_RESPONSE


class JobInstallSerializer(serializers.Serializer):
    job_id = serializers.IntegerField(help_text=_("作业任务ID"))
    ip_filter = serializers.ListField(help_text=_("失败的主机信息"))


class JobLogResponseSerializer(serializers.Serializer):
    pass


class JobOperateSerializer(serializers.Serializer):
    job_id = serializers.IntegerField(help_text=_("作业任务ID"))
    job_url = serializers.CharField(help_text=_("作业任务历史跳转URL"))


class HostSearchResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": HOST_SEARCH_RESPONSE}


class HostBizProxyResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": HOST_PROXY_RESPONSE}


class CloudListResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": CLOUD_LIST_RESPONSE}


class PluginSearchResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": PLUGIN_SEARCH_RESPONSE}
