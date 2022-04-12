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
import logging
import os
import shutil
import tarfile
import traceback
from collections import defaultdict
from enum import Enum
from typing import Any, Dict, KeysView, List, Optional, Set, Union

import yaml
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from packaging import version
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.backend import exceptions
from apps.core.files.storage import get_storage
from apps.node_man import constants, models
from apps.utils import enum, env, files

logger = logging.getLogger("app")


class VariableType(enum.EnhanceEnum):
    OBJECT = "object"
    ARRAY = "array"
    NUMBER = "number"
    STRING = "string"
    BOOLEAN = "boolean"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {
            cls.OBJECT: _("字典"),
            cls.ARRAY: _("列表"),
            cls.NUMBER: _("数字"),
            cls.STRING: _("字符串"),
            cls.BOOLEAN: _("布尔值"),
        }


class LiteralField(serializers.Field):

    default_error_messages = {"invalid": _("Type must be one of string, boolean, number")}

    def to_internal_value(self, data):
        if not isinstance(data, (str, int, float, bool)):
            self.fail("invalid")
        return data

    def to_representation(self, value):
        return value


class VariableNodeSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=128, label=_("变量名称"))
    type = serializers.ChoiceField(choices=VariableType.get_member_value__alias_map(), label=_("变量类型"))
    _required = serializers.BooleanField(required=False, label=_("是否为必填参数"))
    properties = serializers.DictField(required=False, label=_("多子变量"))
    items = serializers.DictField(required=False, label=_("子变量"))
    default = LiteralField(required=False, label=_("默认值"))
    # 一般来说，定义的变量嵌套在 5 层内就可以满足使用场景，此处强制限制，防止恶意攻击导致堆栈爆炸
    depth = serializers.IntegerField(label=_("嵌套深度"), max_value=5)

    @classmethod
    def parse_default(cls, default_value: Union[str, bool, int, float], variable_type: str):
        """
        解析默认值
        :param default_value: 默认值
        :param variable_type: 变量类型
        :return:
        """
        if variable_type == VariableType.BOOLEAN.value:
            if default_value in serializers.BooleanField.TRUE_VALUES:
                return True
            elif default_value in serializers.BooleanField.FALSE_VALUES:
                return False
            else:
                return bool(default_value)
        elif variable_type == VariableType.STRING.value:
            return str(variable_type)
        elif variable_type == VariableType.NUMBER.value:
            # 数据原本就是 number 类型，直接返回
            if isinstance(default_value, (int, float)):
                return default_value
            elif isinstance(default_value, bool):
                return int(default_value)
        try:
            # 尝试将字面量转为浮点数
            return float(default_value)
        except ValueError:
            raise ValidationError(_("Failed to parse '{default_value}' as number".format(default_value=default_value)))

    def validate(self, attrs):
        if attrs["type"] == VariableType.OBJECT.value:
            attrs.pop("items", None)
            attrs["properties"] = attrs.get("properties", {})
        elif attrs["type"] == VariableType.ARRAY.value:
            attrs.pop("properties", None)
            attrs["items"] = attrs.get("items", {})
            if not attrs["items"]:
                raise ValidationError(_("items cannot be {}"))

        # 列表和字典不支持默认值
        if attrs["type"] in [VariableType.ARRAY, VariableType.OBJECT]:
            attrs.pop("default", None)

        # 根据 type 对字面量进行类型转换
        if "default" in attrs:
            attrs["default"] = self.parse_default(default_value=attrs["default"], variable_type=attrs["type"])

        return attrs


def list_package_infos(file_path: str) -> List[Dict[str, Any]]:
    """
    :param file_path: 插件包所在路径
    解析`self.file_path`下插件，获取包信息字典列表
    :return: [
        {
            # 存放插件的临时目录
            "plugin_tmp_dir": "/tmp/12134/",
            # 插件包的相对路径
            "pkg_relative_path": "plugins_linux_x86_64/package_name"
            # 插件包的绝对路径
            "pkg_absolute_path": "/tmp/12134/plugins_linux_x86_64/package_name",
            # 插件所需操作系统
            "package_os": "linux",
            # 支持cpu位数
            "cpu_arch": "x86_64",
            # 是否为自定义插件
            "is_external": "False"
        },
        ...
    ]
    """
    storage = get_storage()
    if not storage.exists(name=file_path):
        raise exceptions.PluginParseError(_("插件不存在: file_path -> {file_path}").format(file_path=file_path))

    # 解压压缩文件
    tmp_dir = files.mk_and_return_tmpdir()
    with storage.open(name=file_path, mode="rb") as tf_from_storage:
        with tarfile.open(fileobj=tf_from_storage) as tf:
            # 检查是否存在可疑内容
            for file_info in tf.getmembers():
                if file_info.name.startswith("/") or "../" in file_info.name:
                    logger.error(
                        "file-> {file_path} contains member-> {name} try to escape!".format(
                            file_path=file_path, name=file_info.name
                        )
                    )
                    raise exceptions.PluginParseError(_("文件包含非法路径成员 -> {name}，请检查").format(name=file_info.name))
            logger.info(
                "file-> {file_path} extract to path -> {tmp_dir} success.".format(file_path=file_path, tmp_dir=tmp_dir)
            )
            tf.extractall(path=tmp_dir)

    package_infos = []

    # 遍历第一层的内容，获取操作系统和cpu架构信息，eg：external(可无，有表示自定义插件)_plugins_linux_x86_64
    for first_plugin_dir_name in os.listdir(tmp_dir):
        # 通过正则提取出插件（plugin）目录名中的插件信息
        re_match = constants.PACKAGE_PATH_RE.match(first_plugin_dir_name)
        if re_match is None:
            logger.info(
                "pkg_dir_name -> {pkg_dir_name} is not match re, jump it.".format(pkg_dir_name=first_plugin_dir_name)
            )
            continue

        # 将文件名解析为插件信息字典
        plugin_info_dict = re_match.groupdict()
        current_os = plugin_info_dict["os"]
        cpu_arch = plugin_info_dict["cpu_arch"]
        logger.info(
            "pkg_dir_name -> {pkg_dir_name} is match for os -> {os}, cpu -> {cpu_arch}".format(
                pkg_dir_name=first_plugin_dir_name, os=current_os, cpu_arch=cpu_arch
            )
        )

        first_level_plugin_path = os.path.join(tmp_dir, first_plugin_dir_name)
        # 遍历第二层的内容，获取包名, eg：plugins_linux_x86_64/package_name
        for second_package_dir_name in os.listdir(first_level_plugin_path):
            # 拼接获取包路径
            second_level_package_dir_path = os.path.join(first_level_plugin_path, second_package_dir_name)
            if not os.path.isdir(second_level_package_dir_path):
                logger.info("found file path -> {path} jump it".format(path=second_level_package_dir_path))
                continue

            package_infos.append(
                {
                    "plugin_tmp_dir": tmp_dir,
                    "pkg_relative_path": os.path.join(first_plugin_dir_name, second_package_dir_name),
                    "pkg_absolute_path": second_level_package_dir_path,
                    "package_os": current_os,
                    "cpu_arch": cpu_arch,
                    "is_external": plugin_info_dict["is_external"] is not None,
                }
            )

    return package_infos


def parse_package(
    pkg_absolute_path: str, package_os: str, cpu_arch: str, is_update: bool, need_detail: bool = False
) -> Dict[str, Any]:
    """
    解析插件包
    :param pkg_absolute_path: 插件包所在的绝对路径
    :param package_os: 操作系统类型，lower
    :param cpu_arch: cpu架构
    :param is_update: 是否校验更新
    :param need_detail: 是否需要解析详情，用于create_package_record创建插件包记录
    :return:
    """
    pkg_parse_info = {
        "result": True,
        "message": "",
        "pkg_name": None,
        "project": None,
        "version": None,
        "category": None,
        "description": None,
        "config_templates": [],
        "os": package_os,
        "cpu_arch": cpu_arch,
    }

    # 判断是否存在project.yaml文件
    project_yaml_file_path = os.path.join(pkg_absolute_path, "project.yaml")
    if not os.path.exists(project_yaml_file_path):
        logger.warning(
            "try to pack path-> {pkg_absolute_path} but not [project.yaml] file under file path".format(
                pkg_absolute_path=pkg_absolute_path
            )
        )
        pkg_parse_info["result"] = False
        pkg_parse_info["message"] = _("缺少project.yaml文件")
        return pkg_parse_info

    # 解析project.yaml文件(版本，插件名等信息)
    try:
        with open(project_yaml_file_path, "r", encoding="utf-8") as project_file:
            yaml_config = yaml.safe_load(project_file)
            if not isinstance(yaml_config, dict):
                raise yaml.YAMLError
    except (IOError, yaml.YAMLError):
        logger.warning(
            "failed to parse or read project_yaml -> {project_yaml_file_path}, for -> {err_msg}".format(
                project_yaml_file_path=project_yaml_file_path, err_msg=traceback.format_exc()
            )
        )
        pkg_parse_info["result"] = False
        pkg_parse_info["message"] = _("project.yaml文件解析读取失败")
        return pkg_parse_info

    try:
        # 解析版本号转为字符串，防止x.x情况被解析为浮点型，同时便于后续写入及比较
        yaml_config["version"] = str(yaml_config["version"])

        pkg_parse_info.update(
            {
                "pkg_name": "{project}-{version}.tgz".format(
                    project=yaml_config["name"], version=yaml_config["version"]
                ),
                "project": yaml_config["name"],
                "version": yaml_config["version"],
                "category": yaml_config["category"],
                "description": yaml_config.get("description", ""),
            }
        )

        # 无法解析 project.control 成为 python 字典类型
        if not isinstance(yaml_config.get("control", {}), dict):
            raise TypeError("can't not convert control in project.yaml to python dict.")

    except (KeyError, TypeError):
        logger.warning(
            "failed to get key info from project.yaml -> {project_yaml_file_path}, for -> {err_msg}".format(
                project_yaml_file_path=project_yaml_file_path, err_msg=traceback.format_exc()
            )
        )
        pkg_parse_info["result"] = False
        pkg_parse_info["message"] = _("project.yaml 文件信息缺失")
        return pkg_parse_info

    # 插件包版本更新标志，用于描述插件包是否为下述的「更新插件版本」情况
    update_flag = False
    # 插件包最新版本预先初始化为当前解析插件包的版本
    package_release_version = yaml_config["version"]

    # 判断插件类型是否符合预取
    if pkg_parse_info["category"] not in constants.CATEGORY_TUPLE:
        logger.warning(
            "project -> {project}, version -> {version}: update(or create) with category-> {category} "
            "which is not acceptable, nothing will do.".format(
                project=pkg_parse_info["project"],
                version=pkg_parse_info["version"],
                category=pkg_parse_info["category"],
            )
        )
        pkg_parse_info["result"] = False
        pkg_parse_info["message"] = _("project.yaml 中 category 配置异常，请确认后重试")
        return pkg_parse_info

    packages_queryset = models.Packages.objects.filter(project=yaml_config["name"], os=package_os, cpu_arch=cpu_arch)

    # 判断是否为新增插件
    if not packages_queryset.exists():
        logger.info(
            "project-> {project}, os-> {os}, cpu_arch-> {cpu_arch} is not exists, "
            "this operations will create new package".format(
                project=pkg_parse_info["project"], os=package_os, cpu_arch=cpu_arch
            )
        )
        pkg_parse_info["message"] = _("新增插件")

    # 判断是否已发布过该插件版本
    elif packages_queryset.filter(version=yaml_config["version"], is_release_version=True, is_ready=True).exists():
        logger.warning(
            "project -> {project}, version-> {version}, os-> {os}, cpu_arch -> {cpu_arch} is release, "
            "will overwrite it".format(
                project=pkg_parse_info["project"], version=pkg_parse_info["version"], os=package_os, cpu_arch=cpu_arch
            )
        )
        pkg_parse_info["message"] = _("已有版本插件更新")

    # 判断预导入插件版本同最新版本的关系
    else:
        # 取出最新版本号
        package_release_version = sorted(
            packages_queryset.values_list("version", flat=True), key=lambda v: version.parse(v)
        )[-1]

        if version.parse(package_release_version) > version.parse(yaml_config["version"]):
            pkg_parse_info["message"] = _("低版本插件仅支持导入")
        else:
            update_flag = True
            pkg_parse_info["message"] = _("更新插件版本")

    logger.info(
        "project -> {project} validate version: is_update -> {is_update}, update_flag -> {update_flag}".format(
            project=yaml_config["name"], is_update=is_update, update_flag=update_flag
        )
    )

    # 需要校验版本更新，但该插件没有升级
    if is_update and not update_flag:
        raise exceptions.PackageVersionValidationError(
            _("文件路径 -> {pkg_absolute_path} 所在包解析版本为 -> {version}, 最新版本 -> {release_version}, 更新校验失败").format(
                pkg_absolute_path=pkg_absolute_path,
                version=pkg_parse_info["version"],
                release_version=package_release_version,
            )
        )

    # 解析配置模板
    config_templates = yaml_config.get("config_templates", [])
    for config_template in config_templates:
        # 配置模板所在的相对路径
        source_path = config_template["source_path"]
        # 配置模板所在的绝对路径
        template_file_path = os.path.join(pkg_absolute_path, source_path)
        if not os.path.exists(template_file_path):
            logger.warning(
                "project.yaml need to import file -> {source_path} but is not exists, nothing will do.".format(
                    source_path=config_template["source_path"]
                )
            )
            pkg_parse_info["result"] = False
            pkg_parse_info["message"] = _("找不到需要导入的配置模板文件 -> {source_path}").format(source_path=source_path)
            return pkg_parse_info

        config_template_variables: Optional[Dict[str, Any]] = None
        try:
            config_template_variables = validate_config_variables(config_template.get("variables"))
            if config_template_variables is not None:
                # 标识配置变量来源
                config_template_variables["from_project_yaml"] = True
        except ValidationError as err:
            pkg_parse_info["result"] = False
            pkg_parse_info["message"] = _("配置模板变量「{cfg_tmpl_name} -> variables」校验失败：{err_msg}").format(
                cfg_tmpl_name=config_template["name"], err_msg=err
            )
        pkg_parse_info["config_templates"].append(
            {
                "name": config_template["name"],
                "is_main": config_template.get("is_main_config", False),
                "source_path": source_path,
                "file_path": config_template["file_path"],
                "variables": config_template_variables,
                "format": config_template["format"],
                # 解析版本号转为字符串，防止x.x情况被解析为浮点型，同时便于后续写入及比较
                "version": str(config_template["version"]),
                "plugin_version": str(config_template["plugin_version"]),
            }
        )

    if need_detail:
        pkg_parse_info["yaml_config"] = yaml_config
    return pkg_parse_info


def fetch_latest_config_templates(
    plugin_name,
    os_type: str,
    cpu_arch: str,
    config_templates: List[Dict[str, Any]],
    plugin_version: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    如果存在多个版本的同名配置，仅展示最新版本，且仅展示指定平台的配置，缺省为当前平台插件最新版本
    优先级： plugin_name > currect platfrom last version > other platform with plugin_version
    若指定了插件版本，则优先取指定版本的配置
    若未匹配指定版本，再从通配(*)的版本中取最新版本
    若存在同名不同平台多版本，只选择指定平台
    :param plugin_name:  插件名称
    :param os_type: 操作系统
    :param cpu_arch: CPU
    :param config_templates: 配置模板列表
    :param plugin_version: 指定插件版本号
    """
    config_tmpls_gby_name: Dict[str, List] = defaultdict(list)
    platform_id__version_and_main_map: Dict[str, Dict[str, Union[str, bool]]] = defaultdict(dict)
    platform_name__ids_map: Dict[str, List[int]] = defaultdict(list)
    platform_name__id_and_version_map: Dict[str, Dict[str, Any]] = defaultdict(dict)

    for config_tmpl in config_templates:
        config_tmpls_gby_name[config_tmpl["name"]].append(config_tmpl)

    platform_config_template_objs: Set[Union[str, int]] = set(
        models.PluginConfigTemplate.objects.filter(
            plugin_name=plugin_name,
            name__in=config_tmpls_gby_name.keys(),
            os=os_type,
            cpu_arch=cpu_arch,
        ).values_list("name", "id", "version", "is_main")
    )

    if platform_config_template_objs:
        for (tmpl_name, tmpl_id, tmpl_version, tmpl_is_main) in platform_config_template_objs:
            platform_id__version_and_main_map[tmpl_id]["version"] = tmpl_version
            platform_name__ids_map[tmpl_name].append(tmpl_id)
            platform_id__version_and_main_map[tmpl_id]["is_main"] = tmpl_is_main

        for tmpl_name in platform_name__ids_map.keys():
            platform_name__id_and_version_map[tmpl_name]["id"] = sorted(platform_name__ids_map[tmpl_name])[-1]
            platform_name__id_and_version_map[tmpl_name]["version"] = platform_id__version_and_main_map[
                platform_name__id_and_version_map[tmpl_name]["id"]
            ]["version"]

    latest_config_templates: List[Dict[str, Any]] = []
    for config_tmpl_name, config_tmpls_with_the_same_name in config_tmpls_gby_name.items():
        same_name_tmpl_map: Dict[str, Dict[str, str]] = {}
        for tmpl in config_tmpls_with_the_same_name:
            same_name_tmpl_map[tmpl["version"]] = tmpl

        #  选取对应平台模板名中的指定版本号或者是最大版本号
        same_name_tmp_versions: KeysView[str] = same_name_tmpl_map.keys()
        if same_name_tmp_versions:
            if plugin_version in same_name_tmp_versions:
                latest_config_template = same_name_tmpl_map[plugin_version]
            else:
                latest_config_template = same_name_tmpl_map[
                    sorted(same_name_tmp_versions, key=lambda v: version.parse(v))[-1]
                ]

            latest_config_templates.append(latest_config_template)

    latest_config_template_names: Set[str] = {tmpl["name"] for tmpl in latest_config_templates}
    # 对于传入模板列表中不存在相符插件包平台配置模板时，为这个配置项补充当前平台下插件的最新版本
    for missed_config_template_name in config_tmpls_gby_name.keys():
        if missed_config_template_name not in latest_config_template_names and platform_config_template_objs:
            try:
                latest_config_templates.append(
                    {
                        "id": platform_name__id_and_version_map[missed_config_template_name]["id"],
                        "version": platform_name__id_and_version_map[missed_config_template_name]["version"],
                        "os": os_type,
                        "cpu_arch": cpu_arch,
                        "name": missed_config_template_name,
                        "is_main": platform_id__version_and_main_map[
                            platform_name__id_and_version_map[missed_config_template_name]["id"]
                        ]["is_main"],
                    }
                )
            except KeyError:
                logger.error(
                    _(
                        f"plugin config template -> {missed_config_template_name} with "
                        f"platform -> {os_type}-{cpu_arch} is not exist "
                    )
                )

    return latest_config_templates


def fill_latest_config_tmpls_to_packages(packages: List[Dict[str, Any]]) -> None:
    """
    填充最新配置文件到插件包信息列表
    :param packages: 插件包列表
    :return:
    """
    plugin_names: Set[str] = set()
    os_types: Set[str] = set()
    cpu_arches: Set[str] = set()

    for package in packages:
        plugin_names.add(package["project"])
        os_types.add(package["os"])
        cpu_arches.add(package["cpu_arch"])

    # 获取插件包关联的配置模板
    config_tmpls = list(
        models.PluginConfigTemplate.objects.filter(
            plugin_name__in=plugin_names, os__in=os_types, cpu_arch__in=cpu_arches
        ).values("id", "name", "version", "is_main", "plugin_version", "cpu_arch", "os", "plugin_name")
    )

    # 以 plugin_name & os & cpu_arch & plugin_version 作为唯一标识，聚合配置模板
    config_tmpls_gby_pkg_key: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for config_tmpl in config_tmpls:
        pkg_key = "_".join(
            [config_tmpl["plugin_name"], config_tmpl["os"], config_tmpl["cpu_arch"], config_tmpl["plugin_version"]]
        )
        config_tmpls_gby_pkg_key[pkg_key].append(
            {
                "id": config_tmpl["id"],
                "version": config_tmpl["version"],
                "os": config_tmpl["os"],
                "cpu_arch": config_tmpl["cpu_arch"],
                "name": config_tmpl["name"],
                "is_main": config_tmpl["is_main"],
            }
        )

    for package in packages:
        # 配置模板 = 通用版本配置模板 + 该版本的配置模板
        pkg_key_prefix = f"{package['project']}_{package['os']}_{package['cpu_arch']}_"
        config_templates = (
            config_tmpls_gby_pkg_key[f"{pkg_key_prefix}{package['version']}"]
            + config_tmpls_gby_pkg_key[f"{pkg_key_prefix}*"]
        )
        # 筛选最新配置
        package["config_templates"] = fetch_latest_config_templates(
            plugin_name=package["project"],
            os_type=package["os"],
            cpu_arch=package["cpu_arch"],
            config_templates=config_templates,
        )


def validate_config_variables(variables_root: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    校验配置变量
    :param variables_root: 配置变量根节点
    :return: 返回通过校验的配置变量
    """

    def _validate_node(_node: Dict[str, Any]) -> Dict[str, Any]:
        _node_serializer = VariableNodeSerializer(data=_node)
        _node_serializer.is_valid(raise_exception=True)
        return _node_serializer.validated_data

    if not variables_root:
        return variables_root

    variables_root["depth"] = 1
    # 为变量节点补充 title，该值仅在 items 中必填，保证节点结构统一
    variables_root["title"] = variables_root.get("title", "variables")

    stack = [variables_root]
    # 定义一个通过校验的配置根节点及栈结构，同步 stack 进行遍历写入
    validated_variables_root = {}
    validated_stack = [validated_variables_root]

    # 空间换时间，迭代模拟递归
    while stack:
        # 校验节点
        node = _validate_node(stack.pop())
        # depth 仅辅助校验，最终数据不需要该值，弹出并记录当前的深度
        depth = node.pop("depth") + 1
        # 与 stack 保持相同的遍历顺序，保证构建变量树与给定的一致
        validated_node = validated_stack.pop()
        validated_node.update(node)

        if node["type"] == VariableType.ARRAY.value:
            node["items"]["depth"] = depth
            stack.append(node["items"])
            # 初始化 items 节点，并将初始化节点添加到 validated_stack
            validated_node["items"] = {}
            validated_stack.append(validated_node["items"])
        elif node["type"] == VariableType.OBJECT.value:
            # 初始化 properties
            validated_node["properties"] = {}
            for title, property_node in node["properties"].items():
                property_node["title"] = title
                property_node["depth"] = depth
                stack.append(property_node)
                # 初始化 properties 子节点
                validated_node["properties"][title] = {}
                validated_stack.append(validated_node["properties"][title])
    return validated_variables_root


def create_package_records(
    file_path: str,
    file_name: str,
    is_release: bool,
    creator: Optional[str] = None,
    select_pkg_relative_paths: Optional[List[str]] = None,
    is_template_load: bool = False,
) -> List[models.Packages]:
    """
    解析上传插件，拆分为插件包并保存记录
    :param file_path: 上传插件所在路径
    :param file_name: 上传插件名称
    :param is_release: 是否正式发布
    :param creator: 操作人
    :param select_pkg_relative_paths: 指定注册插件包的相对路径列表
    :param is_template_load: 是否需要读取配置文件
    :return: [package_object, ...]
    :return:
    """
    pkg_record_objs = []
    package_infos = list_package_infos(file_path=file_path)

    with transaction.atomic():
        for package_info in package_infos:
            if not (
                select_pkg_relative_paths is None or package_info["pkg_relative_path"] in select_pkg_relative_paths
            ):
                logger.info("path -> {path} not selected, jump it".format(path=package_info["pkg_relative_path"]))
                continue
            pkg_record_obj = create_pkg_record(
                pkg_absolute_path=package_info["pkg_absolute_path"],
                package_os=package_info["package_os"],
                cpu_arch=package_info["cpu_arch"],
                is_release=is_release,
                creator=creator,
                is_external=package_info["is_external"],
                is_template_load=is_template_load,
            )

            logger.info(
                "package path -> {path} add to pkg record-> {record_id} success.".format(
                    path=package_info["pkg_relative_path"], record_id=pkg_record_obj.id
                )
            )
            pkg_record_objs.append(pkg_record_obj)

    logger.info("plugin -> {file_name} create pkg record all done.".format(file_name=file_name))

    # 清理临时解压目录
    plugin_tmp_dirs = set([package_info["plugin_tmp_dir"] for package_info in package_infos])
    for plugin_tmp_dir in plugin_tmp_dirs:
        shutil.rmtree(plugin_tmp_dir)

    return pkg_record_objs


@transaction.atomic
def create_pkg_record(
    pkg_absolute_path: str,
    package_os: str,
    cpu_arch: str,
    is_external: bool,
    creator: Optional[str] = None,
    is_release: bool = True,
    is_template_load: bool = False,
) -> models.Packages:
    """
    给定一个插件的路径，分析路径下的project.yaml，生成压缩包到nginx(多台)目录下
    ！！！注意：该任务可能会导致长期的卡顿，请务必注意不要再wsgi等单线程环境中调用！！！
    :param pkg_absolute_path: 需要进行打包的插件包临时解压路径, 例如，plugin_a 路径，路径下放置了插件包各个文件
                     ⚠️ 该路径应为本地临时路径，插件包已从存储源下载到该路径
    :param package_os: 插件包支持的操作系统类型
    :param cpu_arch: 插件支持的CPU架构
    :param is_external: 是否第三方插件
    :param creator: 操作人
    :param is_release: 是否发布的版本
    :param is_template_load: 是否需要读取插件包中的配置模板
    :return: True | raise Exception
    """
    pkg_parse_info = parse_package(
        pkg_absolute_path=pkg_absolute_path, package_os=package_os, cpu_arch=cpu_arch, is_update=False, need_detail=True
    )
    logger.info(f"pkg_absolute_path -> {pkg_absolute_path}, pkg_parse_info -> {pkg_parse_info}")
    if not pkg_parse_info["result"]:
        raise exceptions.PluginParseError(pkg_parse_info.get("message"))

    project = pkg_parse_info["project"]
    yaml_config = pkg_parse_info["yaml_config"]

    # 判断是否已经由插件描述信息，需要写入
    desc, created = models.GsePluginDesc.objects.update_or_create(
        name=project,
        defaults=dict(
            description=yaml_config.get("description", ""),
            scenario=yaml_config.get("scenario", ""),
            description_en=yaml_config.get("description_en", ""),
            scenario_en=yaml_config.get("scenario_en", ""),
            category=yaml_config["category"],
            launch_node=yaml_config.get("launch_node", "all"),
            config_file=yaml_config.get("config_file", ""),
            config_format=yaml_config.get("config_format", ""),
            use_db=bool(yaml_config.get("use_db", False)),
            auto_launch=bool(yaml_config.get("auto_launch", False)),
            is_binary=bool(yaml_config.get("is_binary", True)),
            node_manage_control=yaml_config.get("node_manage_control", ""),
        ),
    )
    if created:
        logger.info(
            "plugin_desc_id -> {plugin_desc_id} for project -> {project} is created".format(
                plugin_desc_id=desc.id, project=project
            )
        )

    # 写入插件包信息
    packages_queryset = models.Packages.objects.filter(
        project=project,
        version=pkg_parse_info["version"],
        os=package_os,
        cpu_arch=cpu_arch,
        pkg_name=pkg_parse_info["pkg_name"],
    )
    if not packages_queryset.exists():
        # 如果之前未有未发布的插件包信息，需要新建
        pkg_record = models.Packages.objects.create(
            pkg_name=pkg_parse_info["pkg_name"],
            version=pkg_parse_info["version"],
            module="gse_plugin",
            creator=creator or settings.SYSTEM_USE_API_ACCOUNT,
            project=project,
            pkg_size=0,
            pkg_path="",
            md5="",
            pkg_mtime="",
            pkg_ctime="",
            location="",
            os=package_os,
            cpu_arch=cpu_arch,
            is_release_version=is_release,
            is_ready=False,
        )
    else:
        # 否则，更新已有的记录即可
        pkg_record = packages_queryset.first()

    # 判断是否需要更新配置文件模板
    if is_template_load:
        for config_template_info in pkg_parse_info["config_templates"]:

            template_file_path = os.path.join(pkg_absolute_path, config_template_info["source_path"])

            with open(template_file_path) as template_fs:
                config_template_content = template_fs.read()

            config_template_obj, __ = models.PluginConfigTemplate.objects.update_or_create(
                plugin_name=pkg_record.project,
                plugin_version=config_template_info["plugin_version"],
                name=config_template_info["name"],
                version=config_template_info["version"],
                is_main=config_template_info["is_main"],
                cpu_arch=cpu_arch,
                os=package_os,
                defaults=dict(
                    format=config_template_info["format"],
                    file_path=config_template_info["file_path"],
                    content=config_template_content,
                    variables=config_template_info.get("variables"),
                    is_release_version=is_release,
                    creator="system",
                    create_time=timezone.now(),
                    source_app_code="bk_nodeman",
                ),
            )

            logger.info(
                "template -> {name} template_version -> {template_version} is create for plugin -> {project} "
                "version -> {version}".format(
                    name=config_template_obj.name,
                    template_version=config_template_obj.version,
                    project=pkg_record.project,
                    version=pkg_record.version,
                )
            )

            # 配置文件已写入DB，从插件包中移除
            os.remove(template_file_path)

    proc_control, __ = models.ProcControl.objects.get_or_create(
        plugin_package_id=pkg_record.id, defaults=dict(module="gse_plugin", project=pkg_parse_info["project"])
    )

    # 更新插件包相关路径
    path_info = env.get_gse_env_path(
        pkg_parse_info["project"], is_windows=(package_os == constants.OsType.WINDOWS.lower())
    )
    proc_control.install_path = path_info["install_path"]
    proc_control.log_path = path_info["log_path"]
    proc_control.data_path = path_info["data_path"]
    proc_control.pid_path = path_info["pid_path"]

    # 更新插件包操作命令
    control_info = yaml_config.get("control", {})
    proc_control.start_cmd = control_info.get("start", "")
    proc_control.stop_cmd = control_info.get("stop", "")
    proc_control.restart_cmd = control_info.get("restart", "")
    proc_control.reload_cmd = control_info.get("reload", "")
    proc_control.kill_cmd = control_info.get("kill", "")
    proc_control.version_cmd = control_info.get("version", "")
    proc_control.health_cmd = control_info.get("health_check", "")
    proc_control.debug_cmd = control_info.get("debug", "")

    proc_control.os = package_os

    # 更新插件二进制配置信息，如果不存在默认为空
    proc_control.process_name = yaml_config.get("process_name")

    # 更新是否需要托管
    proc_control.need_delegate = yaml_config.get("need_delegate", True)

    # 更新端口范围信息
    port_range = yaml_config.get("port_range", "")

    # 校验端口范围合法性
    port_range_list = models.ProcControl.parse_port_range(port_range)
    if port_range_list:
        proc_control.port_range = port_range

    proc_control.save()

    logger.info(
        "process control -> {id} for plugin -> {project} version -> {version} os -> {os} is created.".format(
            id=proc_control.id, project=project, version=pkg_record.version, os=package_os
        )
    )

    # 打包插件包，先在本地打包为tar
    package_tmp_path = os.path.join(constants.TMP_DIR, f"{project}-{pkg_record.version}-{package_os}-{cpu_arch}.tgz")
    with tarfile.open(package_tmp_path, "w:gz") as tf:
        tf.add(
            pkg_absolute_path,
            # 判断是否第三方插件的路径
            arcname=f"{constants.PluginChildDir.EXTERNAL.value}/{project}"
            if is_external
            else f"{constants.PluginChildDir.OFFICIAL.value}/",
        )
        logger.info(
            "project -> {project} version -> {version} now is pack to package_tmp_path -> {package_tmp_path}".format(
                project=project, version=pkg_record.version, package_tmp_path=package_tmp_path
            )
        )

    # 将插件包上传到存储系统
    package_target_path = os.path.join(settings.DOWNLOAD_PATH, pkg_record.os, pkg_record.cpu_arch, pkg_record.pkg_name)
    with open(package_tmp_path, mode="rb") as tf:
        # 采用同名覆盖策略，保证同版本插件包仅保存一份
        storage_path = get_storage(file_overwrite=True).save(package_target_path, tf)
        if storage_path != package_target_path:
            logger.error(
                "package save error, except save to -> {package_target_path}, but -> {storage_path}".format(
                    package_target_path=package_target_path, storage_path=storage_path
                )
            )
            raise exceptions.CreatePackageRecordError(
                _("插件包保存错误，期望保存到 -> {package_target_path}, 实际保存到 -> {storage_path}").format(
                    package_target_path=package_target_path, storage_path=storage_path
                )
            )

    # 补充插件包的文件存储信息
    pkg_record.is_ready = True
    pkg_record.pkg_mtime = str(timezone.now())
    # pkg_ctime 仅记录该插件包信息的创建时间
    pkg_record.pkg_ctime = pkg_record.pkg_ctime or pkg_record.pkg_mtime
    pkg_record.pkg_size = os.path.getsize(package_tmp_path)
    pkg_record.pkg_path = os.path.dirname(package_target_path)
    pkg_record.md5 = files.md5sum(name=package_tmp_path)
    # 这里没有加上包名，是因为原本脚本(bkee/bkce)中就没有加上，为了防止已有逻辑异常，保持一致
    # 后面有哪位发现这里不适用了，可以一并修改
    pkg_record.location = f"http://{os.getenv('LAN_IP')}/download/{package_os}/{cpu_arch}"

    pkg_record.save()

    logger.info(
        "package -> {pkg_name}, package_target_path -> {package_target_path} now is ready to use".format(
            pkg_name=pkg_record.pkg_name, package_target_path=package_target_path
        )
    )

    # 清理临时文件
    os.remove(package_tmp_path)
    logger.info("clean temp tgz file -> {temp_file_path} done.".format(temp_file_path=package_tmp_path))

    return pkg_record


def add_default_platform(params: Dict) -> Dict:
    if "os" not in params:
        params.update({"os": constants.PluginOsType.linux})
    if "cpu_arch" not in params:
        params.update({"cpu_arch": constants.CpuType.x86_64})
    return params
