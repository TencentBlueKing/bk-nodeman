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

import base64
import hashlib

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.node_man import constants
from apps.node_man.models import DownloadRecord, GsePluginDesc, Packages


class GatewaySerializer(serializers.Serializer):
    bk_username = serializers.CharField()
    bk_app_code = serializers.CharField()


class PluginInfoSerializer(GatewaySerializer):
    """插件信息接口序列化器"""

    name = serializers.CharField(max_length=32)
    version = serializers.CharField(max_length=128, required=False)
    cpu_arch = serializers.CharField(max_length=32, allow_null=True, required=False)
    os = serializers.CharField(max_length=32, allow_null=True, required=False)

    def validate(self, attrs):
        # 检查插件是否存在
        try:
            plugin = GsePluginDesc.objects.get(name=attrs["name"])
        except GsePluginDesc.DoesNotExist:
            raise ValidationError("plugin {name} is not exist".format(name=attrs["name"]))
        attrs.pop("name")
        attrs["plugin"] = plugin

        return attrs


class ReleasePluginSerializer(GatewaySerializer):
    """发布插件序列化器"""

    id = serializers.ListField(child=serializers.IntegerField(), required=False, min_length=1)
    name = serializers.CharField(max_length=32, required=False)
    version = serializers.CharField(max_length=128, required=False)
    cpu_arch = serializers.CharField(max_length=32, allow_null=True, required=False)
    os = serializers.CharField(max_length=32, allow_null=True, required=False)
    md5_list = serializers.ListField(child=serializers.CharField(), min_length=1)

    def validate(self, attrs):
        # id或name至少要有一个
        if not ("id" in attrs or ("name" in attrs and "version" in attrs)):
            raise ValidationError("at least has 'id' or ('name' + 'version')")

        return attrs


class PkgStatusOperationSerializer(ReleasePluginSerializer):
    operation = serializers.CharField()

    def validate(self, attrs):
        super().validate(attrs)
        if attrs["operation"] not in constants.PKG_STATUS_OP_TUPLE:
            raise ValidationError("[operation] must be one of: %s" % str(constants.PKG_STATUS_OP_TUPLE))
        return attrs


class PluginStatusOperationSerializer(GatewaySerializer):
    operation = serializers.CharField()
    id = serializers.ListField(child=serializers.IntegerField(), min_length=1)

    def validate(self, data):
        if data["operation"] not in constants.PLUGIN_STATUS_OP_TUPLE:
            raise ValidationError("[operation] must be one of: %s" % str(constants.PLUGIN_STATUS_OP_TUPLE))
        return data


class CreatePluginConfigTemplateSerializer(GatewaySerializer):
    """创建插件配置模板"""

    plugin_name = serializers.CharField(max_length=32)
    plugin_version = serializers.CharField(max_length=128)
    name = serializers.CharField(max_length=32)
    version = serializers.CharField(max_length=128)
    format = serializers.CharField(max_length=16)
    file_path = serializers.CharField(max_length=128)
    content = serializers.CharField()
    md5 = serializers.CharField()
    is_release_version = serializers.BooleanField()

    def validate(self, attrs):
        # base64解码配置模板内容
        try:
            attrs["content"] = base64.b64decode(attrs["content"])
        except TypeError:
            raise ValidationError("content is not a valid base64 string")

        # 配置模板内容的md5是否匹配
        m = hashlib.md5()
        m.update(attrs["content"])
        if m.hexdigest() != attrs["md5"]:
            raise ValidationError("the md5 of content is not match")

        # 对应插件是否存在
        packages = Packages.objects.filter(project=attrs["plugin_name"])
        # 特殊版本不检查
        if attrs["plugin_version"] != "*":
            packages = packages.filter(version=attrs["plugin_version"])
        if not packages.exists():
            raise ValidationError(
                "plugin {plugin_name}:{plugin_version}".format(
                    plugin_name=attrs["plugin_name"],
                    plugin_version=attrs["plugin_version"],
                )
            )
        attrs["content"] = attrs["content"].decode()

        return attrs


class ReleasePluginConfigTemplateSerializer(GatewaySerializer):
    """发布插件配置模板"""

    plugin_name = serializers.CharField(max_length=32, required=False)
    plugin_version = serializers.CharField(max_length=128, required=False)
    name = serializers.CharField(max_length=32, required=False)
    version = serializers.CharField(max_length=32, required=False)
    id = serializers.ListField(child=serializers.IntegerField(), required=False, min_length=1)

    def validate(self, attrs):
        params_keys = {
            "plugin_name",
            "plugin_version",
        }

        # 两种参数模式少要有一种满足
        if not ("id" in attrs or len(params_keys - set(attrs.keys())) == 0):
            raise ValidationError("at least has 'id' or query params")

        return attrs


class RenderPluginConfigTemplateSerializer(GatewaySerializer):
    """渲染插件配置模板"""

    plugin_name = serializers.CharField(max_length=32, required=False)
    plugin_version = serializers.CharField(max_length=128, required=False)
    name = serializers.CharField(max_length=32, required=False)
    version = serializers.CharField(max_length=32, required=False)
    id = serializers.IntegerField(required=False)
    data = serializers.DictField()

    def validate(self, attrs):
        params_keys = {"plugin_name", "plugin_version", "name", "version"}

        # 两种参数模式少要有一种满足
        if not ("id" in attrs or len(params_keys - set(attrs.keys())) == 0):
            raise ValidationError("at least has 'id' or query params")

        return attrs


class PluginConfigTemplateInfoSerializer(GatewaySerializer):
    """插件配置模板信息"""

    plugin_name = serializers.CharField(max_length=32, required=False)
    plugin_version = serializers.CharField(max_length=128, required=False)
    name = serializers.CharField(max_length=32, required=False)
    version = serializers.CharField(max_length=32, required=False)
    id = serializers.IntegerField(required=False)

    def validate(self, attrs):
        # 两种参数模式少要有一种满足
        if not ("id" in attrs or len(list(attrs.keys())) > 2):
            raise ValidationError("at least has 'id' or query params")

        return attrs


class PluginConfigInstanceInfoSerializer(GatewaySerializer):
    """插件配置实例信息"""

    plugin_name = serializers.CharField(max_length=32, required=False)
    plugin_version = serializers.CharField(max_length=128, required=False)
    name = serializers.CharField(max_length=32, required=False)
    version = serializers.CharField(max_length=32, required=False)
    id = serializers.IntegerField(required=False)

    def validate(self, attrs):
        # 两种参数模式少要有一种满足
        if not ("id" in attrs or len(list(attrs.keys())) > 2):
            raise ValidationError("at least has 'id' or query params")

        return attrs


class UploadInfoBaseSerializer(GatewaySerializer):
    md5 = serializers.CharField(help_text=_("上传端计算的文件md5"), max_length=32)
    file_name = serializers.CharField(help_text=_("上传端提供的文件名"), min_length=1)
    module = serializers.CharField(max_length=32, required=False, default="gse_plugin")


class UploadInfoSerializer(UploadInfoBaseSerializer):
    """上传插件包接口序列化器"""

    file_local_path = serializers.CharField(help_text=_("本地文件路径"), max_length=512)
    file_local_md5 = serializers.CharField(help_text=_("Nginx所计算的文件md5"), max_length=32)


class CosUploadInfoSerializer(UploadInfoBaseSerializer):
    download_url = serializers.URLField(help_text=_("对象存储文件下载url"), required=False)
    file_path = serializers.CharField(help_text=_("文件保存路径"), min_length=1, required=False)

    def validate(self, attrs):
        # 两种参数模式少要有一种满足
        if not ("download_url" in attrs or "file_path" in attrs):
            raise ValidationError("at least has download_url or file_path")
        return attrs


class PluginStartDebugSerializer(GatewaySerializer):
    """
    启动调试参数信息
    """

    class HostInfoSerializer(serializers.Serializer):
        ip = serializers.CharField(required=True)
        bk_cloud_id = serializers.IntegerField(required=True)
        bk_supplier_id = serializers.IntegerField(default=constants.DEFAULT_SUPPLIER_ID)
        bk_biz_id = serializers.IntegerField(required=True)

    plugin_id = serializers.IntegerField(required=False)
    plugin_name = serializers.CharField(max_length=32, required=False)
    version = serializers.CharField(max_length=32, required=False)
    config_ids = serializers.ListField(default=[], allow_empty=True, child=serializers.IntegerField())
    host_info = HostInfoSerializer(required=True)

    def validate(self, attrs):
        # 两种参数模式少要有一种满足
        if "id" not in attrs and not ("plugin_name" in attrs and "version") in attrs:
            raise ValidationError("`plugin_id` or `plugin_name + version` required")

        return attrs


class PluginRegisterSerializer(GatewaySerializer):
    file_name = serializers.CharField(help_text=_("文件名称"))
    is_release = serializers.BooleanField(help_text=_("是否立即发布该插件"))

    # 两个配置文件相关参数选填，兼容监控
    is_template_load = serializers.BooleanField(help_text=_("是否需要读取配置文件"), required=False, default=False)
    is_template_overwrite = serializers.BooleanField(help_text=_("是否可以覆盖已经存在的配置文件"), required=False, default=False)

    # TODO 废弃字段，改用 select_pkg_relative_paths，待与前端联调后移除该字段
    select_pkg_abs_paths = serializers.ListField(required=False, min_length=1, child=serializers.CharField())

    select_pkg_relative_paths = serializers.ListField(
        required=False, min_length=1, child=serializers.CharField(), help_text=_("选择注册的插件包相对路径，缺省默认全选")
    )

    def validate(self, attrs):
        attrs["select_pkg_relative_paths"] = attrs.get("select_pkg_abs_paths")

        return attrs


class PluginRegisterTaskSerializer(GatewaySerializer):
    job_id = serializers.IntegerField()


class ExportSerializer(GatewaySerializer):
    """
    导出包序列化器
    """

    class GsePluginParamsSerializer(serializers.Serializer):
        """
        Gse 采集器序列化器
        """

        project = serializers.CharField()
        # 版本号不做正则校验，原因是各个版本指定规则不一，不好统一限制
        # 考虑应该通过DB查询进行进一步的限制即可
        version = serializers.CharField()
        os = serializers.CharField(required=False)
        cpu_arch = serializers.CharField(required=False)

        def validate(self, data):
            if "os" in data and data["os"] not in constants.PLUGIN_OS_TUPLE:
                raise ValidationError(
                    "os must be required [{os_types}]".format(os_types=", ".join(constants.PLUGIN_OS_TUPLE))
                )
            if "cpu_arch" in data and data["cpu_arch"] not in constants.CPU_TUPLE:
                raise ValidationError(
                    "cpu_arch must be required [{cpu_tuple}]".format(cpu_tuple=", ".join(constants.CPU_TUPLE))
                )
            return data

    category = serializers.ChoiceField(choices=DownloadRecord.CATEGORY_CHOICES)
    query_params = GsePluginParamsSerializer()
    creator = serializers.CharField()
    bk_app_code = serializers.CharField()


class DeletePluginSerializer(GatewaySerializer):
    name = serializers.CharField()


class PluginQueryHistorySerializer(GatewaySerializer):
    os = serializers.CharField(required=False)
    cpu_arch = serializers.CharField(required=False)
    pkg_ids = serializers.ListField(child=serializers.IntegerField(min_value=0), required=False)

    def validate(self, data):
        if "os" in data and data["os"] not in constants.PLUGIN_OS_TUPLE:
            raise ValidationError(
                "os must be required [{os_types}]".format(os_types=", ".join(constants.PLUGIN_OS_TUPLE))
            )
        if "cpu_arch" in data and data["cpu_arch"] not in constants.CPU_TUPLE:
            raise ValidationError(
                "cpu_arch must be required [{cpu_types}]".format(cpu_types=", ".join(constants.CPU_TUPLE))
            )
        return data


class PluginParseSerializer(GatewaySerializer):
    file_name = serializers.CharField()
    is_update = serializers.BooleanField(required=False, default=False)
    project = serializers.CharField(required=False)

    def validate(self, data):
        # 检查插件是否存在
        if "project" not in data or GsePluginDesc.objects.filter(name=data["project"]).first():
            return data
        raise ValidationError("plugin {name} is not exist".format(name=data["project"]))


class PluginListSerializer(GatewaySerializer):
    class SortSerializer(serializers.Serializer):
        head = serializers.ChoiceField(choices=list(constants.PLUGIN_HEAD_TUPLE))
        sort_type = serializers.ChoiceField(choices=list(constants.SORT_TUPLE))

    page = serializers.IntegerField(required=False, default=1)
    pagesize = serializers.IntegerField(required=False, default=10)
    search = serializers.CharField(required=False)
    simple_all = serializers.BooleanField(required=False, default=False)
    sort = SortSerializer(required=False)


class PluginUploadSerializer(GatewaySerializer):
    module = serializers.CharField(max_length=32, required=False, default="gse_plugin")
    file = serializers.FileField()
