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
import hashlib
import os
import tarfile
import time
from collections import defaultdict
from typing import Any, Dict, List, Type

from django.db.models import QuerySet
from django.utils.translation import ugettext as _

from apps.backend.agent.artifact_builder import agent, proxy
from apps.backend.agent.artifact_builder.base import BaseArtifactBuilder
from apps.core.files.storage import get_storage
from apps.core.tag.constants import TargetType
from apps.core.tag.models import Tag
from apps.node_man import constants, exceptions, models
from apps.node_man.constants import (
    BUILT_IN_TAG_DESCRIPTIONS,
    BUILT_IN_TAG_NAMES,
    TAG_DESCRIPTION_MAP,
    TAG_NAME_MAP,
    CategoryType,
)
from apps.node_man.models import GsePackageDesc


class GsePackageTools:
    @classmethod
    def get_latest_upload_record(cls, file_name: str) -> models.UploadPackage:
        """
        获取最新的agent上传包记录
        :param file_name: agent包文件名
        """
        upload_package_obj: models.UploadPackage = (
            models.UploadPackage.objects.filter(file_name=file_name, module=TargetType.AGENT.value)
            .order_by("-upload_time")
            .first()
        )
        if upload_package_obj is None:
            raise exceptions.FileDoesNotExistError(_("找不到请求发布的文件，请确认后重试"))

        return upload_package_obj

    @classmethod
    def distinguish_gse_package(cls, file_path: str) -> (str, Type[BaseArtifactBuilder]):
        """
        区分agent和proxy包
        :param file_path: 文件路径
        """
        storage = get_storage()
        with storage.open(name=file_path) as fs:
            with tarfile.open(fileobj=fs) as tf:
                directory_members = tf.getmembers()

        for directory in directory_members:
            if directory.name == "gse/server":
                return constants.GsePackageCode.PROXY.value, proxy.ProxyArtifactBuilder
            elif directory.name.startswith("gse/") and constants.AGENT_PATH_RE.match(directory.name[4:]):
                return constants.GsePackageCode.AGENT.value, agent.AgentArtifactBuilder

        raise exceptions.GsePackageUploadError(
            agent_name=os.path.basename(file_path),
            error=_("该agent包无效，" "gse_proxy的gse目录中应该包含server文件夹，" "gse_agent的gse目录中应该包含agent_(os)_(cpu_arch)的文件夹"),
        )

    @classmethod
    def generate_name_by_description(cls, description: str) -> str:
        """
        根据标签的description生成对应唯一的name
        """
        current_time: str = str(time.time())
        unique_string: str = description + current_time
        return hashlib.md5(unique_string.encode("utf-8")).hexdigest()

    @classmethod
    def create_agent_tags(cls, tag_descriptions, project):
        tags: List[Dict[str, str]] = []
        for tag_description in tag_descriptions:
            gse_package_desc_obj, _ = GsePackageDesc.objects.get_or_create(
                project=project, category=CategoryType.official
            )

            if tag_description in BUILT_IN_TAG_NAMES + BUILT_IN_TAG_DESCRIPTIONS:
                # 内置标签，手动指定name和description
                name: str = TAG_NAME_MAP[tag_description]
                tag_description: str = TAG_DESCRIPTION_MAP[tag_description]
            else:
                # 自定义标签，自动生成name
                name: str = GsePackageTools.generate_name_by_description(tag_description)

            tag_queryset: QuerySet = Tag.objects.filter(
                description=tag_description,
                target_id=gse_package_desc_obj.id,
                target_type=TargetType.AGENT.value,
            )
            if tag_queryset.exists():
                tag_obj: Tag = min(tag_queryset, key=lambda x: len(x.name))
            else:
                tag_obj, _ = Tag.objects.update_or_create(
                    defaults={"description": tag_description},
                    name=name,
                    target_id=gse_package_desc_obj.id,
                    target_type=TargetType.AGENT.value,
                )

            tags.append({"name": tag_obj.name, "description": tag_obj.description})

        return tags

    @classmethod
    def get_quick_search_condition(cls, gse_packages: QuerySet) -> List[Dict[str, Any]]:
        version__count_map: Dict[str, int] = defaultdict(int)
        os_cpu_arch__count_map: Dict[str, int] = defaultdict(int)
        version__version_log_map: Dict[str, str] = defaultdict(str)
        os_cpu_arch__version_log_map: Dict[str, str] = defaultdict(str)

        for package in gse_packages.values("version", "os", "cpu_arch", "version_log"):
            version, os_cpu_arch = package["version"], f"{package['os']}_{package['cpu_arch']}"

            version__count_map[version] += 1
            os_cpu_arch__count_map[os_cpu_arch] += 1

            if version not in version__version_log_map:
                version__version_log_map[version] = package["version_log"]

            if os_cpu_arch not in os_cpu_arch__version_log_map:
                os_cpu_arch__version_log_map[os_cpu_arch] = package["version_log"]

        return [
            {
                "name": _("操作系统/架构"),
                "id": "os_cpu_arch",
                "children": [
                    {
                        "id": os_cpu_arch,
                        "name": os_cpu_arch.capitalize(),
                        "count": count,
                        "description": os_cpu_arch__version_log_map[os_cpu_arch],
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
                        "count": count,
                        "description": version__version_log_map[version],
                    }
                    for version, count in version__count_map.items()
                ],
                "count": sum(version__count_map.values()),
            },
        ]
