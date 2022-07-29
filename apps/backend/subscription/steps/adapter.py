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
import copy
import logging
from collections import ChainMap, OrderedDict, defaultdict
from typing import Any, Dict, List, Union

from django.db.models import Max, Subquery
from django.utils.translation import ugettext as _
from rest_framework import exceptions, serializers

from apps.backend.plugin.tools import fetch_latest_config_templates
from apps.backend.subscription import errors
from apps.node_man import constants, models

logger = logging.getLogger("app")


class StepConfigCheckAndSkipSer(serializers.Serializer):
    check_and_skip = serializers.BooleanField(required=False, default=False, label="安装主插件支持检查是否存在并跳过")
    # check_and_skip=True 时生效：True - 版本不一致时进行安装 / False - 忽略版本不一致的情况，只要保证存活即可
    is_version_sensitive = serializers.BooleanField(required=False, default=False, label="是否强校验安装版本")


class ConfigTemplateSerializer(serializers.Serializer):
    name = serializers.CharField(required=True, label="配置文件名")
    version = serializers.CharField(required=True, label="配置文件版本号")
    is_main = serializers.BooleanField(default=False, label="是否主配置")
    os = serializers.ChoiceField(required=False, label="操作系统", choices=constants.OS_TUPLE)
    cpu_arch = serializers.ChoiceField(required=False, label="CPU类型", choices=constants.CPU_TUPLE)


class PluginStepConfigSerializer(StepConfigCheckAndSkipSer):
    plugin_name = serializers.CharField(required=True, label="插件名称")
    plugin_version = serializers.CharField(required=True, label="插件版本")
    config_templates = ConfigTemplateSerializer(default=[], many=True, label="配置模板列表", allow_empty=True)

    job_type = serializers.ChoiceField(required=False, allow_null=True, allow_blank=True, choices=constants.JOB_TUPLE)


class PolicyConfigTemplateSerializer(ConfigTemplateSerializer):
    id = serializers.IntegerField(required=True, label="配置模板id")


class PolicyStepConfigSerializer(StepConfigCheckAndSkipSer):
    class PolicyPackageSerializer(serializers.Serializer):
        project = serializers.CharField(required=True, label="插件名称")  # TODO 策略传参优化后移除

        id = serializers.IntegerField(required=True, label="package id")
        version = serializers.CharField(required=True, label="插件版本")
        os = serializers.CharField(required=True, label="操作系统")
        cpu_arch = serializers.CharField(required=True, label="cpu架构")
        config_templates = serializers.ListField(
            required=False, label="配置模板列表", child=PolicyConfigTemplateSerializer(), default=[]
        )

    job_type = serializers.ChoiceField(
        required=False, allow_null=True, allow_blank=True, choices=constants.PLUGIN_JOB_TUPLE
    )

    plugin_name = serializers.CharField(required=False, label="插件名称", default="")
    details = serializers.ListField(required=True, min_length=1, child=PolicyPackageSerializer())

    def validate(self, attrs):
        # TODO 后续策略配置移除project，放到字典第一层作为plugin_name
        project_set = set([detail["project"] for detail in attrs["details"]])
        if len(project_set) != 1:
            raise serializers.ValidationError(f"package's project should be the same, but not {project_set}")
        if not attrs["plugin_name"]:
            attrs["plugin_name"] = attrs["details"][0]["project"]
        return attrs


class PluginStepParamsSerializer(serializers.Serializer):
    port_range = serializers.CharField(label="端口范围", required=False, allow_null=True, allow_blank=True)
    context = serializers.DictField(default={}, label="配置文件渲染上下文")
    keep_config = serializers.BooleanField(label="是否保留原有配置文件", allow_null=True, required=False, default=False)
    no_restart = serializers.BooleanField(label="仅更新文件，不重启进程", allow_null=True, required=False, default=False)


class PolicyStepParamsSerializer(serializers.Serializer):
    class PolicyStepParamsInfo(PluginStepParamsSerializer):
        os = serializers.CharField(required=True, label="操作系统")
        cpu_arch = serializers.CharField(required=True, label="cpu架构")

    details = serializers.ListField(child=PolicyStepParamsInfo())


class PolicyStepAdapter:
    def __init__(self, subscription_step: models.SubscriptionStep):
        self.subscription_step: models.SubscriptionStep = subscription_step
        self.subscription: models.Subscription = subscription_step.subscription
        self.log_prefix: str = (
            f"[{self.__class__.__name__}({self.subscription_step.step_id})] "
            f"{self.subscription} | {self.subscription_step} |"
        )

        self.plugin_name = self.config["plugin_name"]
        self.selected_pkg_infos: List[Dict] = self.config["details"]

        self.except_os_key_pkg_map: Dict[str, Dict] = {
            self.get_os_key(pkg["os"], pkg["cpu_arch"]): pkg for pkg in self.selected_pkg_infos
        }

    @property
    def config(self) -> OrderedDict:
        if hasattr(self, "_config") and self._config:
            return self._config
        policy_config = self.format2policy_config(self.subscription_step.config)

        # 处理同名配置模板，取最新版本
        for selected_pkg_info in policy_config["details"]:
            selected_pkg_info["config_templates"] = fetch_latest_config_templates(
                config_templates=selected_pkg_info["config_templates"], plugin_version=selected_pkg_info["version"]
            )

        setattr(self, "_config", self.validated_data(data=policy_config, serializer=PolicyStepConfigSerializer))
        return self._config

    @property
    def params(self) -> OrderedDict:
        if hasattr(self, "_params") and self._params:
            return self._params
        policy_params = self.format2policy_params(self.subscription_step.params)
        setattr(self, "_params", self.validated_data(data=policy_params, serializer=PolicyStepParamsSerializer))
        return self._params

    @property
    def plugin_desc(self) -> models.GsePluginDesc:
        if hasattr(self, "_plugin_desc") and self._plugin_desc:
            return self._plugin_desc
        try:
            plugin_desc = models.GsePluginDesc.objects.get(name=self.plugin_name)
        except models.GsePluginDesc.DoesNotExist:
            raise errors.PluginValidationError(msg="插件 [{name}] 信息不存在".format(name=self.plugin_name))

        setattr(self, "_plugin_desc", plugin_desc)
        return self._plugin_desc

    @property
    def config_inst_gby_os_key(self) -> Dict[str, List[models.PluginConfigInstance]]:
        if hasattr(self, "_config_inst_gby_os_key"):
            return self._config_inst_gby_os_key

        config_inst_gby_os_key = {}
        for os_key, config_templates in self.config_tmpl_obj_gby_os_key.items():
            config_inst_gby_os_key[os_key] = [
                config_template.create_instance(
                    data=self.get_matching_step_params(os_key=os_key).get("context", {}),
                    source_app_code=self.subscription.from_system,
                )
                for config_template in config_templates
            ]

        setattr(self, "_config_inst_gby_os_key", config_inst_gby_os_key)
        return self._config_inst_gby_os_key

    @property
    def config_tmpl_obj_gby_os_key(self) -> Dict[str, List[models.PluginConfigTemplate]]:
        if hasattr(self, "_config_tmpl_obj_gby_os_key"):
            return self._config_tmpl_obj_gby_os_key

        all_config_tmpl_ids = []
        os_key_gby_config_tmpl_id = defaultdict(list)
        for pkg in self.selected_pkg_infos:
            config_tmpl_ids = [config_tmpl["id"] for config_tmpl in pkg["config_templates"]]
            for config_tmpl_id in config_tmpl_ids:
                os_key_gby_config_tmpl_id[config_tmpl_id].append(self.get_os_key(pkg["os"], pkg["cpu_arch"]))
            all_config_tmpl_ids.extend(config_tmpl_ids)
        all_config_tmpl_ids = list(set(all_config_tmpl_ids))

        config_tmpl_obj_gby_os_key: Dict[str, List[models.PluginConfigTemplate]] = defaultdict(list)
        for config_template in models.PluginConfigTemplate.objects.filter(id__in=all_config_tmpl_ids):
            for os_key in os_key_gby_config_tmpl_id[config_template.id]:
                config_tmpl_obj_gby_os_key[os_key].append(config_template)

        logger.info(f"{self.log_prefix} config_tmpl_obj_gby_os_key -> {config_tmpl_obj_gby_os_key}")
        setattr(self, "_config_tmpl_obj_gby_os_key", config_tmpl_obj_gby_os_key)
        return self._config_tmpl_obj_gby_os_key

    @property
    def os_key_pkg_map(self) -> Dict[str, models.Packages]:
        if hasattr(self, "_os_key_pkg_map"):
            return self._os_key_pkg_map

        packages = models.Packages.objects.filter(id__in=[pkg["id"] for pkg in self.selected_pkg_infos])
        os_cpu_pkg_map = {self.get_os_key(package.os, package.cpu_arch): package for package in packages}

        if not os_cpu_pkg_map:
            raise errors.PluginValidationError(
                msg="插件 [{name}-{versions}] 不存在".format(
                    name=self.plugin_name, versions=set([pkg["version"] for pkg in self.selected_pkg_infos])
                )
            )

        logger.info(f"{self.log_prefix} os_key_pkg_map -> {os_cpu_pkg_map}")
        setattr(self, "_os_key_pkg_map", os_cpu_pkg_map)
        return self._os_key_pkg_map

    @property
    def os_key_params_map(self) -> Dict[str, Dict[str, Any]]:
        if hasattr(self, "_os_key_params_map"):
            return self._os_key_params_map
        policy_params_list = self.params["details"]
        os_cpu_params_map = {
            self.get_os_key(policy_params["os"], policy_params["cpu_arch"]): policy_params
            for policy_params in policy_params_list
        }
        setattr(self, "_os_key_params_map", os_cpu_params_map)
        return self._os_key_params_map

    def format2policy_config(self, original_config: Dict):
        try:
            format_result = self.validated_data(data=original_config, serializer=PolicyStepConfigSerializer)
        except exceptions.ValidationError:
            pass
        else:
            return format_result

        validated_config = self.validated_data(data=original_config, serializer=PluginStepConfigSerializer)
        plugin_name = validated_config["plugin_name"]
        plugin_version = validated_config["plugin_version"]

        if plugin_version != "latest":
            packages = models.Packages.objects.filter(
                project=plugin_name,
                version=plugin_version,
            )
        else:
            newest = (
                models.Packages.objects.filter(project=plugin_name).values("os", "cpu_arch").annotate(max_id=Max("id"))
            )
            packages = models.Packages.objects.filter(id__in=Subquery(newest.values("max_id")))

        if not packages:
            raise errors.PluginValidationError(
                msg=_("插件包 [{name}-{version}] 不存在").format(name=plugin_name, version=plugin_version)
            )

        latest_packages_version_set = set(packages.values_list("version", flat=True))
        os_cpu__config_templates_map = defaultdict(list)
        for template in validated_config["config_templates"]:
            is_main_template = template["is_main"]
            if template["version"] != "latest":
                plugin_version_set = {plugin_version, "*"}
            else:
                plugin_version_set = latest_packages_version_set | {"*"}
            config_templates_group_by_os_cpu = (
                models.PluginConfigTemplate.objects.filter(
                    plugin_version__in=plugin_version_set,
                    name=template["name"],
                    plugin_name=plugin_name,
                    is_main=is_main_template,
                )
                .values("os", "cpu_arch")
                .annotate(max_id=Max("id"))
            )
            config_templates = models.PluginConfigTemplate.objects.filter(
                id__in=Subquery(config_templates_group_by_os_cpu.values("max_id"))
            )

            for config_template in config_templates:
                os_cpu__config_templates_map[self.get_os_key(config_template.os, config_template.cpu_arch)].append(
                    {
                        "id": config_template.id,
                        "version": config_template.version,
                        "name": config_template.name,
                        "os": config_template.os,
                        "cpu_arch": config_template.cpu_arch,
                        "is_main": config_template.is_main,
                    }
                )

        policy_packages: List[Dict[str, Union[str, List[Dict[str, Any]]]]] = []
        for package in packages:
            policy_packages.append(
                {
                    "id": package.id,
                    "project": package.project,
                    "version": package.version,
                    "cpu_arch": package.cpu_arch,
                    "os": package.os,
                    "config_templates": os_cpu__config_templates_map[self.get_os_key(package.os, package.cpu_arch)],
                }
            )

        policy_step_config = {**copy.deepcopy(validated_config), "details": policy_packages}

        # 补充original_config中部分必要参数
        return self.fill_additional_keys(
            target=policy_step_config, origin=original_config, additional_keys=["job_type"]
        )

    def format2policy_params(self, original_params: Dict) -> Dict:
        try:
            # 尝试序列化为策略类型的参数
            self.validated_data(data=original_params, serializer=PolicyStepParamsSerializer)
        except exceptions.ValidationError:
            validated_params = self.validated_data(data=original_params, serializer=PluginStepParamsSerializer)
            policy_params_list = [
                {**copy.deepcopy(validated_params), "os": package["os"], "cpu_arch": package["cpu_arch"]}
                for package in self.config["details"]
            ]
            return {**copy.deepcopy(validated_params), "details": policy_params_list}
        else:
            # 适配操作系统类型参数
            for params in original_params["details"]:
                params["os"] = params.get("os") or params["os_type"]

            if self.subscription_step.id:
                self.subscription_step.save()
            return original_params

    @staticmethod
    def validated_data(data, serializer) -> OrderedDict:
        data_serializer = serializer(data=data)
        data_serializer.is_valid(raise_exception=True)
        return data_serializer.validated_data

    @staticmethod
    def fill_additional_keys(target: Dict, origin: Dict, additional_keys: List[str]) -> Dict:
        additional_map = {
            additional_key: origin[additional_key] for additional_key in additional_keys if additional_key in origin
        }
        # 字典具有相同键的情况下，位于ChainMap前的字典覆盖靠后的键值
        return dict(ChainMap(target, additional_map))

    @staticmethod
    def get_os_key(os_type: str, cpu_arch: str) -> str:
        # 默认为 linux-x86_64，兼容CMDB同步过来的主机没有操作系统和CPU架构的场景
        os_type = os_type or constants.OsType.LINUX
        cpu_arch = cpu_arch or constants.CpuType.x86_64
        return f"{os_type.lower()}-{cpu_arch}"

    def get_matching_package_dict(self, os_type: str = None, cpu_arch: str = None, os_key: str = None) -> Dict:
        os_key = os_key or self.get_os_key(os_type, cpu_arch)
        package_dict = self.except_os_key_pkg_map.get(os_key)
        if not package_dict:
            raise errors.PluginValidationError(
                _("订阅安装插件[{plugin_name}] 未选择支持 [{os_key}] 的插件包").format(plugin_name=self.plugin_name, os_key=os_key)
            )
        return package_dict

    def get_matching_step_params(self, os_type: str = None, cpu_arch: str = None, os_key: str = None) -> Dict[str, Any]:

        # TODO 对于普通订阅，一份context被多个包用于渲染，存在windows机器使用linux的包，需要在获取参数也兼容一下🐎？
        if os_key:
            return self.os_key_params_map.get(os_key)
        return self.os_key_params_map.get(self.get_os_key(os_type, cpu_arch), {})

    def get_matching_package_obj(self, os_type: str, cpu_arch: str) -> models.Packages:
        try:
            package = self.os_key_pkg_map[self.get_os_key(os_type, cpu_arch)]
        except KeyError:
            msg = _("插件 [{name}] 不支持 系统:{os_type}-架构:{cpu_arch}-版本:{plugin_version}").format(
                name=self.plugin_name,
                os_type=os_type,
                cpu_arch=cpu_arch,
                plugin_version=self.get_matching_package_dict(os_type, cpu_arch)["version"],
            )
            raise errors.PackageNotExists(msg)
        else:
            if not package.is_ready:
                msg = _("插件 [{name}] 系统:{os_type}-架构:{cpu_arch}-版本:{plugin_version} 未启用").format(
                    name=self.plugin_name,
                    os_type=os_type,
                    cpu_arch=cpu_arch,
                    plugin_version=self.get_matching_package_dict(os_type, cpu_arch)["version"],
                )
                raise errors.PluginValidationError(msg)
            return package

    def get_matching_config_tmpl_objs(self, os_type: str, cpu_arch: str) -> List[models.PluginConfigTemplate]:
        return self.config_tmpl_obj_gby_os_key.get(self.get_os_key(os_type, cpu_arch), [])
