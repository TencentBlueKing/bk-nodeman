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

from django.utils.translation import ugettext as _

from apps.backend.agent.artifact_builder import agent, proxy
from apps.core.files.storage import get_storage
from apps.core.tag.constants import TargetType
from apps.node_man import constants, exceptions, models


class GsePackageTools:
    @classmethod
    def get_latest_upload_record(cls, file_name):
        """
        获取最新的agent上传包记录
        :param file_name: agent包文件名
        """
        upload_package_obj = (
            models.UploadPackage.objects.filter(file_name=file_name, module=TargetType.AGENT.value)
            .order_by("-upload_time")
            .first()
        )
        if upload_package_obj is None:
            raise exceptions.FileDoesNotExistError(_("找不到请求发布的文件，请确认后重试"))

        return upload_package_obj

    @classmethod
    def distinguish_gse_package(cls, file_path):
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
    def generate_name_by_description(cls, description: str, return_primary: bool = False) -> str:
        """
        根据标签的description生成对应唯一的name
        """
        current_time: str = str(time.time())
        unique_string: str = description + current_time
        return hashlib.md5(unique_string.encode("utf-8")).hexdigest()
