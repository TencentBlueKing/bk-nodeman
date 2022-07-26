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
from django.utils.translation import get_language
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from apps.exceptions import ValidationError
from apps.node_man.constants import (
    CATEGORY_CHOICES,
    CONFIG_FILE_FORMAT_CHOICES,
    CPU_CHOICES,
    PLUGIN_JOB_TUPLE,
    PLUGIN_OS_CHOICES,
    JobType,
    ProcType,
)
from apps.node_man.models import GsePluginDesc, Packages, ProcControl, ProcessStatus


class GsePluginSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False, max_length=32)
    description = serializers.CharField(required=False)
    scenario = serializers.CharField(required=False)
    description_en = serializers.CharField(required=False)
    scenario_en = serializers.CharField(required=False)
    category = serializers.ChoiceField(required=False, choices=CATEGORY_CHOICES)

    config_file = serializers.CharField(required=False, max_length=128, allow_null=True, allow_blank=True)
    config_format = serializers.ChoiceField(
        required=False, choices=CONFIG_FILE_FORMAT_CHOICES, allow_null=True, allow_blank=True
    )

    use_db = serializers.BooleanField(required=False)
    is_binary = serializers.BooleanField(required=False)
    auto_launch = serializers.BooleanField(required=False)

    node_manage_control = serializers.JSONField(required=False)

    class Meta:
        model = GsePluginDesc
        fields = (
            "id",
            "name",
            "description",
            "description_en",
            "scenario",
            "scenario_en",
            "category",
            "config_file",
            "config_format",
            "use_db",
            "is_binary",
            "auto_launch",
            "node_manage_control",
        )

    def to_representation(self, instance):
        ret = super(GsePluginSerializer, self).to_representation(instance)
        if get_language() == "en":
            ret["description"] = ret["description_en"]
            ret["scenario"] = ret["scenario_en"]
        return ret

    def create(self, validated_data):
        data = {"name": validated_data["name"]}
        gse_plugin, created = GsePluginDesc.objects.update_or_create(defaults=validated_data, **data)
        return gse_plugin


class ProcessPackageSerializer(serializers.ModelSerializer):
    """
    插件更新包信息表
    """

    pkg_name = serializers.CharField(required=False, max_length=128)
    version = serializers.CharField(required=False, max_length=128)
    module = serializers.CharField(required=False, max_length=32)
    project = serializers.CharField(required=False, max_length=128)
    pkg_size = serializers.IntegerField(required=False)
    pkg_path = serializers.CharField(required=False, max_length=128)
    md5 = serializers.CharField(required=False, max_length=32)
    pkg_mtime = serializers.CharField(required=False, max_length=48)
    pkg_ctime = serializers.CharField(required=False, max_length=48)
    location = serializers.CharField(required=False, max_length=512)
    os = serializers.ChoiceField(required=False, choices=PLUGIN_OS_CHOICES)
    cpu_arch = serializers.ChoiceField(required=False, choices=CPU_CHOICES)

    class Meta:
        model = Packages
        fields = (
            "id",
            "pkg_name",
            "version",
            "module",
            "project",
            "pkg_size",
            "pkg_path",
            "md5",
            "pkg_mtime",
            "pkg_ctime",
            "location",
            "os",
            "cpu_arch",
        )

    def create(self, validated_data):
        data = {
            "module": validated_data["module"],
            "project": validated_data["project"],
            "version": validated_data["version"],
            "os": validated_data["os"],
            "cpu_arch": validated_data["cpu_arch"],
        }
        process_package, created = Packages.objects.update_or_create(defaults=validated_data, **data)
        return process_package


class ProcessStatusSerializer(serializers.ModelSerializer):
    """
    process运行状态的序列化
    """

    bk_host_id = serializers.IntegerField()
    name = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    version = serializers.CharField(required=False)

    class Meta:
        model = ProcessStatus
        fields = ("bk_host_id", "name", "status", "version")


class ProcessControlInfoSerializer(serializers.ModelSerializer):
    module = serializers.CharField(required=False, max_length=32)
    project = serializers.CharField(required=False, max_length=32)

    plugin_package_id = serializers.IntegerField(required=False)
    install_path = serializers.CharField(required=False, max_length=128)
    log_path = serializers.CharField(required=False, max_length=128)
    data_path = serializers.CharField(required=False, max_length=128)
    pid_path = serializers.CharField(required=False, max_length=128)
    start_cmd = serializers.CharField(required=False, max_length=128)
    stop_cmd = serializers.CharField(required=False, max_length=128)
    restart_cmd = serializers.CharField(required=False, max_length=128)
    reload_cmd = serializers.CharField(required=False, max_length=128)

    kill_cmd = serializers.CharField(required=False, max_length=128)
    version_cmd = serializers.CharField(required=False, max_length=128)
    health_cmd = serializers.CharField(required=False, max_length=128)
    debug_cmd = serializers.CharField(required=False, max_length=128)

    os = serializers.ChoiceField(required=False, choices=PLUGIN_OS_CHOICES)

    class Meta:
        model = ProcControl
        fields = (
            "id",
            "module",
            "project",
            "install_path",
            "log_path",
            "data_path",
            "pid_path",
            "start_cmd",
            "stop_cmd",
            "restart_cmd",
            "reload_cmd",
            "kill_cmd",
            "version_cmd",
            "health_cmd",
            "debug_cmd",
            "os",
            "plugin_package_id",
        )

    def create(self, validated_data):
        data = {
            "module": validated_data["module"],
            "project": validated_data["project"],
            "os": validated_data["os"],
        }
        process_info, created = ProcControl.objects.update_or_create(defaults=validated_data, **data)
        return process_info


class PluginListSerializer(serializers.Serializer):
    bk_biz_id = serializers.ListField(help_text=_("业务ID"), required=False, child=serializers.IntegerField())
    bk_host_id = serializers.ListField(help_text=_("主机ID"), required=False, child=serializers.IntegerField())
    bk_cloud_id = serializers.ListField(help_text=_("云区域ID"), required=False, child=serializers.IntegerField())
    conditions = serializers.ListField(help_text=_("搜索条件"), required=False)
    version = serializers.ListField(help_text=_("Agent版本"), required=False)
    exclude_hosts = serializers.ListField(help_text=_("跨页全选排除主机"), required=False)
    page = serializers.IntegerField(label=_("当前页数"), required=False, default=1)
    pagesize = serializers.IntegerField(label=_("分页大小"), required=False, default=10)
    only_ip = serializers.BooleanField(label=_("只返回IP"), required=False, default=False)
    simple = serializers.BooleanField(label=_("仅返回概要信息(bk_host_id, bk_biz_id)"), required=False, default=False)
    detail = serializers.BooleanField(label=_("是否节点详情"), required=False, default=False)

    with_agent_status_counter = serializers.BooleanField(label=_("是否返回Agent状态统计信息"), default=False)


class PluginInfoSerializer(serializers.Serializer):
    name = serializers.CharField(label=_("插件名称"), required=True)
    version = serializers.CharField(label=_("插件版本"), required=False, default="latest")
    keep_config = serializers.BooleanField(label=_("保留原有配置"), required=False)
    no_restart = serializers.BooleanField(label=_("不重启进程"), required=False)

    def validate(self, attrs):

        if attrs["name"] == JobType.MAIN_INSTALL_PLUGIN and (
            not attrs.get("keep_config") or not attrs.get("no_restart")
        ):
            raise ValidationError("更新插件必须传配置参数")

        return attrs

    class Meta:
        # swagger 特殊启动标注，有更优解可去除
        ref_name = "PluginInfoSerializer"


class OperateSerializer(serializers.Serializer):
    job_type = serializers.ChoiceField(label=_("任务类型"), choices=list(PLUGIN_JOB_TUPLE))
    bk_biz_id = serializers.ListField(label=_("业务ID"), required=False)
    bk_cloud_id = serializers.ListField(label=_("云区域ID"), required=False)
    version = serializers.ListField(label=_("Agent版本"), required=False)
    # V2.0.x 参数
    plugin_params = PluginInfoSerializer(label=_("插件信息"), required=False)
    # V2.1.x 插件参数，支持批量操作
    plugin_params_list = serializers.ListField(child=PluginInfoSerializer(label=_("插件信息列表")), required=False)
    conditions = serializers.ListField(label=_("搜索条件"), required=False)
    bk_host_id = serializers.ListField(label=_("主机ID"), required=False)
    exclude_hosts = serializers.ListField(label=_("跨页全选排除主机"), required=False)

    # 以下非参数传值
    op_type = serializers.CharField(label=_("操作类型,"), required=False)
    node_type = serializers.CharField(label=_("节点类型"), required=False)

    def validate(self, attrs):
        # 取得操作类型
        attrs["op_type"] = attrs["job_type"].split("_")[1]
        attrs["node_type"] = attrs["job_type"].split("_")[2]

        if not (attrs.get("plugin_params") or attrs.get("plugin_params_list")):
            # 两个参数都没有，直接抛异常
            raise ValidationError(_("插件参数 plugin_params 和 plugin_params_list 参数不能同时为空"))

        if attrs.get("plugin_params"):
            # 把2.0.x 的参数转为 2.1.x 的参数
            attrs["plugin_params_list"] = [attrs.get("plugin_params")]

        if attrs.get("exclude_hosts") is not None and attrs.get("bk_host_id") is not None:
            raise ValidationError(_("跨页全选模式下不允许传bk_host_id参数."))
        if attrs.get("exclude_hosts") is None and attrs.get("bk_host_id") is None:
            raise ValidationError(_("必须选择一种模式(【是否跨页全选】)"))

        if attrs["node_type"] != ProcType.PLUGIN:
            raise ValidationError(_("插件管理只允许对插件进行操作."))

        plugin_names = [plugin_params["name"] for plugin_params in attrs["plugin_params_list"]]
        if len(plugin_names) != len(set(plugin_names)):
            raise ValidationError(_("不允许选择重复的插件进行操作"))
        return attrs
