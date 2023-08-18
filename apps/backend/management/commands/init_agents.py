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
from __future__ import absolute_import, unicode_literals

import os
import tarfile
import typing

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.backend.agent.artifact_builder import agent, base, proxy
from apps.core.files.storage import get_storage
from apps.node_man import constants, models
from apps.utils import files
from common.log import logger


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("-c", "--cert_path", help=f"证书目录，默认为 {settings.GSE_CERT_PATH}", type=str)
        parser.add_argument("-d", "--download_path", help=f"归档路径，默认为 {settings.DOWNLOAD_PATH}", type=str)
        parser.add_argument("-o", "--overwrite_version", help="版本号，用于覆盖原始制品内的版本信息", type=str)
        parser.add_argument(
            "-e",
            "--enable_agent_pkg_manage",
            help="是否开启Agent包管理模式, 开启则创建Tag, Template, Evn记录",
            action="store_true",
            default=False,
        )

    def handle(self, *args, **options):
        """
        初始化内置官方插件
        :param args:
        :param options:
        :return: None
        """

        storage = get_storage()

        for module in [constants.GsePackageCode.AGENT.value, constants.GsePackageCode.PROXY.value]:
            logger.info(f"load module -> {module}")
            module_dir: str = os.path.join(settings.BK_OFFICIAL_PLUGINS_INIT_PATH, str(module))
            if not os.path.exists(module_dir):
                logger.info(f"module_dir -> {module_dir} not exist, skipped it.")
                continue
            for file_abs_path in files.fetch_file_paths_from_dir(dir_path=module_dir):
                file_name: str = os.path.basename(file_abs_path)
                if not tarfile.is_tarfile(file_abs_path):
                    logger.warning(f"file -> [{file_name}] is not tar file, will not try to import it.")
                    continue

                logger.info(f"start to upload [{file_name}] to storage.")
                with open(file=file_abs_path, mode="rb") as fs:
                    file_path = storage.save(name=os.path.join(settings.UPLOAD_PATH, file_name), content=fs)
                logger.info(f"upload [{file_name}] to storage({file_path}) success.")

                upload_record = models.UploadPackage.create_record(
                    # 后续可以考虑通过路径来判断
                    module=module,
                    file_path=file_path,
                    md5=files.md5sum(name=file_abs_path),
                    operator="system",
                    source_app_code=settings.APP_CODE,
                    file_name=os.path.basename(file_path),
                    is_file_copy=True,
                )

                if module == constants.GsePackageCode.AGENT.value:
                    artifact_builder_class: typing.Type[base.BaseArtifactBuilder] = agent.AgentArtifactBuilder
                else:
                    artifact_builder_class: typing.Type[base.BaseArtifactBuilder] = proxy.ProxyArtifactBuilder

                with artifact_builder_class(
                    initial_artifact_path=upload_record.file_path,
                    cert_path=options.get("cert_path"),
                    download_path=options.get("download_path"),
                    overwrite_version=options.get("overwrite_version"),
                    enable_agent_pkg_manage=options.get("enable_agent_pkg_manage"),
                ) as builder:
                    builder.make()
