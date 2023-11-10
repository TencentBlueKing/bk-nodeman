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
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from apps.exceptions import ValidationError
from apps.node_man.constants import GsePackageCode


class TagsSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    children = serializers.ListField()


class ConditionsSerializer(serializers.Serializer):
    key = serializers.ChoiceField(choices=["version", "os_cpu_arch", "tags", "is_ready"])
    values = serializers.ListField()


class PackageSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    pkg_name = serializers.CharField()
    version = serializers.CharField()
    os = serializers.CharField()
    cpu_arch = serializers.CharField()
    tags = TagsSerializer(many=True)
    creator = serializers.CharField()
    pkg_ctime = serializers.DateTimeField()
    is_ready = serializers.BooleanField()


class PackageDescSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    version = serializers.CharField()
    tags = TagsSerializer(many=True)
    packages = PackageSerializer(many=True)
    is_ready = serializers.BooleanField()


class ListResponseSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    list = PackageSerializer(many=True)


class PackageDescResponseSerialiaer(serializers.Serializer):
    total = serializers.IntegerField()
    list = PackageDescSerializer(many=True)


class OperateSerializer(serializers.Serializer):
    is_ready = serializers.BooleanField()


class QuickSearchSerializer(serializers.Serializer):
    project = serializers.ChoiceField(choices=GsePackageCode.list_choices())


# TODO 与plugin相同可抽取公共Serializer
class UploadSerializer(serializers.Serializer):
    class PkgFileField(serializers.FileField):
        def to_internal_value(self, data):
            data = super().to_internal_value(data)
            file_name = data.name
            if not (file_name.endswith(".tgz") or file_name.endswith(".tar.gz")):
                raise ValidationError(_("仅支持'tgz', 'tar.gz'拓展名的文件"))
            return data

    module = serializers.ChoiceField(choices=["gse_agent", "gse_proxy"], required=False, default="gse_agent")
    package_file = PkgFileField()


class UploadResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    pkg_size = serializers.IntegerField()


class ParseSerializer(serializers.Serializer):
    file_name = serializers.CharField()


class ParseResponseSerializer(serializers.Serializer):
    class ParsePackageSerializer(serializers.Serializer):
        module = serializers.ChoiceField(choices=["agent", "proxy"])
        pkg_name = serializers.CharField()
        pkg_abs_path = serializers.CharField()
        version = serializers.CharField()
        os = serializers.CharField()
        cpu_arch = serializers.CharField()
        config_templates = serializers.ListField()

    description = serializers.CharField()
    packages = ParsePackageSerializer(many=True)


class AgentRegisterSerializer(serializers.Serializer):
    class RegisterPackageSerializer(serializers.Serializer):
        pkg_abs_path = serializers.CharField()
        tags = serializers.ListField()

    is_release = serializers.BooleanField()
    packages = RegisterPackageSerializer(many=True)


class AgentRegisterTaskSerializer(serializers.Serializer):
    job_id = serializers.IntegerField()


class AgentRegisterTaskResponseSerializer(serializers.Serializer):
    is_finish = serializers.BooleanField()
    status = serializers.ChoiceField(choices=["SUCCESS", "FAILED", "RUNNING"])
    message = serializers.CharField()
