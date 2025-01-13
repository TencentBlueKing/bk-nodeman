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

from apps.core.tag.constants import TargetType
from apps.exceptions import ValidationError
from apps.node_man.constants import GsePackageCode
from apps.node_man.handlers.gse_package import gse_package_handler
from apps.node_man.models import UploadPackage


class TagSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField()


class TagProjectSerializer(serializers.Serializer):
    project = serializers.CharField(default=GsePackageCode.AGENT.value)


class TagCreateSerializer(serializers.Serializer):
    tag_descriptions = serializers.ListField(child=serializers.CharField(max_length=32), default=[])
    project = serializers.CharField()

    def validate(self, attrs):
        project = attrs["project"]
        if project not in GsePackageCode.values():
            raise ValidationError(_("project可选项[ gse_agent | gse_plugin ]"))

        return attrs

    class Meta:
        ref_name = "tag_create"


class ParentTagSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField()
    children = TagSerializer(many=True)


class ConditionsSerializer(serializers.Serializer):
    key = serializers.ChoiceField(choices=["version", "os_cpu_arch", "tags", "is_ready"])
    values = serializers.ListField()


class BasePackageSerializer(serializers.Serializer):
    @staticmethod
    def get_tags(obj, enable_tag_separation=True):
        return gse_package_handler.get_tags(
            project=obj.project,
            version=obj.version,
            enable_tag_separation=enable_tag_separation,
        )

    @classmethod
    def get_description(cls, obj):
        return gse_package_handler.get_description(project=obj.project)


class PackageSerializer(BasePackageSerializer):
    id = serializers.IntegerField()
    pkg_name = serializers.CharField()
    version = serializers.CharField()
    os = serializers.CharField()
    cpu_arch = serializers.CharField()
    tags = serializers.SerializerMethodField()
    created_by = serializers.CharField()
    created_time = serializers.DateTimeField()
    is_ready = serializers.BooleanField()


class ListResponseSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    list = PackageSerializer(many=True)


class OperateSerializer(serializers.Serializer):
    is_ready = serializers.BooleanField(required=False)
    tags = serializers.ListField(required=False)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


# class QuickSearchSerializer(serializers.Serializer):
#     project = serializers.ChoiceField(choices=GsePackageCode.list_choices())


class UploadSerializer(serializers.Serializer):
    overload = serializers.BooleanField(default=False, help_text="是否覆盖上传")
    package_file = serializers.FileField()

    def validate(self, data):
        overload = data.get("overload")
        package_file = data.get("package_file")

        file_name = package_file.name

        if not (file_name.endswith(".tgz") or file_name.endswith(".tar.gz")):
            raise ValidationError(_("仅支持'tgz', 'tar.gz'拓展名的文件"))

        if not overload:
            upload_package: UploadPackage = UploadPackage.objects.filter(
                file_name__contains=file_name, module=TargetType.AGENT.value
            ).first()
            if upload_package:
                raise ValidationError(
                    data={
                        "message": _("存在同名agent包"),
                        "file_name": upload_package.file_name,
                        "md5": upload_package.md5,
                    },
                    code=3800002,
                )

        return data


class UploadResponseSerializer(serializers.Serializer):
    name = serializers.CharField()
    pkg_size = serializers.IntegerField()


class ParseSerializer(serializers.Serializer):
    file_name = serializers.CharField()


class ParseResponseSerializer(serializers.Serializer):
    class ParsePackageSerializer(serializers.Serializer):
        project = serializers.ChoiceField(choices=["gse_agent", "gse_proxy"], required=False)
        pkg_name = serializers.CharField(required=False, source="pkg_relative_path")
        version = serializers.CharField(required=False)
        os = serializers.CharField()
        cpu_arch = serializers.CharField()
        config_templates = serializers.ListField(default=[])

        def to_representation(self, instance):
            data = super().to_representation(instance)
            data["project"] = self.context.get("project", "")
            data["version"] = self.context.get("version", "")
            return data

    description = serializers.CharField()
    packages = ParsePackageSerializer(many=True)


class AgentRegisterSerializer(serializers.Serializer):
    file_name = serializers.CharField()
    tags = serializers.ListField(child=serializers.CharField(), default=[])
    tag_descriptions = serializers.ListField(child=serializers.CharField(max_length=32), default=[])
    project = serializers.CharField(default=GsePackageCode.AGENT.value)


class AgentRegisterTaskSerializer(serializers.Serializer):
    task_id = serializers.CharField()
    version = serializers.CharField()


class AgentRegisterTaskResponseSerializer(serializers.Serializer):
    is_finish = serializers.BooleanField()
    status = serializers.ChoiceField(choices=["SUCCESS", "FAILED", "RUNNING"])
    message = serializers.CharField()


class DeployedAgentCountSerializer(serializers.Serializer):
    items = serializers.JSONField(default=[])
    project = serializers.CharField(default=GsePackageCode.AGENT.value)
    biz_scope = serializers.ListField(child=serializers.IntegerField(), default=[])


class VersionQuerySerializer(serializers.Serializer):
    project = serializers.CharField()
    os = serializers.CharField(required=False, allow_blank=True)
    cpu_arch = serializers.CharField(required=False, allow_blank=True)
    versions = serializers.ListField(child=serializers.CharField(), required=False)


class VersionCompareSerializer(serializers.Serializer):
    current_version = serializers.CharField()
    version_to_compares = serializers.ListField(child=serializers.CharField())
