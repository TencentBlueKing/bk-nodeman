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
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.generic import APIViewSet

from . import permission
from .handlers import host_handler, topo_handler
from .serializers import host_sers, topo_sers

IP_CHOOSER_VIEW_TAGS = ["ipchooser"]


class IpChooserTopoViewSet(APIViewSet):
    URL_BASE_NAME = "ipchooser_topo"

    permission_classes = (permission.IpChooserTopoPermission,)

    @swagger_auto_schema(
        operation_id="ipchooser_topo_trees",
        operation_summary=_("批量获取含各节点主机数量的拓扑树"),
        tags=IP_CHOOSER_VIEW_TAGS,
        request_body=topo_sers.TreesRequestSer(),
        responses={status.HTTP_200_OK: topo_sers.TreesResponseSer()},
        extra_overrides={"is_register_apigw": True},
    )
    @action(methods=["POST"], detail=False, serializer_class=topo_sers.TreesRequestSer)
    def trees(self, request, *args, **kwargs):
        return Response(topo_handler.TopoHandler.trees(scope_list=self.validated_data["scope_list"]))

    @swagger_auto_schema(
        operation_id="ipchooser_topo_query_path",
        operation_summary=_("查询多个节点拓扑路径"),
        tags=IP_CHOOSER_VIEW_TAGS,
        request_body=topo_sers.QueryPathRequestSer(),
        responses={status.HTTP_200_OK: topo_sers.QueryPathResponseSer()},
        extra_overrides={"is_register_apigw": True},
    )
    @action(methods=["POST"], detail=False, serializer_class=topo_sers.QueryPathRequestSer)
    def query_path(self, request, *args, **kwargs):
        return Response(topo_handler.TopoHandler.query_path(node_list=self.validated_data["node_list"]))

    @swagger_auto_schema(
        operation_id="ipchooser_topo_query_hosts",
        operation_summary=_("根据多个拓扑节点与搜索条件批量分页查询所包含的主机信息"),
        tags=IP_CHOOSER_VIEW_TAGS,
        request_body=topo_sers.QueryHostsRequestSer(),
        responses={status.HTTP_200_OK: topo_sers.QueryHostsResponseSer()},
        extra_overrides={"is_register_apigw": True},
    )
    @action(methods=["POST"], detail=False, serializer_class=topo_sers.QueryHostsRequestSer)
    def query_hosts(self, request, *args, **kwargs):
        return Response(
            topo_handler.TopoHandler.query_hosts(
                readable_node_list=self.validated_data["node_list"],
                conditions=self.validated_data["conditions"],
                limit_host_ids=self.validated_data.get("search_limit", {}).get("limit_host_ids"),
                start=self.validated_data["start"],
                page_size=self.validated_data["page_size"],
            )
        )

    @swagger_auto_schema(
        operation_id="ipchooser_topo_query_host_id_infos",
        operation_summary=_("根据多个拓扑节点与搜索条件批量分页查询所包含的主机 ID 信息"),
        tags=IP_CHOOSER_VIEW_TAGS,
        request_body=topo_sers.QueryHostIdInfosRequestSer(),
        responses={status.HTTP_200_OK: topo_sers.QueryHostIdInfosResponseSer()},
        extra_overrides={"is_register_apigw": True},
    )
    @action(methods=["POST"], detail=False, serializer_class=topo_sers.QueryHostIdInfosRequestSer)
    def query_host_id_infos(self, request, *args, **kwargs):
        return Response(
            topo_handler.TopoHandler.query_host_id_infos(
                readable_node_list=self.validated_data["node_list"],
                conditions=self.validated_data["conditions"],
                limit_host_ids=self.validated_data.get("search_limit", {}).get("limit_host_ids"),
                start=self.validated_data["start"],
                page_size=self.validated_data["page_size"],
            )
        )

    @swagger_auto_schema(
        operation_id="ipchooser_topo_agent_statistics",
        operation_summary=_("获取多个拓扑节点的主机 Agent 状态统计信息"),
        tags=IP_CHOOSER_VIEW_TAGS,
        request_body=topo_sers.AgentStatisticsRequestSer(),
        responses={status.HTTP_200_OK: topo_sers.AgentStatisticsRequestSer()},
        extra_overrides={"is_register_apigw": True},
    )
    @action(methods=["POST"], detail=False, serializer_class=topo_sers.AgentStatisticsRequestSer)
    def agent_statistics(self, request, *args, **kwargs):
        return Response(topo_handler.TopoHandler.agent_statistics(readable_node_list=self.validated_data["node_list"]))


class IpChooserHostViewSet(APIViewSet):
    URL_BASE_NAME = "ipchooser_host"

    permission_classes = (permission.IpChooserHostPermission,)

    @swagger_auto_schema(
        operation_id="ipchooser_host_check",
        operation_summary=_("根据用户手动输入的`IP`/`IPv6`/`主机名`/`host_id`等关键字信息获取真实存在的机器信息"),
        tags=IP_CHOOSER_VIEW_TAGS,
        request_body=host_sers.HostCheckRequestSer(),
        responses={status.HTTP_200_OK: host_sers.HostCheckResponseSer()},
        extra_overrides={"is_register_apigw": True},
    )
    @action(methods=["POST"], detail=False, serializer_class=host_sers.HostCheckRequestSer)
    def check(self, request, *args, **kwargs):
        return Response(
            host_handler.HostHandler.check(
                scope_list=self.validated_data["scope_list"],
                limit_host_ids=self.validated_data.get("search_limit", {}).get("limit_host_ids"),
                ip_list=self.validated_data["ip_list"],
                ipv6_list=self.validated_data["ipv6_list"],
                key_list=self.validated_data["key_list"],
            )
        )

    @swagger_auto_schema(
        operation_id="ipchooser_host_details",
        operation_summary=_("根据主机关键信息获取机器详情信息"),
        tags=IP_CHOOSER_VIEW_TAGS,
        request_body=host_sers.HostDetailsRequestSer(),
        responses={status.HTTP_200_OK: host_sers.HostDetailsResponseSer()},
        extra_overrides={"is_register_apigw": True},
    )
    @action(methods=["POST"], detail=False, serializer_class=host_sers.HostDetailsRequestSer)
    def details(self, request, *args, **kwargs):
        return Response(
            host_handler.HostHandler.details(
                scope_list=self.validated_data["scope_list"],
                host_list=self.validated_data["host_list"],
                show_agent_realtime_state=self.validated_data["agent_realtime_state"],
            )
        )
