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
import os
import tarfile

from django.utils.translation import ugettext as _

from apps.backend.agent.artifact_builder import agent, proxy
from apps.core.files.storage import get_storage
from apps.core.tag.constants import TargetType
from apps.node_man import constants, exceptions, models
from apps.utils import files


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
    def extract_gse_package(cls, source_file_path, target_extract_dir=None):
        """
        将文件从storage中拉取下来解压到本地
        :param source_file_path: storage中tar包路径
        :param target_extract_dir: 解压路径
        """
        target_extract_dir = target_extract_dir or files.mk_and_return_tmpdir()
        storage = get_storage()
        with storage.open(name=source_file_path, mode="rb") as tf_from_storage:
            with tarfile.open(fileobj=tf_from_storage) as tf:
                agent_name = tf.name
                tf.extractall(target_extract_dir)

        return target_extract_dir, agent_name

    @classmethod
    def distinguish_gse_package(cls, extract_dir, agent_name):
        """
        区分agent和proxy包
        :param extract_dir: 解压路径
        :param agent_name: 压缩包名字
        """
        gse_directory = os.listdir(extract_dir + "/gse")
        if "server" in gse_directory:
            project = constants.GsePackageCode.PROXY.value
            artifact_builder_class = proxy.ProxyArtifactBuilder
        elif any("agent_" in filename for filename in gse_directory):
            project = constants.GsePackageCode.AGENT.value
            artifact_builder_class = agent.AgentArtifactBuilder
        else:
            raise exceptions.GsePackageUploadError(agent_name=agent_name, error=_("该agent包无效"))

        return project, artifact_builder_class
