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
import json
import logging
import tarfile
import typing
from collections import defaultdict

from django.http import JsonResponse
from django.utils.translation import ugettext as _
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from rest_framework import filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from apps.backend.agent.artifact_builder import agent, base, proxy
from apps.core.files.storage import get_storage
from apps.generic import ApiMixinModelViewSet as ModelViewSet
from apps.generic import ValidationMixin
from apps.node_man import constants, exceptions, models
from apps.node_man.handlers.plugin_v2 import PluginV2Handler
from apps.node_man.permissions import package_manage as pkg_permission
from apps.node_man.serializers import package_manage as pkg_manage
from apps.node_man.utils.filters import GsePackageFilter
from common.utils.drf_utils import swagger_auto_schema

PACKAGE_MANAGE_VIEW_TAGS = ["PKG_Manager"]
PACKAGE_DES_VIEW_TAGS = ["PKG_Desc"]
logger = logging.getLogger("app")


class PackageManageViewSet(ModelViewSet, ValidationMixin):
    queryset = models.GsePackages.objects.all()
    # http_method_names = ["get", "post"]
    # ordering_fields = ("module",)
    serializer_class = pkg_manage.PackageSerializer
    permission_classes = (pkg_permission.PackageManagePermission,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filter_class = GsePackageFilter

    def dispatch(self, request, *args, **kwargs):
        project = "gse_agent"
        if request.FILES:
            pass
        elif "project" in request.GET:
            project = request.GET["project"]
        elif request.body and "project" in json.loads(request.body):
            project = json.loads(request.body)["project"]
        self.queryset = self.queryset.filter(project=project)
        return super().dispatch(request, *args, **kwargs)

    @swagger_auto_schema(
        responses={200: pkg_manage.ListResponseSerializer},
        operation_summary="安装包列表",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.queryset)
        res = {
            "total": queryset.count(),
            "list": self.paginate_queryset(queryset) if "pagesize" in request.query_params else queryset,
        }
        return Response(pkg_manage.ListResponseSerializer(res).data)

    @swagger_auto_schema(
        operation_summary="操作类动作：启用/停用",
        body_in=pkg_manage.OperateSerializer,
        responses={200: pkg_manage.PackageSerializer},
        tags=PACKAGE_MANAGE_VIEW_TAGS,
    )
    def update(self, request, validated_data, *args, **kwargs):
        instance = self.get_object()
        serializer = pkg_manage.OperateSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        updated_instance = self.get_object()

        return Response(pkg_manage.PackageSerializer(updated_instance).data)

    @swagger_auto_schema(
        operation_summary="删除安装包",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
    )
    def destroy(self, request, *args, **kwargs):
        return super(PackageManageViewSet, self).destroy(request, *args, **kwargs)

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
        gse_packages = pkg_manage.QuickFilterConditionPackageSerializer(self.queryset, many=True).data
        version_set, os_cpu_arch_set = set(), set()
        version_count_map, os_cpu_arch_count_map = defaultdict(int), defaultdict(int)
        if gse_packages:
            for gse_package in gse_packages:
                version, os, cpu_arch = gse_package.get("version"), gse_package.get("os"), gse_package.get("cpu_arch")
                os_cpu_arch = f"{os}_{cpu_arch}"

                version_set.add(version)
                os_cpu_arch_set.add(os_cpu_arch)

                version_count_map[version] += 1
                version_count_map["ALL"] += 1
                os_cpu_arch_count_map[os_cpu_arch] += 1
                os_cpu_arch_count_map["ALL"] += 1
            version_set.add("ALL")
            os_cpu_arch_set.add("ALL")

        return Response(
            [
                {
                    "name": "操作系统/架构",
                    "id": "os_cpu_arch",
                    "children": [
                        {
                            "id": os_cpu_arch,
                            "name": os_cpu_arch,
                            "count": os_cpu_arch_count_map[os_cpu_arch],
                        }
                        for os_cpu_arch in os_cpu_arch_set
                    ],
                },
                {
                    "name": "版本号",
                    "id": "version",
                    "children": [
                        {
                            "id": version,
                            "name": version,
                            "count": version_count_map[version],
                        }
                        for version in version_set
                    ],
                },
            ]
        )

    @swagger_auto_schema(
        operation_summary="Agent包上传",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
        responses={HTTP_200_OK: pkg_manage.UploadResponseSerializer},
    )
    @action(detail=False, methods=["POST"], serializer_class=pkg_manage.UploadSerializer)
    def upload(self, request):
        validated_data = self.validated_data
        result = PluginV2Handler.upload(package_file=validated_data["package_file"], module=validated_data["module"])
        if "result" in result:
            return JsonResponse(result)
        else:
            return Response(result)

    @swagger_auto_schema(
        operation_summary="解析Agent包",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
        responses={HTTP_200_OK: pkg_manage.ParseResponseSerializer},
    )
    @action(detail=False, methods=["POST"], serializer_class=pkg_manage.ParseSerializer)
    def parse(self, request):
        validated_data = self.validated_data
        upload_package_obj = (
            models.UploadPackage.objects.filter(file_name=validated_data["file_name"]).order_by("-upload_time").first()
        )
        if upload_package_obj is None:
            raise exceptions.FileDoesNotExistError(_("找不到请求发布的文件，请确认后重试"))

        file_path = upload_package_obj.file_path

        storage = get_storage()
        if not storage.exists(name=file_path):
            raise exceptions.PluginParseError(_(f"插件不存在: file_path -> {file_path}"))

        with storage.open(name=file_path, mode="rb") as tf_from_storage:
            with tarfile.open(fileobj=tf_from_storage) as tf:
                # todo: 需要判断是否为agent
                # if ... -> proxy
                # elif ... -> agent
                # else -> raise
                if "gse/server" in tf.getnames():
                    project = constants.GsePackageCode.PROXY.value
                    artifact_builder_class: typing.Type[base.BaseArtifactBuilder] = proxy.ProxyArtifactBuilder
                else:
                    project = constants.GsePackageCode.AGENT.value
                    artifact_builder_class: typing.Type[base.BaseArtifactBuilder] = agent.AgentArtifactBuilder

                with artifact_builder_class(initial_artifact_path=file_path) as builder:
                    extract_dir, package_dir_infos = builder.list_package_dir_infos()
                    artifact_meta_info: typing.Dict[str, typing.Any] = builder.get_artifact_meta_info(extract_dir)

        res = {"description": artifact_meta_info.get("changelog"), "packages": package_dir_infos}

        context = {
            "project": project,
            "pkg_name": f"{artifact_meta_info['name']}-{artifact_meta_info['version']}.tgz",
            "version": artifact_meta_info["version"],
        }

        return Response(pkg_manage.ParseResponseSerializer(res, context=context).data)

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
        # mock_data = [
        #     {
        #         "id": "builtin",
        #         "name": "内置标签",
        #         "children": [
        #             {"id": "stable", "name": "稳定版本", "children": []},
        #             {"id": "latest", "name": "最新版本", "children": []},
        #         ],
        #     },
        #     {
        #         "id": "custom",
        #         "name": "自定义标签",
        #         "children": [
        #             {"id": "custom", "name": "自定义版本", "children": []}
        #         ]
        #     },
        # ]
        mock_data = [
            {
                "id": "builtin",
                "name": "内置标签",
                "children": [],
            },
            {
                "id": "custom",
                "name": "自定义标签",
                "children": [],
            },
        ]
        return Response(mock_data)

    @swagger_auto_schema(
        operation_summary="获取Agent包版本",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
        responses={HTTP_200_OK: pkg_manage.PackageDescResponseSerializer},
    )
    @action(detail=False, methods=["GET"])
    def version(self, request):
        # mock_data = {
        #     "total": 10,
        #     "list": [
        #         {
        #             "id": 1,
        #             "version": "2.1.2",
        #             "tags": [{"id": "stable", "name": "稳定版本"}],
        #             "is_ready": True,
        #             "description": "",
        #             "packages": [
        #                 {
        #                     "pkg_name": "gseagent-2.1.2.tgz",
        #                     "tags": [{"id": "stable", "name": "稳定版本1"}, {"id": "latest", "name": "最新版本"}],
        #                 },
        #                 {
        #                     "pkg_name": "gseagent-2.1.2.tgz",
        #                     "tags": [{"id": "stable", "name": "稳定版本2"}, {"id": "latest", "name": "最新版本"}],
        #                 }
        #             ],
        #         }
        #     ],
        # }
        # return Response(mock_data)
        gse_packages = pkg_manage.VersionDescPackageSerializer(self.queryset, many=True).data
        res, version_2_index = [], {}
        for package in gse_packages:
            version = package["version"]
            sub_tags = {"pkg_name": package.pop("pkg_name"), "tags": package["tags"]}

            if version not in version_2_index:
                version_2_index[version] = len(version_2_index)
                package["packages"] = [sub_tags]
                res.append(package)
            else:
                old_package = res[version_2_index[package["version"]]]
                if package["tags"]:
                    old_package["packages"].append(sub_tags)
                old_package["tags"] = list(filter(lambda x: x in package["tags"], old_package["tags"]))

        return Response(res)


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
