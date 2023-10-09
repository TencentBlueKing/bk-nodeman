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


class GsePackageFilter(FilterSet):
    tags = django_filters.CharFilter(name="tags", method="filter_tags")
    os_cpu_arch = django_filters.CharFilter(name="os_cpu_arch", method="filter_os_cpu_arch")

    def filter_tags(self, queryset, name, value):
        pass

    def filter_os_cpu_arch(self, queryset, name, value):
        pass

    class Meta:
        model = GsePackages
        fields = ["os_cpu_arch", "tags", "project", "created_by", "is_ready", "version"]
