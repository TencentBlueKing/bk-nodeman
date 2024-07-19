# -*- coding: utf-8 -*-
"""
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-蓝鲸 PaaS 平台(BlueKing-PaaS) available.
 * Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at http://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
"""
import os
import tempfile

from apigw_manager.apigw.command import SyncCommand
from apigw_manager.apigw.utils import ZipArchiveFile


class Command(SyncCommand):
    """Synchronous API gateway resource docs"""

    default_namespace = "resource_docs"

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            "--safe-mode",
            action="store_true",
            default=False,
            help="do nothing when dir or archive file does not exist",
        )

    def do(self, manager, definition, safe_mode, *args, **kwargs):
        # 1. 文档为归档文件
        archivefile = definition.get("archivefile")
        if archivefile and os.path.isfile(archivefile):
            with open(archivefile, "rb") as f:
                self._sync_resource_docs_by_archive(manager, f)
                return

        # 2. 指定文档目录，需归档后同步
        basedir = definition.get("basedir")
        if not basedir or not os.path.isdir(basedir):
            if safe_mode:
                return

            raise ValueError("the docs dir does not exist or is not a directory: %s" % basedir)

        with tempfile.TemporaryFile() as temp_file:
            ZipArchiveFile.archive(basedir, temp_file)
            temp_file.seek(0)

            self._sync_resource_docs_by_archive(manager, temp_file)

    def _sync_resource_docs_by_archive(self, manager, fileobj):
        result = manager.sync_resource_docs_by_archive(files={"file": fileobj})
        print("API gateway resource docs synchronization by archive completed, result: %s" % result)
