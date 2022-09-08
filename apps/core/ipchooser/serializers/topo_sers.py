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

from rest_framework import serializers

from ..tests import mock_data
from . import base


class TreesRequestSer(base.ScopeSelectorBaseSer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.API_TOPO_TREES_REQUEST}


class TreesResponseSer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.API_TOPO_TREES_RESPONSE}


class QueryPathRequestSer(base.PermissionSer):
    node_list = serializers.ListField(child=base.TreeNodeSer())

    class Meta:
        swagger_schema_fields = {"example": mock_data.API_TOPO_QUERY_PATH_REQUEST}


class QueryPathResponseSer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.API_TOPO_QUERY_PATH_RESPONSE}


class QueryHostsRequestSer(base.QueryHostsBaseSer):
    node_list = serializers.ListField(child=base.TreeNodeSer())

    class Meta:
        swagger_schema_fields = {"example": mock_data.API_TOPO_QUERY_HOSTS_REQUEST}


class QueryHostsResponseSer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.API_TOPO_QUERY_HOSTS_RESPONSE}


class QueryHostIdInfosRequestSer(QueryHostsRequestSer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.API_TOPO_QUERY_HOST_ID_INFOS_REQUEST}


class QueryHostIdInfosResponseSer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.API_TOPO_QUERY_HOST_ID_INFOS_RESPONSE}


class AgentStatisticsRequestSer(QueryHostsRequestSer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.API_TOPO_QUERY_HOST_ID_INFOS_REQUEST}


class AgentStatisticsResponseSer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.API_TOPO_QUERY_HOST_ID_INFOS_RESPONSE}
