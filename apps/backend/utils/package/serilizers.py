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

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from apps.exceptions import ValidationError
from apps.node_man import constants


class GatewaySerializer(serializers.Serializer):
    bk_username = serializers.CharField()
    bk_app_code = serializers.CharField()


class UploadBaseSerializer(GatewaySerializer):
    md5 = serializers.CharField(help_text=_("上传端计算的文件md5"), max_length=32)
    file_name = serializers.CharField(help_text=_("上传端提供的文件名"), min_length=1)
    module = serializers.CharField(max_length=32, required=False, default="gse_plugin")


class NginxUploadSerializer(UploadBaseSerializer):
    """上传插件包接口序列化器"""

    file_local_path = serializers.CharField(help_text=_("本地文件路径"), max_length=512)
    file_local_md5 = serializers.CharField(help_text=_("Nginx所计算的文件md5"), max_length=32)


class CosUploadSerializer(UploadBaseSerializer):
    """对象存储上传文件接口序列号器"""

    download_url = serializers.URLField(help_text=_("文件下载url"), required=False)
    file_path = serializers.CharField(help_text=_("文件保存路径"), min_length=1, required=False)

    def validate(self, attrs):
        # 两种参数模式少要有一种满足
        if not ("download_url" in attrs or "file_path" in attrs):
            raise ValidationError("at least has download_url or file_path")
        return attrs


class AgentParseSerializer(GatewaySerializer):
    file_name = serializers.CharField()


class SwithVersionSerializer(GatewaySerializer):
    version = serializers.CharField(help_text=_("切换前版本号"), max_length=32)
    switch_releasing = serializers.CharField(help_text=_("目标版本号"), max_length=32)
    medium = serializers.CharField(help_text=_("安装介质"), max_length=32, required=False)

    def validate(self, attrs):
        # if self.switch_releasing not in constants.RELEASING_TYPE_TUPLE:
        #     raise ValidationError(f"当前只支持以下状态版本: {'|'.join(constants.RELEASING_TYPE_TUPLE)}")
        if attrs["switch_releasing"] not in constants.RELEASING_TYPE_TUPLE:
            raise ValidationError(f"当前只支持以下状态版本: {'|'.join(constants.RELEASING_TYPE_TUPLE)}")
        return attrs
