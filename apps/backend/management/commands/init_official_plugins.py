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
import tarfile
import traceback

import six
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from apps.backend.plugin import tools
from apps.node_man import models
from apps.utils.files import md5sum
from common.log import logger


class Command(BaseCommand):
    def handle(self, *args, **options):
        """
        初始化内置官方插件
        :param args:
        :param options:
        :return: None
        """
        # 成功导入的文件计数
        file_count = 0
        # 成功导入插件包的技术
        package_count = 0

        # 1. 遍历寻找所有符合条件的插件文件
        # 此处使用walk的原因，主要是考虑后续需要使用文件夹来隔离不同类型的插件，所以使用walk而非listdir
        for dir_path, _, file_list in os.walk(settings.BK_OFFICIAL_PLUGINS_INIT_PATH):

            for file_name in file_list:
                file_abs_path = os.path.join(dir_path, file_name)

                # 判断是否符合预期的文件内容
                if os.path.isdir(file_abs_path):
                    logger.warning("file->[%s] is dir not file, will not try to import it." % file_abs_path)
                    continue

                if not tarfile.is_tarfile(file_abs_path):
                    logger.warning("file->[%s] is not tar file, will not try to import it." % file_abs_path)
                    continue

                # 2. 尝试导入这个文件
                with atomic():
                    upload_record = models.UploadPackage.create_record(
                        # 后续可以考虑通过路径来判断
                        module="gse_plugin",
                        file_path=file_abs_path,
                        md5=md5sum(name=file_abs_path),
                        operator="system",
                        source_app_code="bk_nodeman",
                        file_name=file_name,
                        is_file_copy=True,
                    )

                    try:
                        # 如果是官方内置的插件，那么应该是直接发布的
                        package_list = tools.create_package_records(
                            file_path=upload_record.file_path,
                            file_name=upload_record.file_name,
                            is_release=True,
                            is_template_load=True,
                        )
                    except Exception as error:
                        # 但是需要注意这个文件可能是已经存在的文件，会有导入失败的问题
                        logger.error(
                            "failed to import file->[%s] for->[%s] file all records will be deleted."
                            % (file_abs_path, traceback.format_exc())
                        )
                        six.raise_from(error, error)
                        continue

                package_name_list = [
                    # mysql_export->1.0.0->x86->linux
                    "->".join([package.pkg_name, str(package.version), package.cpu_arch, package.os])
                    for package in package_list
                ]
                logger.info("file->[{}] import success for packages->[{}]".format(file_abs_path, package_name_list))

                file_count += 1
                package_count += len(package_list)

        logger.info(
            "all package under path->[%s] is import success, file_count->[%s] package_count->[%s]"
            % (settings.BK_OFFICIAL_PLUGINS_INIT_PATH, file_count, package_count)
        )
