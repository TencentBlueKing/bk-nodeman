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
import django_filters
from django_filters.rest_framework import FilterSet

from apps.node_man.models import GsePackages
from apps.node_man.serializers import package_manage as pkg_manage


class GsePackageFilter(FilterSet):
    tags = django_filters.CharFilter(field_name="tags", method="filter_tags")
    os_cpu_arch = django_filters.CharFilter(field_name="os_cpu_arch", method="filter_os_cpu_arch")
    project = django_filters.CharFilter(field_name="project", method="filter_project")
    created_by = django_filters.CharFilter(field_name="created_by", method="filter_created_by")
    is_ready = django_filters.CharFilter(field_name="is_ready", method="filter_is_ready")
    version = django_filters.CharFilter(field_name="version", method="filter_version")

    def filter_tags(self, queryset, name, value):
        tag_names = self.str_to_list(value)
        package_ids = [
            gse_package.get("id")
            for tag_name in tag_names
            for gse_package in pkg_manage.PackageSerializer(queryset, many=True).data
            if tag_name
            in set(
                children_tag.get("name")
                for parent_tag in gse_package.get("tags")
                for children_tag in parent_tag["children"]
            )
        ]

        return queryset.filter(id__in=package_ids)

    def filter_os_cpu_arch(self, queryset, name, value):
        os_cpu_arch_list = self.str_to_list(value)
        for os_cpu_arch in os_cpu_arch_list:
            os_cpu_arch = os_cpu_arch.split("_", 1)
            if len(os_cpu_arch) != 2:
                continue

            os, cpu_arch = os_cpu_arch[0], os_cpu_arch[1]
            queryset = queryset.filter(os=os, cpu_arch=cpu_arch)
        return queryset

    def filter_project(self, queryset, name, value):
        return queryset.filter(project__in=self.str_to_list(value))

    def filter_created_by(self, queryset, name, value):
        return queryset.filter(created_by__in=self.str_to_list(value))

    def filter_is_ready(self, queryset, name, value):
        return queryset.filter(is_ready__in=self.str_to_list(value, excepted_type="bool"))

    def filter_version(self, queryset, name, value):
        return queryset.filter(version__in=self.str_to_list(value))

    @classmethod
    def str_to_list(cls, s, excepted_type="str"):
        li = [tag_name.replace("&nbsp;", "").strip() for tag_name in s.split(",")]
        if excepted_type == "bool":
            li = [True if v.lower() == "true" else False for v in li]
        return li

    class Meta:
        model = GsePackages
        fields = ["os_cpu_arch", "tags", "project", "created_by", "is_ready", "version"]
