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
from rest_framework.exceptions import ValidationError

from apps.node_man import constants, exceptions, models
from apps.node_man.serializers import base
from apps.node_man.serializers.host_v2 import NodeSerializer


class PluginEditSerializer(serializers.Serializer):
    """更新插件验证"""

    description = serializers.CharField(label=_("插件别名"), min_length=1)


class ReleasePluginSerializer(serializers.Serializer):
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


class PluginStatusOperationSerializer(serializers.Serializer):
    operation = serializers.CharField()
    id = serializers.ListField(child=serializers.IntegerField(), min_length=1)

    def validate(self, data):
        if data["operation"] not in constants.PLUGIN_STATUS_OP_TUPLE:
            raise ValidationError("[operation] must be one of: %s" % str(constants.PLUGIN_STATUS_OP_TUPLE))
        return data


class PluginRegisterSerializer(serializers.Serializer):
    file_name = serializers.CharField()
    is_release = serializers.BooleanField()

    # 两个配置文件相关参数选填，兼容监控
    # 是否需要读取配置文件
    is_template_load = serializers.BooleanField(required=False, default=False)
    # 是否可以覆盖已经存在的配置文件
    is_template_overwrite = serializers.BooleanField(required=False, default=False)

    select_pkg_abs_paths = serializers.ListField(required=False, min_length=1, child=serializers.CharField())


class PluginRegisterTaskSerializer(serializers.Serializer):
    job_id = serializers.IntegerField()


class QueryExportTaskSerializer(PluginRegisterTaskSerializer):
    job_id = serializers.IntegerField()


class ExportSerializer(serializers.Serializer):
    """
    导出包序列化器
    """

    class GsePluginV2ParamsSerializer(serializers.Serializer):
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

    category = serializers.CharField()
    query_params = GsePluginV2ParamsSerializer()


class PluginQueryHistorySerializer(serializers.Serializer):
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


class PluginParseSerializer(serializers.Serializer):
    file_name = serializers.CharField()
    is_update = serializers.BooleanField(required=False, default=False)
    project = serializers.CharField(required=False)

    def validate(self, data):
        # 检查插件是否存在
        if "project" not in data or models.GsePluginDesc.objects.filter(name=data["project"]).first():
            return data
        raise ValidationError("plugin {name} is not exist".format(name=data["project"]))


class PluginListSerializer(serializers.Serializer):
    class SortSerializer(serializers.Serializer):
        head = serializers.ChoiceField(choices=list(constants.PLUGIN_HEAD_TUPLE))
        sort_type = serializers.ChoiceField(choices=list(constants.SORT_TUPLE))

    page = serializers.IntegerField(required=False, default=1)
    pagesize = serializers.IntegerField(required=False, default=10)
    search = serializers.CharField(required=False)
    simple_all = serializers.BooleanField(required=False, default=False)
    sort = SortSerializer(required=False)


class PluginUploadSerializer(serializers.Serializer):
    class PkgFileField(serializers.FileField):
        def to_internal_value(self, data):
            data = super().to_internal_value(data)
            file_name = data.name
            if not (file_name.endswith(".tgz") or file_name.endswith(".tar.gz")):
                raise ValidationError(_("仅支持'tgz', 'tar.gz'拓展名的文件"))
            return data

    module = serializers.CharField(max_length=32, required=False, default="gse_plugin")
    package_file = PkgFileField()


class PluginListHostSerializer(serializers.Serializer):
    bk_biz_id = serializers.ListField(label=_("业务ID"), required=False)
    bk_host_id = serializers.ListField(label=_("主机ID"), required=False)
    project = serializers.CharField(label=_("插件名称"), required=True)
    conditions = serializers.ListField(label=_("搜索条件"), required=False)
    nodes = serializers.ListField(label=_("拓扑节点列表"), child=NodeSerializer(), required=False)
    page = serializers.IntegerField(label=_("当前页数"), required=False, default=1)
    pagesize = serializers.IntegerField(label=_("分页大小"), required=False, default=10)
    exclude_hosts = serializers.ListField(label=_("跨页全选排除主机"), required=False)

    def validate(self, data):
        if not models.GsePluginDesc.objects.filter(name=data["project"]).exists():
            raise ValidationError(_("插件[{project}] 不存在").format(project=data["project"]))
        return data


class PluginFetchConfigVarsSerializer(serializers.Serializer):
    config_tpl_ids = serializers.ListField(
        label=_("配置模板ID列表"), child=serializers.IntegerField(min_value=0), min_length=1
    )

    def validate(self, data):
        data["config_tpl_ids"] = list(set(data["config_tpl_ids"]))
        return data


class PluginOperateSerializer(serializers.Serializer):
    job_type = serializers.ChoiceField(label=_("任务类型"), choices=list(constants.PLUGIN_JOB_TUPLE))
    plugin_name = serializers.CharField(label=_("插件名称"))
    # 一次性任务范围
    scope = base.ScopeSerializer()
    # 参数配置
    steps = serializers.ListField(child=base.StepSerializer(), required=False, default=[])

    def validate(self, data):
        if models.GsePluginDesc.objects.filter(name=data["plugin_name"]).first() is None:
            raise exceptions.PluginNotExistError(_("不存在名称为: {name} 的插件").format(name=data["plugin_name"]))

        if data["job_type"] == constants.JobType.MAIN_INSTALL_PLUGIN and not data["steps"]:
            raise ValidationError(_("插件安装/更新需要传递steps"))

        return data


class FetchPackageDeployInfoSerializer(serializers.Serializer):
    projects = serializers.ListField(label=_("插件名称列表"), child=serializers.CharField(min_length=1))
    keys = serializers.ListField(
        label=_("聚合关键字，可选：os/version/cpu_arch"), child=serializers.CharField(min_length=1), required=False, default=[]
    )

    def validate(self, data):
        data["projects"] = list(set(data["projects"]))

        illegal_keywords = []
        optional_keys = {"os", "version", "cpu_arch"}
        for key in data["keys"]:
            if key not in optional_keys:
                illegal_keywords.append(key)

        if illegal_keywords:
            raise ValidationError(
                _("存在非法关键字 -> {illegal_keywords}, 可选项为 -> {optional_keys}").format(
                    illegal_keywords=illegal_keywords, optional_keys=optional_keys
                )
            )
        return data


class FetchResourcePolicyStatusSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(label=_("业务ID"))
    bk_obj_id = serializers.CharField(label=_("对象ID"))


class FetchResourcePolicySerializer(FetchResourcePolicyStatusSerializer):
    bk_inst_id = serializers.IntegerField(label=_("实例ID"))


class SetResourcePolicySerializer(FetchResourcePolicySerializer):
    class ResourcePolicySerializer(serializers.Serializer):
        plugin_name = serializers.CharField(label=_("插件名称"))
        cpu = serializers.IntegerField(label=_("CPU限额"))
        mem = serializers.IntegerField(label=_("内存限额"))

    resource_policy = serializers.ListField(child=ResourcePolicySerializer())
