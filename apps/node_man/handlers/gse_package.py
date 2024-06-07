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
from collections import defaultdict
from typing import Any, Dict, List

from django.core.signals import request_finished
from django.db.models import Q, QuerySet
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _

from apps.core.tag.models import Tag
from apps.node_man.constants import (
    BUILT_IN_TAG_NAMES,
    GsePackageCacheKey,
    GsePackageCode,
)
from apps.node_man.models import GsePackageDesc


class GsePackageHandler:
    PROJECT_VERSION__TAGS_MAP = "project_version__tags_map"
    PROJECT__DESCRIPTION_MAP = "project__description_map"

    def __init__(self):
        self._init_caches()

    def _init_caches(self):
        """初始化缓存"""
        self.cache = {
            self.PROJECT_VERSION__TAGS_MAP: defaultdict(list),
            self.PROJECT__DESCRIPTION_MAP: {},
        }

        self.cache_counter = {
            self.PROJECT_VERSION__TAGS_MAP: 0,
            self.PROJECT__DESCRIPTION_MAP: 0,
        }

    def clear_caches(self):
        """清理缓存"""
        self._init_caches()

    def _init_project_version__tags_map(self):
        """初始化项目版本标签映射"""
        for project in GsePackageCode.values():
            tags: QuerySet = self.get_tag_objs(project).values("name", "description", "target_version")

            for tag in tags:
                cache_key = self.get_tags_cache_key(project, tag.pop("target_version"))
                self.cache[self.PROJECT_VERSION__TAGS_MAP][cache_key].append(tag)

        self.cache_counter[self.PROJECT_VERSION__TAGS_MAP] += 1

    def _init_project__description_map(self):
        """初始化项目描述映射"""
        for project in GsePackageCode.values():
            description = GsePackageDesc.objects.filter(project=project).first().description
            cache_key = self.get_description_cache_key(project)
            self.cache[self.PROJECT__DESCRIPTION_MAP][cache_key] = description

        self.cache_counter[self.PROJECT__DESCRIPTION_MAP] += 1

    @classmethod
    def get_tags_cache_key(cls, project: str, version: str) -> str:
        """获取标签缓存key"""
        return f"{GsePackageCacheKey.TAGS_PREFIX.value}:{project}:{version}"

    @classmethod
    def get_description_cache_key(cls, project: str) -> str:
        """获取描述缓存key"""
        return f"{GsePackageCacheKey.DESCRIPTION_PREFIX.value}:{project}"

    @classmethod
    def get_tag_objs(cls, project: str, version: str = None) -> QuerySet:
        """获取标签对象"""
        target_ids = GsePackageDesc.objects.filter(project=project).values_list("id", flat=True)

        if not version:
            return Tag.objects.filter(target_id__in=target_ids)
        return Tag.objects.filter(target_id__in=target_ids, target_version=version)

    def get_tags(
        self,
        project: str,
        version: str,
        enable_tag_separation: bool = False,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        获取标签列表
        enable_tag_separation: 是否需要将标签分割为内置和自定义
        unique: 是否去重
        use_cache: 是否使用缓存
        get_template_tags: 是否获取模板标签，为True代表获取模板标签，否则获取版本标签
        """
        # 频繁调用get_tags时开启use_cache，少量时可不用
        if use_cache:
            if not self.cache_counter[self.PROJECT_VERSION__TAGS_MAP]:
                self._init_project_version__tags_map()

            cache_key = self.get_tags_cache_key(project, version)
            tags = self.cache[self.PROJECT_VERSION__TAGS_MAP].get(cache_key, [])
        else:
            tags = self.get_tag_objs(project, version).values("name", "description")

        return self.handle_tags(tags, enable_tag_separation=enable_tag_separation)

    def get_description(self, project: str, use_cache: bool = True) -> str:
        """获取包描述信息"""
        if use_cache:
            if not self.cache_counter[self.PROJECT__DESCRIPTION_MAP]:
                self._init_project__description_map()

            cache_key: str = self.get_description_cache_key(project)
            return self.cache[self.PROJECT__DESCRIPTION_MAP].get(cache_key, "")

        return GsePackageDesc.objects.filter(project=project).first().description

    def handle_tags(
        self,
        tags: List[Dict[str, str]],
        enable_tag_separation: bool = False,
        tag_description=None,
    ) -> List[Dict[str, Any]]:
        """
        处理标签列表
        tags: 原始标签列表
        enable_tag_separation: 是否需要将标签分割为内置和自定义
        unique: 是否去重
        get_template_tags: 是否获取模板标签，为True代表获取模板标签，否则获取版本标签
        tag_description: 模糊匹配标签描述
        """
        if tag_description:
            tags = [tag for tag in tags if tag_description in tag["description"]]

        if not enable_tag_separation:
            return tags

        built_in_tags, custom_tags = self.split_tags_into_builtin_and_custom(tags)

        parent_tags: List[Dict[str, Any]] = [
            {"name": "builtin", "description": _("内置标签"), "children": built_in_tags},
            {"name": "custom", "description": _("自定义标签"), "children": custom_tags},
        ]

        return [parent_tag for parent_tag in parent_tags if parent_tag.get("children")]

    @classmethod
    def filter_tags(cls, queryset: QuerySet, project: str, tag_names: List[str] = None) -> QuerySet:
        """筛选标签queryset"""
        project__id_map: Dict[str, int] = dict(GsePackageDesc.objects.values_list("project", "id"))
        combined_tag_names_conditions: Q = Q()

        for tag_name in tag_names or []:
            combined_tag_names_conditions |= Q(name__contains=tag_name)

        filter_conditions: Q = Q(target_id=project__id_map.get(project)) & combined_tag_names_conditions

        target_versions: QuerySet = Tag.objects.filter(filter_conditions).values_list("target_version", flat=True)

        return queryset.filter(version__in=target_versions)

    @classmethod
    def split_tags_into_builtin_and_custom(
        cls, tags: List[Dict[str, Any]]
    ) -> (List[Dict[str, Any]], List[Dict[str, Any]]):
        """将标签拆分为内置的和自定义的"""
        built_in_tags, custom_tags = [], []
        for tag in tags:
            if tag["name"] in BUILT_IN_TAG_NAMES:
                built_in_tags.append(tag)
            else:
                custom_tags.append(tag)

        return built_in_tags, custom_tags


@receiver(request_finished)
def clear_gse_package_handler_cache(sender, **kwargs):
    """每次视图结束后清除缓存，保证每次视图获取的都是最新数据"""
    gse_package_handler.clear_caches()


gse_package_handler = GsePackageHandler()
