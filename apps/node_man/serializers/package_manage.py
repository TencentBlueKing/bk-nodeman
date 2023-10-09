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

from apps.core.tag.models import Tag
from apps.exceptions import ValidationError
from apps.node_man.constants import BUILT_IN_TAG_NAMES, GsePackageCode
from apps.node_man.models import GsePackageDesc


class TagsSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField()


class ParentTagSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField()
    children = TagsSerializer(many=True)


class ConditionsSerializer(serializers.Serializer):
    key = serializers.ChoiceField(choices=["version", "os_cpu_arch", "tags", "is_ready"])
    values = serializers.ListField()


class BasePackageSerializer(serializers.Serializer):
    def get_tags(self, obj, to_top=False):
        agent_project_ids = GsePackageDesc.objects.filter(project=obj.project).values_list("id", flat=True)
        tags = Tag.objects.filter(target_id__in=agent_project_ids, target_version=obj.version).values_list(
            "name", "description"
        )
        if to_top:
            tags = [{"name": name, "description": description} for name, description in tags]
            return TagsSerializer(list(tags), many=True).data

        built_in_tags, custom_tags = self.split_builtin_tags_and_custom_tags(tags)
        parent_tags = [
            {"name": "builtin", "description": "内置标签", "children": built_in_tags},
            {"name": "custom", "description": "自定义标签", "children": custom_tags},
        ]
        self.filter_no_children_parent_tag(parent_tags)
        return ParentTagSerializer(parent_tags, many=True).data

    @classmethod
    def split_builtin_tags_and_custom_tags(cls, tags):
        """将标签拆分为内置的和自定义的"""
        built_in_tags, custom_tags = [], []
        for name, description in tags:
            if name in BUILT_IN_TAG_NAMES:
                built_in_tags.append({"name": name, "description": description})
            else:
                custom_tags.append({"name": name, "description": description})

        return built_in_tags, custom_tags

    @classmethod
    def filter_no_children_parent_tag(cls, parent_tags):
        for i in range(len(parent_tags) - 1, -1, -1):
            if not parent_tags[i].get("children"):
                parent_tags.pop(i)

    @classmethod
    def get_description(cls, obj):
        return GsePackageDesc.objects.filter(project=obj.project).first().description


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


class FilterConditionPackageSerializer(BasePackageSerializer):
    version = serializers.CharField()
    tags = serializers.SerializerMethodField()
    created_by = serializers.CharField()
    is_ready = serializers.BooleanField()


class QuickFilterConditionPackageSerializer(BasePackageSerializer):
    version = serializers.CharField()
    os = serializers.CharField()
    cpu_arch = serializers.CharField()


class VersionDescPackageSerializer(BasePackageSerializer):
    id = serializers.IntegerField()
    version = serializers.CharField()
    tags = serializers.SerializerMethodField()
    is_ready = serializers.BooleanField()
    description = serializers.SerializerMethodField()
    pkg_name = serializers.CharField()

    def get_tags(self, obj, to_top=False):
        return super().get_tags(obj, to_top=True)


class DescPackageSerializer(BasePackageSerializer):
    version = serializers.CharField()
    tags = serializers.SerializerMethodField()
    is_ready = serializers.BooleanField()
    description = serializers.SerializerMethodField()


class PackageDescSerializer(BasePackageSerializer):
    id = serializers.IntegerField()
    version = serializers.CharField()
    tags = serializers.SerializerMethodField()
    # packages = NameDescPackageSerializer(many=True)
    packages = serializers.SerializerMethodField()
    is_ready = serializers.BooleanField()
    # description = serializers.SerializerMethodField()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return data


class ListResponseSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    list = PackageSerializer(many=True)


class PackageDescResponseSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    list = PackageDescSerializer(many=True)


class OperateSerializer(serializers.Serializer):
    is_ready = serializers.BooleanField()

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


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
        project = serializers.ChoiceField(choices=["agent", "proxy"], required=False)
        pkg_name = serializers.CharField(required=False)
        pkg_abs_path = serializers.CharField(source="pkg_absolute_path")
        version = serializers.CharField(required=False)
        os = serializers.CharField()
        cpu_arch = serializers.CharField()
        config_templates = serializers.ListField(default=[])

        def to_representation(self, instance):
            data = super().to_representation(instance)
            data["project"] = self.context.get("project", "")
            data["pkg_name"] = self.context.get("pkg_name", "")
            data["version"] = self.context.get("version", "")
            return data

    description = serializers.CharField()
    packages = ParsePackageSerializer(many=True)


class AgentRegisterSerializer(serializers.Serializer):
    # class RegisterPackageSerializer(serializers.Serializer):
    #     pkg_abs_path = serializers.CharField()
    #     tags = serializers.ListField()
    #
    # is_release = serializers.BooleanField()
    # packages = RegisterPackageSerializer(many=True)
    file_name = serializers.CharField()
    tags = serializers.ListField(child=serializers.CharField())


class AgentRegisterTaskSerializer(serializers.Serializer):
    job_id = serializers.IntegerField()


class AgentRegisterTaskResponseSerializer(serializers.Serializer):
    is_finish = serializers.BooleanField()
    status = serializers.ChoiceField(choices=["SUCCESS", "FAILED", "RUNNING"])
    message = serializers.CharField()
