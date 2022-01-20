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
import datetime
import re
import traceback

import requests
from django.http import Http404

from apps.node_man.models import AccessPoint, GlobalSettings
from apps.node_man.serializers.plugin import (
    GsePluginSerializer,
    ProcessControlInfoSerializer,
    ProcessPackageSerializer,
)
from apps.utils import APIModel
from common.log import logger

Multi_backslash_pattern = re.compile(r"\\+")


class APHandler(APIModel):
    """
    AP处理器
    """

    def ap_list(self, ap_ids):
        """
        根据ap_id获得接入点名称
        :param ap_ids: 接入点id集合
        :return
        {
            id: name
        }
        """

        ap_id_name = dict(AccessPoint.objects.filter(id__in=ap_ids).values_list("id", "name"))
        return ap_id_name

    def init_plugin_data(self, username, ap_id=None):
        if ap_id:
            ap = AccessPoint.objects.get(id=ap_id)
        else:
            ap = AccessPoint.objects.filter(is_default=True).first()

        # 插入初始化信息
        GlobalSettings.objects.update_or_create(
            defaults={
                "v_json": {
                    "user": username,
                    "time": str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    "ap_id": ap.id,
                }
            },
            key="plugin_config",
        )

        data = []
        inner_url = f"{ap.package_inner_url}/init_nodeman.json"
        init_nodeman_json = read_remote_file_content(inner_url)

        for i, row in enumerate(init_nodeman_json):
            try:
                result = self._init(row)
                data.append(result)
            except Exception as err:
                logger.error("init_nodeman_json data incorrect: {}".format(str(err)))
                logger.error("incorrect data: {}, index: {}".format(init_nodeman_json, i))
                logger.error(traceback.format_exc())

        return data

    def _init(self, data):
        gseplugindesc = data.get("gseplugindesc")
        packages = data.get("packages")
        proccontrol = data.get("proccontrol")

        # replace multiple \ to one for windows paths
        proccontrol = {
            key: re.sub(Multi_backslash_pattern, r"\\", value) if key.endswith("path") else value
            for key, value in proccontrol.items()
        }
        packages = {
            key: re.sub(Multi_backslash_pattern, r"\\", value) if key.endswith("path") else value
            for key, value in packages.items()
        }

        process_serializer = GsePluginSerializer(data=gseplugindesc)
        process_serializer.is_valid(raise_exception=True)
        process_serializer.save()

        package_serializer = ProcessPackageSerializer(data=packages)
        package_serializer.is_valid(raise_exception=True)
        package_serializer.save()

        proccontrol["plugin_package_id"] = package_serializer.data["id"]
        process_info_serializer = ProcessControlInfoSerializer(data=proccontrol)
        process_info_serializer.is_valid(raise_exception=True)
        process_info_serializer.save()

        return {
            "gseplugindesc": process_serializer.data,
            "packages": package_serializer.data,
            "proccontrol": process_info_serializer.data,
        }


def read_remote_file_content(remote_url):
    # os.environ["http_proxy"] = ""
    # os.environ["https_proxy"] = ""
    try:
        response = requests.get(remote_url, proxies={})
    except Exception:
        raise ValueError("无法通过内网URL {}找到初始化文件".format(remote_url))

    if response.status_code == 404:
        raise Http404("nginx服务器上找不到初始化文件")

    try:
        return response.json()
    except ValueError:
        raise ValueError("初始化文件格式错误，无法解析")
