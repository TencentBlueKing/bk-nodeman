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
import zipfile

import yaml
from bkapi_client_core.config import SettingKeys, settings
from packaging.version import Version as _Version

from apigw_manager.core import configuration
from bkapi_client_core.config import SettingKeys, settings


def get_configuration(**kwargs):
    """Generate management configuration according to the settings"""

    settings_mappings = [
        ("BK_APIGW_NAME", "api_name"),
        ("BK_APP_CODE", "bk_app_code"),
        ("BK_APP_SECRET", "bk_app_secret"),
        ("BK_APIGW_JWT_PROVIDER_CLS", "jwt_provider_cls"),
    ]

    for attr, key in settings_mappings:
        if key in kwargs:
            continue

        value = settings.get(attr)
        if value is not None:
            kwargs[key] = value

    host = kwargs.pop("host", "")
    if not host:
        host = _get_host_from_settings()

    # stage has been added to host, here stage is set to an empty string
    return configuration.Configuration(
        host=host.rstrip("/"),
        stage="",
        **kwargs,
    )


def _get_host_from_settings():
    stage_url = settings.get("BK_APIGATEWAY_API_STAGE_URL")
    if stage_url:
        return stage_url

    tmpl = settings.get(SettingKeys.BK_API_URL_TMPL)
    if tmpl:
        # API 网关 admin API 对应网关名为 bk-apigateway
        return "%s/prod/" % tmpl.format(api_name="bk-apigateway").rstrip("/")

    return ""


def yaml_load(content):
    """Load YAML"""
    return yaml.load(content, Loader=yaml.FullLoader)


def parse_value_list(*values):
    """Parse value list"""
    data = {}
    for i in values:
        key, sep, value = i.partition(":")
        if not sep:
            data[key] = None
        else:
            data[key] = yaml_load(value)

    return data


class ZipArchiveFile:
    @classmethod
    def archive(cls, path, output):
        """归档文件

        其中的文件名，设置为基于 path 的相对路径
        """
        archived_files = cls._get_archived_files(path)
        with zipfile.ZipFile(output, "w") as zip_:
            for file_path, name in archived_files.items():
                zip_.write(file_path, name)

        return output

    @classmethod
    def _get_archived_files(cls, path):
        """获取待归档文件，及去掉基准目录后的文件名"""
        if os.path.isfile(path):
            return {path: os.path.basename(path)}

        path = path if path.endswith(os.path.sep) else path + os.path.sep

        path_to_name = {}
        for root, dirs, files in os.walk(path):
            for name in files:
                file_path = os.path.join(root, name)
                path_to_name[file_path] = file_path[len(path) :]

        return path_to_name


class SemVersion(_Version):
    @property
    def pre(self):
        pre = self._version.pre

        if not pre:
            return None

        # 恢复缩写，如 1.1.0a1 -> 1.1.0-alpha1
        letter, number = pre
        if letter == "a":
            letter = "alpha"
        elif letter == "b":
            letter = "beta"

        return "-%s" % letter, number


def parse_version(version):
    return SemVersion(version)
