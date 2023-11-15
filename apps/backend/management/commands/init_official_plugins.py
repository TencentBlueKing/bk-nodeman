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
import traceback

import six
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from apps.backend.management.commands import utils
from apps.backend.plugin import tools
from apps.backend.subscription.handler import SubscriptionHandler
from apps.core.files.storage import get_storage
from apps.core.tag.constants import TargetType
from apps.core.tag.handlers import TagHandler
from apps.node_man import constants, models
from apps.utils import files
from common.log import logger

log_and_print = utils.get_log_and_print("init_official_plugins")


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("-t", "--tag", help="为目标版本所指定的标签", type=str)
        parser.add_argument("-r", "--run-policy", help="触发部署策略", action="store_true", default=False)

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
        tag = options.get("tag")
        run_policy = options.get("run_policy") or False

        log_and_print(f"options: tag -> {tag}, run_policy -> {run_policy}")

        storage = get_storage()

        # 1. 遍历寻找所有符合条件的插件文件
        # 此处使用walk的原因，主要是考虑后续需要使用文件夹来隔离不同类型的插件，所以使用walk而非listdir
        for file_abs_path in files.fetch_file_paths_from_dir(
            settings.BK_OFFICIAL_PLUGINS_INIT_PATH, ignored_dir_names=constants.GsePackageCode.list_member_values()
        ):
            file_name: str = os.path.basename(file_abs_path)
            if not tarfile.is_tarfile(file_abs_path):
                logger.warning("file->[%s] is not tar file, will not try to import it." % file_abs_path)
                continue

            with open(file=file_abs_path, mode="rb") as fs:
                file_path = storage.save(name=os.path.join(settings.UPLOAD_PATH, file_name), content=fs)

            # 2. 尝试导入这个文件
            with atomic():
                upload_record = models.UploadPackage.create_record(
                    # 后续可以考虑通过路径来判断
                    module="gse_plugin",
                    file_path=file_path,
                    md5=files.md5sum(name=file_abs_path),
                    operator="system",
                    source_app_code="bk_nodeman",
                    file_name=os.path.basename(file_path),
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

            if tag and package_list:
                one_of_pkg = package_list[0]
                log_and_print(
                    f"tag to be created: name -> {tag}, plugin_name -> {one_of_pkg.plugin_desc.name}, "
                    f"version -> {one_of_pkg.version}"
                )
                TagHandler.publish_tag_version(
                    name=tag,
                    target_type=TargetType.PLUGIN.value,
                    target_id=one_of_pkg.plugin_desc.id,
                    target_version=one_of_pkg.version,
                )

            if tag and run_policy:
                to_be_run_policies = models.Subscription.objects.filter(
                    plugin_name=one_of_pkg.plugin_desc.name,
                    category=models.Subscription.CategoryType.POLICY,
                    pid=models.Subscription.ROOT,
                    enable=True,
                )
                for policy in to_be_run_policies:
                    log_and_print(f"policy to be run: name -> {policy.name}, id -> {policy.id}")
                    try:
                        run_result = SubscriptionHandler(policy.id).run()
                        log_and_print(f"policy run: name -> {policy.name}, id -> {policy.id}, result -> {run_result}")
                    except Exception as e:
                        log_and_print(
                            f"policy run failed but skipped: name -> {policy.name}, id -> {policy.id}, error -> {e}"
                        )

        logger.info(
            "all package under path->[%s] is import success, file_count->[%s] package_count->[%s]"
            % (settings.BK_OFFICIAL_PLUGINS_INIT_PATH, file_count, package_count)
        )
