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
import typing

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from apps.generic import ApiMixinModelViewSet as ModelViewSet
from apps.generic import ValidationMixin
from apps.node_man.serializers import package_manage as pkg_manage
from apps.node_man.tools.gse_package import GsePackageTools
from apps.node_man.views.package_manage import PACKAGE_MANAGE_VIEW_TAGS
from common.utils.drf_utils import swagger_auto_schema


class AgentViewSet(ModelViewSet, ValidationMixin):
    """
    agent相关API
    """

    @swagger_auto_schema(
        operation_summary="解析Agent包",
        tags=PACKAGE_MANAGE_VIEW_TAGS,
        responses={HTTP_200_OK: pkg_manage.ParseResponseSerializer},
    )
    @action(detail=False, methods=["POST"], serializer_class=pkg_manage.ParseSerializer)
    def parse(self, request):
        """
        return: {
            "description": "test",
            "packages": [
                {
                    "pkg_abs_path": "xxx/xxxxx",
                    "pkg_name": "gseagent_2.1.7_linux_x86_64.tgz",
                    "module": "agent",
                    "version": "2.1.7",
                    "config_templates": [],
                    "os": "x86_64",
                },
                {
                    "pkg_abs_path": "xxx/xxxxx",
                    "pkg_name": "gseagent_2.1.7_linux_x86.tgz",
                    "module": "agent",
                    "version": "2.1.7",
                    "config_templates": [],
                    "os": "x86",
                },
            ],
        }
        """
        validated_data = self.validated_data

        # 获取最新的agent上传包记录
        upload_package_obj = GsePackageTools.get_latest_upload_record(file_name=validated_data["file_name"])

        # 区分agent和proxy包
        project, artifact_builder_class = GsePackageTools.distinguish_gse_package(
            file_path=upload_package_obj.file_path
        )

        # 解析包
        with artifact_builder_class(initial_artifact_path=upload_package_obj.file_path) as builder:
            extract_dir, package_dir_infos = builder.list_package_dir_infos()
            artifact_meta_info: typing.Dict[str, typing.Any] = builder.get_artifact_meta_info(extract_dir)

        res = {"description": artifact_meta_info.get("changelog"), "packages": package_dir_infos}

        context = {
            "project": project,
            "version": artifact_meta_info["version"],
        }

        return Response(pkg_manage.ParseResponseSerializer(res, context=context).data)
