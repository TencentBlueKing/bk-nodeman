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
from typing import Iterable, List, Optional

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.core.files.storage import constants as core_files_constants
from apps.core.files.storage import get_storage
from apps.node_man.models import AccessPoint
from apps.utils import files

from . import utils

log_and_print = utils.get_log_and_print("copy_file_to_nginx(storage)")


def copy_dir_files_to_storage(
    source_dir_path: str, target_dir_paths: Iterable[str], ignored_dir_names: Optional[List[str]] = None
):
    """
    将目录下文件保存到存储
    :param source_dir_path: 源目录路径
    :param target_dir_paths: 目标目录路径
    :param ignored_dir_names: 忽略的目录名称
    :return:
    """

    log_and_print(
        f"source_dir_path -> {source_dir_path} \n target_dir_path -> {target_dir_paths} \n "
        f"ignored_dir_names -> {ignored_dir_names}"
    )

    storage = get_storage(file_overwrite=True)
    source_file_paths = files.fetch_file_paths_from_dir(dir_path=source_dir_path, ignored_dir_names=ignored_dir_names)

    for source_file_path in source_file_paths:
        # 获取文件相对路径，用于拼接保存路径
        file_relative_path = source_file_path.replace(source_dir_path + os.path.sep, "")
        with open(source_file_path, mode="rb") as target_file_fs:
            for target_dir_path in target_dir_paths:
                target_file_path = os.path.join(target_dir_path, file_relative_path)
                storage.save(name=target_file_path, content=target_file_fs)
                target_file_fs.seek(0)

    # 如果使用了蓝鲸制品库，更新默认接入点的下载地址
    if storage.storage_type == core_files_constants.StorageType.BLUEKING_ARTIFACTORY.value:
        default_ap = AccessPoint.objects.all().first()
        default_save_path = default_ap.nginx_path or settings.DOWNLOAD_PATH
        if default_save_path.startswith("/"):
            default_save_path = default_save_path[1:]
        package_download_url = os.path.join(
            storage.endpoint_url, "generic", storage.project_id, storage.bucket, default_save_path
        )
        log_and_print(f"storage_type -> {storage.storage_type}, init package_download_url -> {package_download_url}")

        default_ap.package_inner_url = package_download_url
        default_ap.package_outer_url = package_download_url
        default_ap.save()


class Command(BaseCommand):
    def handle(self, *args, **options):
        """
        拷贝scripts下的文件到nginx download下
        """

        if not settings.BK_BACKEND_CONFIG:
            log_and_print("command only work on settings.BK_BACKEND_CONFIG == True")
            return

        # 接入点配置的nginx路径
        target_dir_paths = {ap.nginx_path for ap in AccessPoint.objects.all() if ap.nginx_path}
        # 默认nginx路径
        target_dir_paths.add(settings.DOWNLOAD_PATH)

        copy_dir_files_to_storage(
            source_dir_path=settings.BK_SCRIPTS_PATH,
            target_dir_paths=target_dir_paths,
            ignored_dir_names=["__pycache__"],
        )

        log_and_print("success.")
