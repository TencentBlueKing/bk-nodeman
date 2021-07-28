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
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.node_man.models import AccessPoint

IGNORED_PATH = ["__pycache__"]


class Command(BaseCommand):
    def handle(self, *args, **options):
        """
        拷贝scripts下的文件到nginx download下
        """
        # 接入点配置的nginx路径
        nginx_paths = [ap.nginx_path for ap in AccessPoint.objects.all() if ap.nginx_path]
        # 默认nginx路径
        nginx_paths.append(settings.NGINX_DOWNLOAD_PATH)
        # 去重
        nginx_paths = list(set(nginx_paths))
        for _path in os.listdir(settings.BK_SCRIPTS_PATH):
            if _path in IGNORED_PATH:
                continue

            _abspath = os.sep.join([settings.BK_SCRIPTS_PATH, _path])
            if os.path.isfile(_abspath):
                for dest_path in nginx_paths:
                    print("[Copying File]: from {} to {}".format(_abspath, dest_path))
                    shutil.copy2(_abspath, dest_path)

            if os.path.isdir(_abspath):
                for dest_path in nginx_paths:
                    print("[Copying Directory]: from {} to {}".format(_abspath, dest_path))
                    _dst_dir = os.sep.join([dest_path, _path])
                    shutil.rmtree(_dst_dir, ignore_errors=True)
                    shutil.copytree(_abspath, _dst_dir)

        for filename in ["setup_agent.bat", "gsectl.bat"]:
            # Windows脚本替换换行符
            for dest_path in nginx_paths:
                os.system(
                    """
                    awk 'sub("$","\r")' {path}/{filename} > {dest_path}/{filename}
                    """.format(
                        path=settings.BK_SCRIPTS_PATH, dest_path=dest_path, filename=filename
                    )
                )
