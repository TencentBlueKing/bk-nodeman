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
import logging
import typing
from collections import defaultdict

from django.http import JsonResponse
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from rest_framework import filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from apps.backend.sync_task.constants import SyncTaskType
from apps.core.ipchooser.tools.base import HostQuerySqlHelper
from apps.core.tag.constants import TargetType
from apps.generic import ApiMixinModelViewSet as ModelViewSet
from apps.generic import ValidationMixin
from apps.node_man import constants, models
from apps.node_man.permissions import package_manage as pkg_permission
from apps.node_man.serializers import package_manage as pkg_manage
from apps.node_man.tools.gse_package import GsePackageTools
from apps.node_man.tools.package import PackageTools
from apps.node_man.utils.filters import GsePackageFilter
from common.api import NodeApi
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

    @swagger_auto_schema(
        responses={200: pkg_manage.ListResponseSerializer},
        operation_summary="安装包列表",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
    )
    def list(self, request, *args, **kwargs):
        """
        return: {
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
        """
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
        """
        return: {
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
        """
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
        """
        return: [
            {"name": "操作系统/架构", "id": "os_cpu_arch", "children": [
                {"name": "Linux_x86_64", "id": "linux_x86_64", "count": 10},
                {"name": "Linux_x86", "id": "linux_x86", "count": 10},
                {"name": "ALL", "id": "ALL", "count": 20},
            ]},
            {"name": "版本号", "id": "version", "children": [
                {"name": "2.1.8", "id": "2.1.8", "count": 10},
                {"name": "2.1.7", "id": "2.1.7", "count": 10},
                {"name": "ALL", "id": "ALL", "count": 20},
            ]},
        ]
        """
        gse_packages = pkg_manage.QuickFilterConditionPackageSerializer(self.queryset, many=True).data

        version_count_map = defaultdict(int)
        os_cpu_arch_count_map = defaultdict(int)

        for package in gse_packages:
            version_count_map[package["version"]] += 1
            os_cpu_arch_count_map[f"{package['os']}_{package['cpu_arch']}"] += 1

        response_data = [
            {
                "name": "操作系统/架构",
                "id": "os_cpu_arch",
                "children": [{"id": key, "name": key, "count": value} for key, value in os_cpu_arch_count_map.items()],
            },
            {
                "name": "版本号",
                "id": "version",
                "children": [{"id": key, "name": key, "count": value} for key, value in version_count_map.items()],
            },
        ]

        # 添加ALL
        for item in response_data:
            count_of_children = sum([child_item["count"] for child_item in item["children"]])
            item["children"].append({"id": "ALL", "name": "ALL", "count": count_of_children})

        return Response(response_data)

    @swagger_auto_schema(
        operation_summary="Agent包上传",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
        responses={HTTP_200_OK: pkg_manage.UploadResponseSerializer},
    )
    @action(detail=False, methods=["POST"], serializer_class=pkg_manage.UploadSerializer)
    def upload(self, request):
        """
        return: {
            "id": 116,
            "name": "HR7vt0c_gse_ce-v2.1.3-beta.13.tgz",
            "pkg_size": "336252435"
        }
        """
        request_serializer = self.serializer_class(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        validated_data = request_serializer.validated_data

        # todo: 如果不对upload进行侵入式修改，会存在大量的storage upload和download操作
        res = PackageTools.upload(package_file=validated_data["package_file"], module=TargetType.AGENT.value)

        if "result" in res:
            return JsonResponse(res)
        else:
            return Response(res)

    @swagger_auto_schema(
        operation_summary="解析Agent包",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
        responses={HTTP_200_OK: pkg_manage.ParseResponseSerializer},
    )
    @action(detail=False, methods=["POST"], serializer_class=pkg_manage.ParseSerializer)
    def parse(self, request):
        """
        return: {
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
        """
        validated_data = self.validated_data

        # 获取最新的agent上传包记录
        upload_package_obj = GsePackageTools.get_latest_upload_record(file_name=validated_data["file_name"])

        # 将文件从storage中拉取下来解压到本地
        # todo: 大文件瓶颈，待优化，下载速度巨慢(本地测试37秒接口，35秒耗时在此)
        extract_dir, agent_name = GsePackageTools.extract_gse_package(source_file_path=upload_package_obj.file_path)

        # 区分agent和proxy包
        project, artifact_builder_class = GsePackageTools.distinguish_gse_package(
            extract_dir=extract_dir, agent_name=agent_name
        )

        # 解析包，添加extract_dir之后在builder中不需要再次下载解压
        with artifact_builder_class(
            initial_artifact_path=upload_package_obj.file_path,
            extract_dir=extract_dir,
        ) as builder:
            builder.applied_tmp_dirs.add(extract_dir)
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
        """
        return: {"job_id": 1}
        """
        validated_data = self.validated_data

        response = NodeApi.sync_task_create(
            {
                "task_name": SyncTaskType.REGISTER_GSE_PACKAGE.value,
                "task_params": {
                    "file_name": validated_data["file_name"],
                    "tags": validated_data["tags"],
                },
            }
        )

        return Response(pkg_manage.AgentRegisterTaskSerializer({"task_id": response["task_id"]}).data)

    @swagger_auto_schema(
        operation_summary="查询Agent包注册任务",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
        query_in=pkg_manage.AgentRegisterTaskSerializer,
        responses={HTTP_200_OK: pkg_manage.AgentRegisterTaskResponseSerializer},
    )
    @action(detail=False, methods=["GET"])
    def query_register_task(self, request, validated_data):
        """
        return: {
            "is_finish": True,
            "status": "SUCCESS",
            "message": "",
        }
        """
        validated_data = pkg_manage.AgentRegisterTaskSerializer(request.query_params).data

        return Response(NodeApi.sync_task_status({"task_id": validated_data["task_id"]}))

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
        responses={HTTP_200_OK: pkg_manage.PackageDescResponseSerializer},
    )
    @action(detail=False, methods=["GET"])
    def version(self, request):
        """
        return: {
            "total": 10,
            "list": [
                {
                    "id": 1,
                    "version": "2.1.2",
                    "tags": [{"id": "stable", "name": "稳定版本"}],
                    "is_ready": True,
                    "description": "",
                    "packages": [
                        {
                            "pkg_name": "gseagent-2.1.2.tgz",
                            "tags": [{"id": "stable", "name": "稳定版本1"}, {"id": "latest", "name": "最新版本"}],
                        },
                        {
                            "pkg_name": "gseagent-2.1.2.tgz",
                            "tags": [{"id": "stable", "name": "稳定版本2"}, {"id": "latest", "name": "最新版本"}],
                        }
                    ],
                }
            ],
        }
        """
        gse_packages = pkg_manage.VersionDescPackageSerializer(self.filter_queryset(self.queryset), many=True).data
        res, version_2_index = [], {}
        for new_package in gse_packages:
            version = new_package["version"]

            if version not in version_2_index:
                # 初始化新版本的包
                version_2_index[version] = len(version_2_index)

                # 添加子包
                res.append(new_package)
                continue

            old_package = res[version_2_index[version]]

            # 添加子包
            old_package["packages"].append(new_package["packages"][0])

            # 子包之间标签取交集
            old_package["tags"] = list(filter(lambda x: x in new_package["tags"], old_package["tags"]))

        return Response(res)

    @swagger_auto_schema(
        operation_summary="获取已部署主机数量",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
    )
    @action(detail=False, methods=["POST"], serializer_class=pkg_manage.DeployedAgentCountSerializer)
    def deployed_hosts_count(self, request):
        validated_data = self.validated_data

        items = validated_data["items"]
        project = validated_data["project"]
        if not items:
            return Response()

        # 划分维度到主机和进程
        dimensions = list(items[0].keys())
        host_dimensions = [d for d in dimensions if d in [field.name for field in models.Host._meta.fields]]
        process_dimensions = list(set(dimensions) - set(host_dimensions))

        # 主机筛选条件
        host_kwargs = {f"{dimension}__in": [item[dimension] for item in items] for dimension in host_dimensions}

        # 进程筛选条件
        process_params = {"conditions": [{"key": "status", "value": [constants.ProcStateType.RUNNING]}]}
        for dimension in process_dimensions:
            process_params["conditions"].append({"key": dimension, "value": [item[dimension] for item in items]})

        # 主机和进程连表查询
        host_queryset = HostQuerySqlHelper.multiple_cond_sql(
            params=process_params,
            biz_scope=[],
            need_biz_scope=False,
            is_proxy=False if project == constants.GsePackageCode.AGENT.value else True,
        ).filter(**host_kwargs)

        # 分组统计数量，使用values + annotate分组统计不管用，原因不详
        dimension_2_count = defaultdict(int)
        for host in host_queryset.values(*dimensions):
            dimension_2_count["|".join(host.get(d, "").lower() for d in dimensions)] += 1

        # 填充count到item
        for item in items:
            item["count"] = dimension_2_count.get("|".join(item.get(d, "").lower() for d in dimensions), 0)

        return Response(items)


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
