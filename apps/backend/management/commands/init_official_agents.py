# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from __future__ import absolute_import, unicode_literals

import os
import re
import tarfile
from typing import List

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from apps.backend.agent.agent_manage.pack_gse_client_with_plugin import GseClientPack
from apps.backend.exceptions import CertFileNotFoundError
from apps.core.files.storage import get_storage
from apps.node_man.models import GlobalSettings, UploadPackage
from apps.utils.files import md5sum
from common.log import logger


class Command(BaseCommand):
    storage = get_storage()
    GSE_AGENT_PACKAGE_RE = re.compile(r"gse_(?P<os>(ee|ce))-(\d+\.\d+\.\d+).(?P<suffix>(tar|tar.gz|tgz))$")
    GSE_PLUGINS_PACKAGE_RE = re.compile(r"gse_plugins-(\d+.\d+.\d+).(?P<suffix>(tar|tar.gz|tgz))$")

    def handle(self, *args, **options):
        cert_file_name = self.filter_cert_package()
        for dir_path, _, file_list in os.walk(settings.BK_OFFICIAL_AGENT_INIT_PATH):
            for file_name in file_list:
                file_abs_path = os.path.join(dir_path, file_name)

                # 判断是否符合预期的文件内容
                if os.path.isdir(file_abs_path):
                    logger.warning("file->[%s] is dir not file, will not try to import it." % file_abs_path)
                    continue

                if not tarfile.is_tarfile(file_abs_path):
                    logger.warning("file->[%s] is not tar file, will not try to import it." % file_abs_path)
                    continue

        similar_gse_agent_packages = self.filter_target_name_by_regex(
            self.GSE_AGENT_PACKAGE_RE, settings.BK_OFFICIAL_AGENT_INIT_PATH
        )
        similar_gse_plugins_packages = self.filter_target_name_by_regex(
            self.GSE_PLUGINS_PACKAGE_RE, settings.BK_OFFICIAL_AGENT_INIT_PATH
        )
        gse_agent_package = self.filter_last_package(similar_gse_agent_packages)
        gse_plugins_package = self.filter_last_package(similar_gse_plugins_packages)
        gse_plugins_version = self.GSE_PLUGINS_PACKAGE_RE.match(os.path.basename(gse_plugins_package)).group(1)
        gse_agent_version = self.GSE_AGENT_PACKAGE_RE.match(os.path.basename(gse_agent_package)).group(3)

        GseClientPack().pack_gse_client_with_plugins(
            client_version=gse_agent_version,
            plugins_version=gse_plugins_version,
            cert_package=cert_file_name,
            client_package=gse_agent_package,
            plugins_package=gse_plugins_package,
        )

    @classmethod
    def filter_cert_package(cls):
        global_cert_re = re.compile("cert.*(?P<suffix>(tar|tar.gz|tgz))$")
        cert_package = GlobalSettings.get_config(key="BLUEKING_CERT_PACKAGE")
        if cert_package:
            return cert_package
        # 初始化路径下的包到配置文件
        similar_cert_files = cls.filter_target_name_by_regex(global_cert_re, settings.BK_OFFICIAL_AGENT_INIT_PATH)
        # 选取最新的包
        last_package = cls.filter_last_package(similar_cert_files)
        if not last_package:
            raise CertFileNotFoundError(context="未匹配正确的证书文件")
        file_abs_path = os.path.join(settings.BK_OFFICIAL_AGENT_INIT_PATH, last_package)
        with atomic():
            upload_record = UploadPackage.create_record(
                module="gse_agent",
                file_path=file_abs_path,
                md5=md5sum(file_abs_path),
                operator="system",
                is_file_copy=True,
                source_app_code="bk_nodeman",
                file_name=os.path.basename(last_package),
            )
            logger.info(
                f"user -> {upload_record.creator} from app-> {upload_record.source_app_code} upload"
                f"file -> {upload_record.file_path} success."
            )

            GlobalSettings.set_config(key="BLUEKING_CERT_PACKAGE", value=file_abs_path)
            logger.info(f"setting global cert config package -> {last_package}")
        return last_package

    @classmethod
    def filter_last_package(cls, file_list: List[str]):
        """
        选取目标文件中最新的一个
        """
        last_package = sorted(file_list, key=lambda t: cls.storage.get_modified_time(t).strftime("%s"))[-1]
        return last_package

    @classmethod
    def filter_target_name_by_regex(cls, regex, file_dir):
        """
        选出目标目录下所有符合预期正则表达式的文件
        """
        similar_file_list = []
        for file_name in os.listdir(file_dir):
            file_path = os.path.join(file_dir, file_name)
            if regex.match(file_name):
                similar_file_list.append(file_path)
        return similar_file_list
