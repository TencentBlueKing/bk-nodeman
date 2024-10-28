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
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.generic import ModelViewSet
from apps.iam import ActionEnum
from apps.node_man.handlers.cmdb import CmdbHandler
from apps.node_man.handlers.host import HostHandler
from apps.node_man.handlers.permission import HostPermission
from apps.node_man.models import Host
from apps.node_man.periodic_tasks import sync_cmdb_host_periodic_task
from apps.node_man.serializers import response
from apps.node_man.serializers.host import (
    BizProxySerializer,
    HostSearchSerializer,
    HostUpdateSerializer,
    ProxySerializer,
    SyncCmdbHostSerializer,
)
from apps.utils.local import get_request_username

HOST_VIEW_TAGS = ["host"]


class HostViewSet(ModelViewSet):
    model = Host
    permission_classes = (HostPermission,)

    @swagger_auto_schema(
        operation_id="list_hosts",
        operation_summary="查询主机列表",
        responses={status.HTTP_200_OK: response.HostSearchResponseSerializer()},
        tags=HOST_VIEW_TAGS,
        extra_overrides={"is_register_apigw": True},
    )
    @action(detail=False, methods=["POST"], serializer_class=HostSearchSerializer)
    def search(self, request):
        """
        @api {POST} /host/search/ 查询主机列表
        @apiName list_host
        @apiGroup Host
        """
        return Response(HostHandler().list(self.validated_data, get_request_username()))

    @swagger_auto_schema(
        operation_id="list_cloud_proxies",
        operation_summary="查询管控区域下有操作权限的proxy列表",
        query_serializer=ProxySerializer(),
        responses={status.HTTP_200_OK: response.HostBizProxyResponseSerializer()},
        tags=HOST_VIEW_TAGS,
        extra_overrides={"is_register_apigw": True},
    )
    @action(detail=False, serializer_class=ProxySerializer)
    def proxies(self, request, *args, **kwargs):
        """
        @api {GET} /host/proxies/ 查询有proxy操作权限的管控区域proxy列表
        @apiName retrieve_cloud_proxies
        @apiGroup Host
        """
        proxies = HostHandler().proxies(self.validated_data["bk_cloud_id"])
        # 用户有proxy操作权限的业务
        user_biz = CmdbHandler().biz_id_name({"action": ActionEnum.PROXY_OPERATE.id})
        for proxy in proxies:
            proxy["permissions"] = {"operate": proxy["bk_biz_id"] in user_biz}

        return Response(proxies)

    @swagger_auto_schema(
        operation_id="list_biz_proxies",
        operation_summary="查询业务下管控区域的proxy集合",
        query_serializer=BizProxySerializer(),
        responses={status.HTTP_200_OK: response.HostBizProxyResponseSerializer()},
        tags=HOST_VIEW_TAGS,
        extra_overrides={"is_register_apigw": True},
    )
    @action(detail=False, serializer_class=BizProxySerializer)
    def biz_proxies(self, request, *args, **kwargs):
        """
        @api {GET} /host/biz_proxies/ 查询业务下管控区域的proxy集合
        @apiName retrieve_biz_proxies
        @apiGroup Host
        """
        return Response(HostHandler().biz_proxies(self.validated_data["bk_biz_id"]))

    @swagger_auto_schema(
        operation_summary="更新Proxy主机信息",
        tags=HOST_VIEW_TAGS,
    )
    @action(detail=False, methods=["POST"], serializer_class=HostUpdateSerializer)
    def update_single(self, request):
        """
        @api {POST} /host/update_single/ 更新Proxy主机信息
        @apiName update_host
        @apiGroup Host
        @apiParam {Int} bk_host_id 主机ID
        @apiParam {Number} [bk_cloud_id] 管控区域ID
        @apiParam {String} [inner_ip] 内网IP
        @apiParam {String} [outer_ip] 外网IP
        @apiParam {String} [login_ip] 登录IP
        @apiParam {String} [data_ip] 数据IP
        @apiParam {String} [account] 账户名
        @apiParam {Int} [ap_id] 接入点ID
        @apiParam {Number} [port] 端口
        @apiParam {String} [auth_type] 认证类型
        @apiParam {String} [password] 密码
        """
        return Response(HostHandler().update_proxy_info(self.validated_data))

    @swagger_auto_schema(
        operation_summary="同步cmdb主机",
        tags=HOST_VIEW_TAGS,
    )
    @action(detail=False, methods=["GET"], serializer_class=SyncCmdbHostSerializer)
    def sync_cmdb_host(self, request):
        sync_cmdb_host_periodic_task(self.validated_data["bk_biz_id"])
        return Response()
