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

import logging
import re
import shutil
from collections import defaultdict
from typing import Any, Dict

from django.utils.translation import ugettext_lazy as _
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.backend import exceptions
from apps.backend.agent import tools
from apps.backend.agent.tools import switch_releasing_version
from apps.backend.utils.package.handler import PackageHandler
from apps.backend.utils.package.serilizers import (
    AgentParseSerializer,
    CosUploadSerializer,
    SwithVersionSerializer,
)
from apps.generic import APIViewSet
from apps.node_man import constants, models

LOG_PREFIX_RE = re.compile(r"(\[\d{4}-\d{1,2}-\d{1,2}\s\d{1,2}:\d{1,2}.*?\] )")
logger = logging.getLogger("app")


class AgentViewSet(APIViewSet, mixins.RetrieveModelMixin, mixins.ListModelMixin):
    """
    插件相关API
    """

    @action(detail=False, methods=["POST"], serializer_class=CosUploadSerializer)
    def upload(self, request, *args, **kwargs):
        """
        @api {POST} /agent/upload/ 上传 Agent 相关文件接口
        @apiName upload
        @apiGroup backend_plugin
        @apiParam {String} module 模块名称
        @apiParam {String} md5 上传端计算的文件md5
        @apiParam {String} file_name 上传端提供的文件名
        @apiParam {String} download_url 文件下载url，download_url & file_path 其中一个必填
        @apiParam {String} file_path 文件保存路径，download_url & file_path 其中一个必填
        @apiParamExample {Json} 请求参数
        {
          "bk_app_code": "bk_nodeman",
          "bk_app_secret": "xxx",
          "bk_username": "xxx",
          "md5": "e86c07536ada151dd85ca533874e8883",
          "filename": "gse_ee-1.7.15.tgz",
          "download_url": "http://xxxx/gse_ee-1.7.15.tgz "
        }
        @apiSuccessExample {json} 成功返回:
        {
            "id": 1,
            "name": "gse_ee-1.7.15.tgz ",
            "pkg_size": "666"
        }
        """
        params = self.validated_data

        upload_result = PackageHandler.upload(
            md5=params["md5"],
            origin_file_name=params["file_name"],
            module=params["module"],
            operator=params["bk_username"],
            app_code=params["bk_app_code"],
            file_path=params.get("file_path"),
            download_url=params.get("download_url"),
            action_type=constants.ProcType.AGENT,
        )
        return Response(upload_result)

    @action(detail=False, methods=["POST"], serializer_class=AgentParseSerializer)
    def parse(self, request):
        """
        @api {POST} /agent/parse/ 解析插件包
        @apiName agent_parse
        @apiGroup backend_agent
        @apiParam {String} file_name 文件名
        @apiParam {String} [is_update] 是否为更新校验，默认为`False`
        @apiParamExample {Json} 请求参数
        {
            "file_name": "basereport-10.1.12.tgz"
        }
        @apiSuccessExample {json} 成功返回:
        [
            {
                "message": "新增插件",
                "pkg_abs_path": "basereport_linux_x86_64/basereport",
                "pkg_name": "basereport-10.1.12",
                "project": "basereport",
                "version": "10.1.12",
                "category": "官方插件",
                "config_templates": [
                    {"name": "child1.conf", "version": "1.0", "is_main": false},
                    {"name": "child2.conf", "version": "1.1", "is_main": false},
                    {"name": "basereport-main.config", "version": "0.1", "is_main": true}
                ],
                "os": "x86_64",
                "cpu_arch": "linux",
                "description": "高性能日志采集"
            },
            {
                "message": "缺少project.yaml文件",
                "pkg_abs_path": "external_bkmonitorbeat_windows_x32/bkmonitorbeat",
                "pkg_name": None,
                "version": None,
                "agent_files": {
                    "linux_x86":  [ "a"],
                    "windows_x86": ["c"],
                },
                "proxy_files": {
                    "linux_x86_64":  [ "a"],
                },
                "config_template": {
                    "agent": [
                        "windows_x86": ["c"],
                    ]
                },
                "version": "1.7.17",
                "medium": "default"，
                "desc": "通用Agent安装包，无定制化需求"
            },
        ]
        """
        params = self.validated_data
        upload_package_obj = (
            models.UploadPackage.objects.filter(file_name=params["file_name"]).order_by("-upload_time").first()
        )
        if upload_package_obj is None:
            raise exceptions.UploadPackageNotExistError(_("找不到请求发布的文件，请确认后重试"))

        # 解析Agent完整包
        package_infos = tools.parse_client_package(file_path=upload_package_obj.file_path)

        pkg_parse_result: Dict[str, Any] = defaultdict(list)
        for node_type, infos in package_infos.items():
            if node_type == constants.AgentPackageMap.CONFIG_TEMPLATE:
                for template__node_type, template__infos in infos:
                    pkg_parse_result[constants.AgentPackageMap.CONFIG_TEMPLATE][template__node_type] = template__infos
            else:
                for platform, files in infos.items():
                    pkg_parse_result[node_type][platform] = files

        pkg_parse_result.update(
            {
                "result": pkg_parse_result["result"],
                "version": pkg_parse_result["version"],
                "medium": pkg_parse_result["medium"],
                "desc": pkg_parse_result["desc"],
                "pkg_abs_path": upload_package_obj.file_path,
            }
        )

        agent_tmp_dir: str = package_infos["package_tmp_path"]
        # 清理临时解压目录
        shutil.rmtree(agent_tmp_dir)
        return Response(pkg_parse_result)

    @action(detail=False, methods=["POST"], serializer_class=SwithVersionSerializer)
    def switch_version(self, request):

        # 从某个版本切换到指定到版本

        params = self.validated_data
        version = params["version"]
        switch_releasing = params["switch_releasing"]
        medium = params.get("medium", constants.AgentPackageMap.AGENT_DEFAULT_MEDIUM["name"])

        switch_result = switch_releasing_version(version=version, medium=medium, switch_releasing=switch_releasing)
        return Response(switch_result)
