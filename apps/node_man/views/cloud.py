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
from apps.node_man.handlers.cloud import CloudHandler
from apps.node_man.handlers.permission import CloudPermission
from apps.node_man.models import Cloud
from apps.node_man.serializers import response
from apps.node_man.serializers.cloud import EditSerializer, ListSerializer
from apps.utils.local import get_request_username

CLOUD_VIEW_TAGS = ["cloud"]


class CloudViewSet(ModelViewSet):
    model = Cloud
    lookup_value_regex = "[0-9.]+"
    permission_classes = (CloudPermission,)

    @swagger_auto_schema(
        operation_id="cloud_list",
        operation_summary="查询管控区域列表",
        query_serializer=ListSerializer(),
        responses={status.HTTP_200_OK: response.CloudListResponseSerializer()},
        tags=CLOUD_VIEW_TAGS,
        extra_overrides={"is_register_apigw": True},
    )
    def list(self, request, *args, **kwargs):
        """
        @api {GET} /cloud/ 查询管控区域列表
        @apiName list_cloud
        @apiGroup Cloud
        """

        self.serializer_class = ListSerializer
        params = self.validated_data

        clouds = CloudHandler().list(params)
        return Response(clouds)

    @swagger_auto_schema(
        operation_summary="查询管控区域详情",
        tags=CLOUD_VIEW_TAGS,
    )
    def retrieve(self, request, *args, **kwargs):
        """
        @api {GET} /cloud/{{pk}}/  查询管控区域详情
        @apiName retrieve_cloud
        @apiGroup Cloud
        @apiSuccessExample {json} 成功返回:
        {
            "bk_cloud_id": 1,
            "bk_cloud_name": "管控区域名称",
            "isp": "tencent",
            "isp_name": "腾讯云",
            "isp_icon": "",
            "ap_id": 1,
            "ap_name": "接入点名称",
            "bk_biz_scope": [1, 2, 3],
        }
        """

        cloud = CloudHandler().retrieve(int(kwargs["pk"]))
        return Response(cloud)

    @swagger_auto_schema(
        operation_id="create_cloud_area",
        operation_summary="创建管控区域",
        tags=CLOUD_VIEW_TAGS,
        extra_overrides={"is_register_apigw": True},
    )
    def create(self, request, *args, **kwargs):
        """
        @api {POST} /cloud/  创建管控区域
        @apiName create_cloud
        @apiGroup Cloud
        @apiDescription ap_id==-1代表自动选择
        @apiParam {String} bk_cloud_name 管控区域名称
        @apiParam {String} isp 云服务商
        @apiParam {Int} ap_id 接入点ID
        @apiParamExample {Json} 请求参数
        {
            "bk_cloud_name": "管控区域名称",
            "isp": "tencent",
            "ap_id": 1,
        }
        @apiSuccessExample {json} 成功返回:
        {
            "bk_cloud_id": 1
        }
        """

        self.serializer_class = EditSerializer
        data = self.validated_data

        result = CloudHandler().create(data, get_request_username())
        return Response(result)

    @swagger_auto_schema(
        operation_summary="编辑管控区域",
        tags=CLOUD_VIEW_TAGS,
    )
    def update(self, request, *args, **kwargs):
        """
        @api {PUT} /cloud/{{pk}}/  编辑管控区域
        @apiName update_cloud
        @apiGroup Cloud
        @apiParam {String} bk_cloud_name 管控区域名称
        @apiParam {String} isp 云服务商
        @apiParam {Int} ap_id 接入点ID
        @apiParam {List} bk_biz_scope 业务范围
        @apiParamExample {Json} 请求参数
        {
            "bk_cloud_name": "管控区域名称",
            "isp": "tencent",
            "ap_id": 1,
        }
        """

        self.serializer_class = EditSerializer
        data = self.validated_data
        bk_cloud_id = int(kwargs["pk"])
        bk_cloud_name = data["bk_cloud_name"]
        isp = data["isp"]
        ap_id = data["ap_id"]
        CloudHandler().update(bk_cloud_id, bk_cloud_name, isp, ap_id)
        return Response({})

    @swagger_auto_schema(
        operation_summary="删除管控区域",
        tags=CLOUD_VIEW_TAGS,
    )
    def destroy(self, request, *args, **kwargs):
        """
        @api {DELETE} /cloud/{{pk}}/  删除管控区域
        @apiName delete_cloud
        @apiGroup Cloud
        """

        CloudHandler().destroy(int(kwargs["pk"]))
        return Response({})

    @swagger_auto_schema(
        operation_summary="查询某主机服务信息",
        tags=CLOUD_VIEW_TAGS,
    )
    @action(detail=True, methods=["GET"], url_path="biz")
    def list_cloud_biz(self, request, pk=None):
        """
        @api {GET} /cloud/{{pk}}/biz/ 查询某主机服务信息
        @apiName list_cloud_biz
        @apiGroup Cloud
        @apiSuccessExample {json} 成功返回:
        {
            "data": [
                53
            ]
        }
        """

        data = CloudHandler().list_cloud_biz(int(pk))
        return Response(data)
