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
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from rest_framework import filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from apps.generic import ApiMixinModelViewSet as ModelViewSet
from apps.node_man import models
from apps.node_man.permissions import package_manage as pkg_permission
from apps.node_man.serializers import package_manage as pkg_manage
from apps.node_man.utils.filters import GsePackageFilter
from common.utils.drf_utils import swagger_auto_schema

PACKAGE_MANAGE_VIEW_TAGS = ["PKG_Manager"]
PACKAGE_DES_VIEW_TAGS = ["PKG_Desc"]


class PackageManageViewSet(ModelViewSet):
    queryset = models.GsePackages.objects.all()
    # http_method_names = ["get", "post"]
    # ordering_fields = ("module",)
    serializer_class = pkg_manage.PackageSerializer
    permission_classes = (pkg_permission.PackageManagePermission,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filter_class = GsePackageFilter

    @swagger_auto_schema(
        responses={200: pkg_manage.ListResponseSerializer},
        operation_summary="安装包列表",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
    )
    def list(self, request, *args, **kwargs):
        mock_data = {
            "total": 2,
            "list": [
                {
                    "id": 1,
                    "pkg_name": "pkg_name",
                    "version": "1.1.1",
                    "os": "Linux",
                    "cpu_arch": "x86_64",
                    "tags": [{"id": "stable", "name": "稳定版本"}],
                    "creator": "string",
                    "pkg_ctime": "2019-08-24 14:15:22",
                    "is_ready": True,
                },
                {
                    "id": 2,
                    "pkg_name": "pkg_name",
                    "version": "1.1.2",
                    "os": "Linux",
                    "os_cpu_arch": "x86_64",
                    "tags": [{"id": "stable", "name": "稳定版本"}],
                    "creator": "string",
                    "pkg_ctime": "2019-08-24 14:15:22",
                    "is_ready": True,
                },
            ],
        }
        return Response(mock_data)
        # return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="操作类动作：启用/停用",
        body_in=pkg_manage.OperateSerializer,
        responses={200: pkg_manage.PackageSerializer},
        tags=PACKAGE_MANAGE_VIEW_TAGS,
    )
    def update(self, request, validated_data, *args, **kwargs):
        mock_data = {
            "id": 1,
            "pkg_name": "pkg_name",
            "version": "1.1.1",
            "os": "Linux",
            "cpu_arch": "x86_64",
            "tags": [{"id": "stable", "name": "稳定版本"}],
            "creator": "string",
            "pkg_ctime": "2019-08-24 14:15:22",
            "is_ready": True,
        }

        return Response(mock_data)

    @swagger_auto_schema(
        operation_summary="删除安装包",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
    )
    def destroy(self, request, *args, **kwargs):

        return Response()

    @swagger_auto_schema(
        operation_summary="获取快速筛选信息",
        manual_parameters=[
            openapi.Parameter(
                "project", in_=openapi.TYPE_STRING, description="区分gse_agent, gse_proxy", type=openapi.TYPE_STRING
            )
        ],
        tags=PACKAGE_MANAGE_VIEW_TAGS,
    )
    @action(detail=False, methods=["GET"])
    def quick_search_condition(self, request, *args, **kwargs):
        mock_version = [
            {"name": "2.1.8", "id": "2.1.8", "count": 10},
            {"name": "2.1.7", "id": "2.1.7", "count": 10},
            {"name": "ALL", "id": "all", "count": 20},
        ]

        mock_os_cpu_arch = [
            {"name": "Linux_x86_64", "id": "linux_x86_64", "count": 10},
            {"name": "Linux_x86", "id": "linux_x86", "count": 10},
            {"name": "ALL", "id": "all", "count": 20},
        ]

        mock_data = [
            {"name": "操作系统/架构", "id": "os_cpu_arch", "children": mock_os_cpu_arch},
            {"name": "版本号", "id": "version", "children": mock_version},
        ]

        return Response(mock_data)

    @swagger_auto_schema(
        operation_summary="Agent包上传",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
        responses={HTTP_200_OK: pkg_manage.UploadResponseSerializer},
    )
    @action(detail=False, methods=["POST"], serializer_class=pkg_manage.UploadSerializer)
    def upload(self, request):
        # data = self.validated_data
        mock_data = {
            "id": 1,
            "name": "gse_agent.tgz",
            "pkg_size": 100,
        }
        return Response(mock_data)

    @swagger_auto_schema(
        operation_summary="解析Agent包",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
        responses={HTTP_200_OK: pkg_manage.ParseResponseSerializer},
    )
    @action(detail=False, methods=["POST"], serializer_class=pkg_manage.ParseSerializer)
    def parse(self, request):
        mock_data = {
            "description": "test",
            "packages": [
                {
                    "pkg_abs_path": "xxx/xxxxx",
                    "pkg_name": "gseagent_2.1.7_linux_x86_64.tgz",
                    "module": "agent",
                    "version": "2.1.7",
                    "config_templates": [],
                    "os": "x86_64",
                },
                {
                    "pkg_abs_path": "xxx/xxxxx",
                    "pkg_name": "gseagent_2.1.7_linux_x86.tgz",
                    "module": "agent",
                    "version": "2.1.7",
                    "config_templates": [],
                    "os": "x86",
                },
            ],
        }
        return Response(mock_data)

    @swagger_auto_schema(
        operation_summary="创建Agent包注册任务",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
        responses={HTTP_200_OK: pkg_manage.AgentRegisterTaskSerializer},
    )
    @action(detail=False, methods=["POST"], serializer_class=pkg_manage.AgentRegisterSerializer)
    def create_register_task(self, request):
        mock_data = {"job_id": 1}
        return Response(mock_data)

    @swagger_auto_schema(
        operation_summary="查询Agent包注册任务",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
        query_in=pkg_manage.AgentRegisterTaskSerializer,
        responses={HTTP_200_OK: pkg_manage.AgentRegisterTaskResponseSerializer},
    )
    @action(detail=False, methods=["GET"])
    def query_register_task(self, request, validated_data):

        mock_data = {
            "is_finish": True,
            "status": "SUCCESS",
            "message": "",
        }
        return Response(mock_data)

    @swagger_auto_schema(
        operation_summary="获取Agent包标签",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
        responses={HTTP_200_OK: pkg_manage.TagsSerializer(many=True)},
    )
    @action(detail=False, methods=["GET"])
    def tags(self, request):
        # 由tag handler 实现
        mock_data = [
            {
                "id": "builtin",
                "name": "内置标签",
                "children": [
                    {"id": "stable", "name": "稳定版本", "children": []},
                    {"id": "latest", "name": "最新版本", "children": []},
                ],
            },
            {"id": "custom", "name": "自定义标签", "children": [{"id": "custom", "name": "自定义版本", "children": []}]},
        ]
        return Response(mock_data)

    @swagger_auto_schema(
        operation_summary="获取Agent包版本",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
        responses={HTTP_200_OK: pkg_manage.PackageDescResponseSerialiaer},
    )
    @action(detail=False, methods=["GET"])
    def version(self, request):
        mock_data = {
            "total": 10,
            "list": [
                {
                    "id": 1,
                    "version": "2.1.2",
                    "tags": [{"id": "stable", "name": "稳定版本"}],
                    "is_ready": True,
                    "description": "我是描述",
                    "packages": [
                        {
                            "pkg_name": "gseagent-2.1.2.tgz",
                            "tags": [{"id": "stable", "name": "稳定版本"}, {"id": "latest", "name": "最新版本"}],
                        }
                    ],
                }
            ],
        }
        return Response(mock_data)


# class AgentPackageDescViewSet(ModelViewSet):
#     queryset = models.AgentPackageDesc.objects.all()
#     # model = models.Packages
#     # http_method_names = ["get", "post"]
#     # ordering_fields = ("module",)
#     # serializer_class = pkg_manage.PackageSerializer
#     # filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)

#     # filter_fields = ("module", "creator", "is_ready", "version")

#     @swagger_auto_schema(
#         query_in=pkg_manage.PackageDescSearchSerializer,
# responses={200: pkg_manage.PackageDescResponseSerialiaer},
#         operation_summary="Agent版本列表",
#         tags=PACKAGE_DES_VIEW_TAGS,
#     )
#     def list(self, request, *args, **kwargs):

#         mock_data = {
#             "total": 10,
#             "list": [
#                 {
#                     "id": 1,
#                     "version": "2.1.2",
#                     "tags": [{"id": "stable", "name": "稳定版本"}],
#                     "is_ready": True,
#                     "description": "我是描述",
#                     "packages": [
#                         {
#                             "pkg_name": "gseagent-2.1.2.tgz",
#                             "tags": [{"id": "stable", "name": "稳定版本"}, {"id": "latest", "name": "最新版本"}],
#                         }
#                     ],
#                 }
#             ],
#         }
#         return Response(mock_data)
#         # return super().list(request, *args, **kwargs)
