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
import re
import tarfile
import time
from typing import Dict, List, Type

from django.utils.translation import ugettext as _

from apps.backend.agent.artifact_builder import agent, proxy
from apps.backend.agent.artifact_builder.base import BaseArtifactBuilder
from apps.core.files.storage import get_storage
from apps.core.tag.constants import TargetType
from apps.core.tag.models import Tag
from apps.node_man import constants, exceptions, models
from apps.node_man.constants import CategoryType
from apps.node_man.models import GsePackageDesc, UploadPackage


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
        :param file_path: agent包文件路径
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

        # 文件解析失败，将上传记录和包都干掉
        storage.delete(name=file_path)
        UploadPackage.objects.filter(file_path=file_path).delete()
        raise exceptions.GsePackageUploadError(
            agent_name=os.path.basename(file_path),
            error=_("该agent包无效，" "gse_proxy的gse目录中应该包含server文件夹，" "gse_agent的gse目录中应该包含agent_(os)_(cpu_arch)的文件夹"),
        )

    @classmethod
    def generate_name_by_description(cls, description: str) -> str:
        """
        根据标签描述生成对应唯一的id
        :param description: agent包标签描述
        """
        current_time: str = str(time.time())
        unique_string: str = description + current_time
        return hashlib.md5(unique_string.encode("utf-8")).hexdigest()

    @classmethod
    def create_agent_tags(cls, tag_descriptions, project):
        """
        根据agent包标签描述列表自动创建或返回已有的标签信息

        :input
        {
            "project": "gse_agent",
            "tag_descriptions": ["aaa", "bbb"]
        }

        :return
        [
            {
                "name": "7188612c63753ec339500e72083fe8ac",
                "description": "aaa"
            },
            {
                "name": "381b9dc36b32195acb53418b588bb99b",
                "description": "bbb"
            }
        ]

        :params tag_descriptions: 标签描述列表
        :params project: gse_agent或gse_proxy

        """
        tags: List[Dict[str, str]] = []
        for tag_description in tag_descriptions:
            gse_package_desc_obj, _ = GsePackageDesc.objects.get_or_create(
                project=project, category=CategoryType.official
            )

            if tag_description in constants.BUILT_IN_TAG_DESCRIPTIONS + constants.BUILT_IN_TAG_NAMES:
                # 内置标签，手动指定name和description
                name: str = constants.TAG_DESCRIPTION__TAG_NAME.get(tag_description, tag_description)
                tag_description = constants.TAG_NAME__TAG_DESCRIPTION.get(tag_description, tag_description)
            else:
                # 自定义标签，自动生成name
                name: str = GsePackageTools.generate_name_by_description(tag_description)

            tag_queryset = Tag.objects.filter(
                description=tag_description,
                target_id=gse_package_desc_obj.id,
                target_type=TargetType.AGENT.value,
            )

            # 如果已存在标签，直接返回已存在的标签，否则创建一个新的标签
            if tag_queryset.exists():
                tag_obj: Tag = tag_queryset.first()
            else:
                tag_obj, _ = Tag.objects.update_or_create(
                    defaults={"description": tag_description},
                    name=name,
                    target_id=gse_package_desc_obj.id,
                    target_type=TargetType.AGENT.value,
                )

            tags.append({"name": tag_obj.name, "description": tag_obj.description})

        return tags

    @staticmethod
    def extract_numbers(s):
        """从字符串中提取所有的数字，并返回它们的整数列表"""
        numbers = re.findall(r"\d+", s)
        return [int(num) for num in numbers]

    @staticmethod
    def compare_version(a, b):
        return GsePackageTools.extract_numbers(a) > GsePackageTools.extract_numbers(b)

    @classmethod
    def match_criteria(cls, pkg_version_info, validated_data, filter_keys):
        for key in filter_keys:
            if key == "os" and validated_data["os"] not in pkg_version_info["os_choices"]:
                return False
            elif key == "cpu_arch" and validated_data["cpu_arch"] not in pkg_version_info["cpu_arch_choices"]:
                return False
        return True
