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
from collections import defaultdict
from typing import Any, Dict, List

import django_filters
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import transaction
from django.db.models import Min, Q, QuerySet
from django.http import JsonResponse
from django.utils.translation import get_language
from django.utils.translation import ugettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from drf_yasg import openapi
from rest_framework import filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from apps.backend.sync_task.constants import SyncTaskType
from apps.core.files.storage import get_storage
from apps.core.ipchooser.tools.base import HostQuerySqlHelper
from apps.core.tag.constants import TargetType
from apps.core.tag.models import Tag
from apps.exceptions import ValidationError
from apps.generic import ApiMixinModelViewSet as ModelViewSet
from apps.generic import ValidationMixin
from apps.node_man import constants, exceptions, models
from apps.node_man.constants import STABLE_DESCRIPTION
from apps.node_man.handlers.gse_package import gse_package_handler
from apps.node_man.models import GsePackageDesc, GsePackages, UploadPackage
from apps.node_man.permissions import package_manage as pkg_permission
from apps.node_man.serializers import package_manage as pkg_manage
from apps.node_man.tools.gse_package import GsePackageTools
from apps.node_man.tools.package import PackageTools
from common.api import NodeApi
from common.utils.drf_utils import swagger_auto_schema

PACKAGE_MANAGE_VIEW_TAGS = ["PKG_Manager"]
PACKAGE_DES_VIEW_TAGS = ["PKG_Desc"]
logger = logging.getLogger("app")


class PackageManageOrderingFilterSet(filters.OrderingFilter):
    def get_ordering(self, request, queryset, view):
        # 这里由原来的request.params变为了request.data，其余不变
        params = request.data.get(self.ordering_param)
        if params:
            fields = [param.strip() for param in params.split(",")]
            ordering = self.remove_invalid_fields(queryset, fields, view, request)
            if ordering:
                return ordering

        return self.get_default_ordering(view)

    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)
        if not ordering:
            return queryset

        for field in ordering[::-1]:
            reverse = field.startswith("-")
            if field.lstrip("-") == "version":
                # 版本按这样排 V2.1.6-beta.10 -> [2, 1, 5, 10]
                queryset: List[GsePackages] = sorted(
                    queryset, key=lambda obj: GsePackageTools.extract_numbers(obj.version), reverse=reverse
                )
            else:
                queryset: List[GsePackages] = sorted(
                    queryset, key=lambda obj: getattr(obj, field.lstrip("-")), reverse=reverse
                )

        return queryset


class PackageManageFilterClass(FilterSet):
    os = django_filters.BaseInFilter(field_name="os", lookup_expr="in")
    cpu_arch = django_filters.BaseInFilter(field_name="cpu_arch", lookup_expr="in")
    tag_names = django_filters.BaseInFilter(lookup_expr="in", method="filter_tag_names")
    created_by = django_filters.BaseInFilter(field_name="created_by", lookup_expr="in")
    is_ready = django_filters.CharFilter(field_name="is_ready", method="filter_is_ready")
    version = django_filters.BaseInFilter(field_name="version", lookup_expr="in")
    created_time = django_filters.DateTimeFromToRangeFilter()
    condition = django_filters.Filter(method="filter_condition")

    def filter_tag_names(self, queryset, name, tag_names):
        if "project" not in self.request.data:
            raise ValidationError(_("筛选tag_names时必须传入project"))
        return gse_package_handler.filter_tags(queryset, self.request.data["project"], tag_names=tag_names)

    def filter_condition(self, queryset, name, query_list):
        if not isinstance(query_list, list):
            return queryset

        model_field_query, tag_query = Q(), Q()
        tag_names: List[str] = []

        # 筛选非tag字段
        for query_info in query_list:
            if not isinstance(query_info, dict) or query_info.get("key") != "query" or "value" not in query_info:
                continue

            tag_names.append(query_info["value"])
            for field in ["os", "cpu_arch", "created_by", "is_ready", "version"]:
                model_field_query |= Q(**{f"{field}__icontains": query_info["value"]})

        # 筛选tag字段
        if "project" in self.request.data and tag_names:
            tag_query = Q(
                id__in=gse_package_handler.filter_tags(
                    queryset=queryset, project=self.request.data["project"], tag_names=tag_names
                ).values_list("id", flat=True)
            )

        return queryset.filter(model_field_query | tag_query)

    @staticmethod
    def filter_is_ready(queryset, name, is_ready):
        if is_ready in (True, "True", "true", "1"):
            return queryset.filter(is_ready=True)
        elif is_ready in (False, "False", "false", "0"):
            return queryset.filter(is_ready=False)
        else:
            return queryset.none()

    class Meta:
        model = GsePackages
        fields = ["tag_names", "project", "created_by", "is_ready", "version", "os", "cpu_arch"]


class PackageManageFilterBackend(DjangoFilterBackend):
    def get_filterset_kwargs(self, request, queryset, view):
        return {
            "data": {**request.data, **dict(request.query_params.items())},
            "queryset": queryset,
            "request": request,
        }


class PackageManageViewSet(ValidationMixin, ModelViewSet):
    serializer_class = pkg_manage.PackageSerializer
    permission_classes = (pkg_permission.PackageManagePermission,)
    filter_backends = (PackageManageFilterBackend, filters.SearchFilter, PackageManageOrderingFilterSet)
    filter_class = PackageManageFilterClass
    ordering_fields = ["version", "created_time"]

    def get_queryset(self):
        if self.action not in ["search", "quick_search_condition"]:  # noqa
            self.filter_class = None
        return models.GsePackages.objects.all().order_by("-is_ready")

    @swagger_auto_schema(
        responses={200: pkg_manage.ListResponseSerializer},
        operation_summary="安装包列表",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
    )
    @action(detail=False, methods=["POST"])
    def search(self, request, *args, **kwargs):
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
        return super().list(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save()

        if "tags" not in serializer.validated_data:
            return

        package_obj: GsePackages = self.get_object()
        tags: QuerySet = gse_package_handler.get_tag_objs(package_obj.project, package_obj.version)
        with transaction.atomic():
            # 清空标签，对于内置标签修改版本为空，非内置标签删除，稳定版本标签不可删除
            tags.filter(name__in=["latest", "test"]).update(target_version="")
            tags.exclude(name__in=["latest", "test", "stable"]).delete()

            # 新增标签
            package_desc_obj: GsePackageDesc = GsePackageDesc.objects.get(project=package_obj.project)
            for tag_description in serializer.validated_data["tags"]:
                gse_package_handler.handle_add_tag(
                    tag_description=tag_description,
                    package_obj=package_obj,
                    package_desc_obj=package_desc_obj,
                )

    @swagger_auto_schema(
        operation_summary="操作类动作：启用/停用/修改(新增, 删除)标签",
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
        instance: GsePackages = self.get_object()
        serializer = pkg_manage.OperateSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        updated_instance: GsePackages = self.get_object()

        return Response(pkg_manage.PackageSerializer(updated_instance).data)

    @swagger_auto_schema(
        operation_summary="删除安装包",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
    )
    def destroy(self, request, *args, **kwargs):
        gse_package_obj: GsePackages = self.get_object()

        # 如果最后一个版本的包被清除了，将标签的target_version置空，防止下次上传这个版本的包时留下以前的标签
        if GsePackages.objects.filter(version=gse_package_obj.version).count() == 1:
            Tag.objects.filter(target_version=gse_package_obj.version).update(target_version="")

        return super().destroy(request, *args, **kwargs)

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
            {
                "name": "操作系统/架构",
                "id": "os_cpu_arch",
                "children": [
                    {"name": "Linux_x86_64", "id": "linux_x86_64", "count": 10},
                    {"name": "Linux_x86", "id": "linux_x86", "count": 10},
                    {"name": "ALL", "id": "ALL", "count": 20},
                ]
            },
            {
                "name": "版本号",
                "id": "version",
                "children": [
                    {"name": "2.1.8", "id": "2.1.8", "count": 10},
                    {"name": "2.1.7", "id": "2.1.7", "count": 10},
                    {"name": "ALL", "id": "ALL", "count": 20},
                ]
            },
        ]
        """
        gse_packages = self.filter_queryset(self.get_queryset()).values("version", "os", "cpu_arch", "version_log")

        version__count_map: Dict[str, int] = defaultdict(int)
        os_cpu_arch__count_map: Dict[str, int] = defaultdict(int)

        for package in gse_packages.values("version", "os", "cpu_arch", "version_log"):
            version, os_cpu_arch = package["version"], f"{package['os']}_{package['cpu_arch']}"

            version__count_map[version] += 1
            os_cpu_arch__count_map[os_cpu_arch] += 1

        return Response(
            [
                {
                    "name": _("操作系统/架构"),
                    "id": "os_cpu_arch",
                    "children": [
                        {
                            "id": os_cpu_arch,
                            "name": os_cpu_arch.capitalize(),
                            "count": count,
                        }
                        for os_cpu_arch, count in os_cpu_arch__count_map.items()
                    ],
                    "count": sum(os_cpu_arch__count_map.values()),
                },
                {
                    "name": _("版本号"),
                    "id": "version",
                    "children": [
                        {
                            "id": version,
                            "name": version.capitalize(),
                            "count": version__count_map[version],
                        }
                        # 版本按这样排 V2.1.6-beta.10 -> [2, 1, 5, 10]
                        for version in sorted(version__count_map, reverse=True, key=GsePackageTools.extract_numbers)
                    ],
                    "count": sum(version__count_map.values()),
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

        if validated_data.get("overload"):
            storage = get_storage()
            package_file: InMemoryUploadedFile = validated_data["package_file"]

            # 只选择最新上传的记录
            # 使用contains是因为上传之后得到的文件名前面带有前缀
            # gse_ce-v2.1.3-beta.13.tgz -> HR7vt0c_gse_ce-v2.1.3-beta.13.tgz
            upload_package: UploadPackage = UploadPackage.objects.filter(
                file_name__contains=package_file.name, module=TargetType.AGENT.value
            ).first()

            # 如果需要覆盖，且数据库找得到该记录并且storage存在的情况下，将记录和相对应的包清掉
            if upload_package and storage.exists(name=upload_package.file_path):
                storage.delete(name=upload_package.file_path)
                upload_package.delete()

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
        return Response(NodeApi.agent_parse(self.validated_data))

    @swagger_auto_schema(
        operation_summary="创建Agent包注册任务",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
        responses={HTTP_200_OK: pkg_manage.AgentRegisterTaskSerializer},
    )
    @action(detail=False, methods=["POST"], serializer_class=pkg_manage.AgentRegisterSerializer)
    def create_register_task(self, request):
        """
        return: {"task_id": 1}
        """
        validated_data = self.validated_data

        extra_tag_names: List[str] = [
            tag_info["name"]
            for tag_info in GsePackageTools.create_agent_tags(
                tag_descriptions=validated_data["tag_descriptions"],
                project=validated_data["project"],
            )
        ]
        response = NodeApi.sync_task_create(
            {
                "task_name": SyncTaskType.REGISTER_GSE_PACKAGE.value,
                "task_params": {
                    "file_name": validated_data["file_name"],
                    "tags": validated_data["tags"] + extra_tag_names,
                },
            }
        )

        return Response({"task_id": response["task_id"]})

    @swagger_auto_schema(
        operation_summary="查询Agent包注册任务",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
        responses={HTTP_200_OK: pkg_manage.AgentRegisterTaskResponseSerializer},
    )
    @action(detail=False, methods=["GET"], serializer_class=pkg_manage.AgentRegisterTaskSerializer)
    def query_register_task(self, request):
        """
        return: {
            "is_finish": True,
            "status": "SUCCESS",
            "message": "",
        }
        """

        validated_data = self.validated_data

        task_result = NodeApi.sync_task_status({"task_id": validated_data["task_id"]})

        # 在celery任务中无法获取正确的用户名，当上传成功时，更新用户名
        if task_result["status"] == "SUCCESS":
            GsePackages.objects.filter(version=validated_data["version"]).update(created_by=request.user.username)

        return Response(task_result)

    @swagger_auto_schema(
        operation_summary="获取Agent包标签",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
    )
    @action(detail=False, methods=["GET"], serializer_class=pkg_manage.TagProjectSerializer)
    def tags(self, request):
        """
        return: [
            {
                "name": "builtin",
                "description": "内置标签",
                "children": [
                    {
                        "id": 95,
                        "name": "stable",
                        "description": "稳定版本"
                    },
                    {
                        "id": 96,
                        "name": "latest",
                        "description": "最新版本"
                    },
                    {
                        "id": 97,
                        "name": "test",
                        "description": "测试版本"
                    }
                ]
            },
            {
                "name": "custom",
                "description": "自定义标签",
                "children": [
                    {
                        "id": 145,
                        "name": "custom3",
                        "description": "自定义标签3"
                    },
                    {
                        "id": 146,
                        "name": "custom4",
                        "description": "自定义标签4"
                    },
                    {
                        "id": 147,
                        "name": "custom5",
                        "description": "自定义标签5"
                    }
                ]
            }
        ]
        """
        validated_data = self.validated_data
        try:
            return Response(
                gse_package_handler.handle_tags(
                    tags=list(
                        Tag.objects.filter(target_id=GsePackageDesc.objects.get(project=validated_data["project"]).id)
                        .values("name")
                        .distinct()
                        .annotate(
                            id=Min("id"),
                            description=Min("description"),
                        )
                    ),
                    tag_description=request.query_params.get("tag_description"),
                    enable_tag_separation=True,
                )
            )
        except GsePackageDesc.DoesNotExist:
            raise exceptions.ModelInstanceNotFoundError(model_name="GsePackageDesc")

    @swagger_auto_schema(
        operation_summary="获取Agent包版本",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
    )
    @action(
        detail=False,
        methods=["POST"],
        serializer_class=pkg_manage.VersionQuerySerializer,
        permission_classes=[IsAuthenticated],
    )
    def version(self, request):
        """
        return: {
            "total": 10,
            "list": [
                {
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
        validated_data = self.validated_data

        gse_packages: QuerySet = (
            self.get_queryset()
            .filter(project=validated_data["project"], is_ready=True)
            .values("version", "project", "pkg_name", "os", "cpu_arch", "version_log", "version_log_en")
        )

        language = get_language()

        version__pkg_info_map: Dict[str, Dict[str, Any]] = {}
        max_version_count: int = 0
        default_version: str = ""
        for package in gse_packages:
            version, project, pkg_name = package["version"], package["project"], package["pkg_name"]
            tags: List[Dict[str, Any]] = gse_package_handler.get_tags(
                version=version,
                project=project,
                enable_tag_separation=False,
            )

            # 获取默认标签
            if not default_version and any(tag["description"] == STABLE_DESCRIPTION for tag in tags):
                default_version = version

            # 初始化某个版本的包
            if version not in version__pkg_info_map:
                version__pkg_info_map[version] = {
                    "version": version,
                    "project": project,
                    "packages": [],
                    "tags": tags,
                    "description": package["version_log"] if language == "zh-hans" else package["version_log_en"],
                    "count": 0,
                    "os_choices": set(),
                    "cpu_arch_choices": set(),
                }

            # 累加同个版本包的数量，并统计版本包最大数量
            version__pkg_info_map[version]["count"] += 1
            max_version_count = max(max_version_count, version__pkg_info_map[version]["count"])

            # 聚合操作系统和cpu架构信息
            version__pkg_info_map[version]["os_choices"].add(package["os"])
            version__pkg_info_map[version]["cpu_arch_choices"].add(package["cpu_arch"])

            # 添加小包包名和小包标签信息
            version__pkg_info_map[version]["packages"].append(
                {"pkg_name": pkg_name, "tags": tags, "os": package["os"], "cpu_arch": package["cpu_arch"]}
            )

            # 将上一次的标签和这次的标签取共同的部分
            last_tags: List[Dict[str, Any]] = version__pkg_info_map[version]["tags"]
            if last_tags != tags:
                version__pkg_info_map[version]["tags"] = [tag for tag in last_tags if tag in tags]

        # 按版本排序
        version__pkg_info_map = dict(
            sorted(
                version__pkg_info_map.items(),
                key=lambda version__pkg_info_tuple: GsePackageTools.extract_numbers(version__pkg_info_tuple[0]),
                reverse=True,
            )
        )

        filter_keys = [key for key in ["os", "cpu_arch"] if validated_data.get(key)]
        if filter_keys:
            # 筛选
            version__pkg_version_info_map = {
                version: pkg_version_info
                for version, pkg_version_info in version__pkg_info_map.copy().items()
                if GsePackageTools.match_criteria(pkg_version_info, validated_data, filter_keys)
            }
        else:
            # 不筛选，默认为统一版本，统一版本需要各个系统的包都齐了才能算入
            # 如果count数量不等于包版本最大数量，则说明缺少某些系统的包
            version__pkg_version_info_map = {
                version: pkg_version_info
                for version, pkg_version_info in version__pkg_info_map.copy().items()
                if pkg_version_info["count"] == max_version_count
            }

        machine_latest_version: str = ""
        if validated_data.get("versions", ""):
            machine_latest_version = max(validated_data["versions"], key=GsePackageTools.extract_numbers)
        package_latest_version = list(version__pkg_version_info_map.keys())[0] if version__pkg_version_info_map else ""

        return Response(
            {
                "machine_latest_version": machine_latest_version,
                "package_latest_version": package_latest_version,
                "default_version": default_version,
                "pkg_info": list(version__pkg_version_info_map.values()),
                "versions_count": len(validated_data["versions"]) if validated_data.get("versions") else 0,
            }
        )

    @swagger_auto_schema(
        operation_summary="Agent包版本比较",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
    )
    @action(
        detail=False,
        methods=["POST"],
        serializer_class=pkg_manage.VersionCompareSerializer,
        permission_classes=[IsAuthenticated],
    )
    def version_compare(self, request):
        validated_data = self.validated_data

        extracted_current_version: List[int] = GsePackageTools.extract_numbers(validated_data["current_version"])
        version_to_compares: List[str] = validated_data["version_to_compares"]

        upgrade_count, downgrade_count, no_change_count = 0, 0, 0

        for version_to_compare in version_to_compares:
            if GsePackageTools.extract_numbers(version_to_compare) > extracted_current_version:
                downgrade_count += 1
            elif GsePackageTools.extract_numbers(version_to_compare) < extracted_current_version:
                upgrade_count += 1
            else:
                no_change_count += 1

        return Response(
            {
                "upgrade_count": upgrade_count,
                "downgrade_count": downgrade_count,
                "no_change_count": no_change_count,
            }
        )

    @swagger_auto_schema(
        operation_summary="获取已部署主机数量",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
    )
    @action(detail=False, methods=["POST"], serializer_class=pkg_manage.DeployedAgentCountSerializer)
    def deployed_hosts_count(self, request):
        """
        input: {
            "items": [
                {
                    "os_type": "linux",
                    "version": "3.6.21"
                },
                {
                    "os_type": "windows",
                    "version": "3.6.21"
                },
                {
                    "os_type": "windows",
                    "version": "3.6.22"
                }
            ],
            "project": "gse_agent"
        }

        return: [
            {
                "os_type": "linux",
                "version": "3.6.21",
                "count": 3
            },
            {
                "os_type": "windows",
                "version": "3.6.21",
                "count": 2
            },
            {
                "os_type": "windows",
                "version": "3.6.22",
                "count": 0
            }
        ]
        """
        validated_data = self.validated_data

        items = validated_data["items"]
        project = validated_data["project"]
        if not items:
            return Response()

        # 划分维度到主机和进程
        dimensions: List[str] = list(items[0].keys())
        host_dimensions: List[str] = [d for d in dimensions if d in [field.name for field in models.Host._meta.fields]]
        process_dimensions: List[str] = list(set(dimensions) - set(host_dimensions))

        # 主机筛选条件
        host_kwargs: Dict[str, list] = {
            f"{dimension}__in": [item[dimension] for item in items] for dimension in host_dimensions
        }

        # 进程筛选条件
        process_params: Dict[str, list] = {
            "conditions": [{"key": "status", "value": [constants.ProcStateType.RUNNING]}]
        }
        for dimension in process_dimensions:
            process_params["conditions"].append({"key": dimension, "value": [item[dimension] for item in items]})

        # 主机和进程连表查询
        host_queryset: QuerySet = HostQuerySqlHelper.multiple_cond_sql(
            params=process_params,
            biz_scope=validated_data["biz_scope"],
            need_biz_scope=True if validated_data["biz_scope"] else False,
            is_proxy=False if project == constants.GsePackageCode.AGENT.value else True,
        ).filter(**host_kwargs)

        # 分组统计数量
        dimension__count_map: Dict[str, int] = defaultdict(int)
        for host in host_queryset.values(*dimensions):
            dimension__count_map["|".join(host.get(d, "").lower() for d in dimensions)] += 1

        # 填充count到item
        for item in items:
            item["count"] = dimension__count_map.get("|".join(item.get(d, "").lower() for d in dimensions), 0)

        return Response(items)

    @swagger_auto_schema(
        operation_summary="批量编辑agent标签",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
    )
    @action(detail=False, methods=["POST"], serializer_class=pkg_manage.TagCreateSerializer)
    def create_agent_tags(self, request):
        """
        input: {
            "project": "gse_agent",
            "tag_descriptions": ["stable", "恭喜", "发财"]
        }

        return: [
            {
                "name": "stable",
                "description": "稳定版本"
            },
            {
                "name": "43f5242cbf2181dc8818a9b8c1c48da6",
                "description": "恭喜"
            },
            {
                "name": "7d602b6a7e590b232c9c5d1f871601a4",
                "description": "发财"
            }
        ]
        """
        validated_data = self.validated_data

        return Response(
            data=GsePackageTools.create_agent_tags(
                tag_descriptions=validated_data["tag_descriptions"],
                project=validated_data["project"],
            )
        )
