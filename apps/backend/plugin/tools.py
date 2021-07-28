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
import logging
import os
import traceback
from collections import defaultdict
from typing import Any, Dict, List

import yaml
from django.utils.translation import ugettext_lazy as _
from packaging import version

from apps.backend.exceptions import PackageVersionValidationError
from apps.node_man import constants, models

logger = logging.getLogger("app")


def parse_package(package_info: dict, is_update: bool, project: str) -> dict:
    package_parse_detail = {
        "result": True,
        "message": "",
        "pkg_name": None,
        "pkg_abs_path": package_info["pkg_abs_path"],
        "project": None,
        "version": None,
        "category": None,
        "config_templates": [],
        "os": package_info["package_os"],
        "cpu_arch": package_info["cpu_arch"],
        "description": None,
    }
    update_flag = False

    # 1. 判断是否存在project.yaml文件
    project_file_path = os.path.join(package_info["dir_path"], "project.yaml")
    if not os.path.exists(project_file_path):
        logger.warning(
            "try to pack path->[%s] but is not [project.yaml] file under file path" % package_info["dir_path"]
        )
        package_parse_detail["result"] = False
        package_parse_detail["message"] = _("缺少project.yaml文件")
        return package_parse_detail

    # 2. 解析project.yaml文件(版本，插件名等信息)
    try:
        with open(project_file_path, "r", encoding="utf-8") as project_file:
            yaml_config = yaml.safe_load(project_file)
            if not isinstance(yaml_config, dict):
                raise yaml.YAMLError
    except (IOError, yaml.YAMLError):
        logger.warning(
            "failed to parse or read project_yaml->[{}] for->[{}]".format(project_file_path, traceback.format_exc())
        )
        package_parse_detail["result"] = False
        package_parse_detail["message"] = _("project.yaml文件解析读取失败")
        return package_parse_detail

    try:
        # 解析版本号转为字符串，防止x.x情况被解析为浮点型，同时便于后续写入及比较
        yaml_config["version"] = str(yaml_config["version"])

        package_parse_detail.update(
            {
                "pkg_name": "{}-{}.tgz".format(yaml_config["name"], yaml_config["version"]),
                "project": yaml_config["name"],
                "version": yaml_config["version"],
                "category": yaml_config["category"],
                "description": yaml_config.get("description", ""),
            }
        )
    except KeyError:
        logger.warning(
            "failed to get key info from project.yaml->[%s] for->[%s] maybe config file error?"
            % (project_file_path, traceback.format_exc())
        )
        package_parse_detail["result"] = False
        package_parse_detail["message"] = _("project.yaml文件信息缺失")
        return package_parse_detail

    package_release_version = yaml_config["version"]

    # 更新插件名称对应不上
    if is_update and yaml_config["name"] != project:
        raise PackageVersionValidationError(
            _("期望更新的插件为[{project}]，实际上传的插件为[{update_plugin_name}]").format(
                project=project, update_plugin_name=yaml_config["name"]
            )
        )

    # 3. 判断插件类型是否符合预取
    if yaml_config["category"] not in constants.CATEGORY_TUPLE:
        logger.warning(
            "project->[%s] version->[%s] update(or create) with category->[%s] which is not acceptable, "
            "nothing will do." % (yaml_config["name"], yaml_config["version"], yaml_config["category"])
        )
        package_parse_detail["result"] = False
        package_parse_detail["message"] = _("project.yaml中category配置异常，请确认后重试")
        return package_parse_detail
    package_parse_detail["category"] = constants.CATEGORY_DICT[yaml_config["category"]]

    packages_queryset = models.Packages.objects.filter(
        project=yaml_config["name"], os=package_info["package_os"], cpu_arch=package_info["cpu_arch"]
    )
    # 4. 判断是否为新增插件
    if not packages_queryset.exists():
        logger.info(
            "project->[%s] os->[%s] cpu_arch->[%s] is not exists, this operations will create new package"
            % (yaml_config["name"], package_info["package_os"], package_info["cpu_arch"])
        )
        package_parse_detail["message"] = _("新增插件")

    # 5. 判断以前是否已发布过该插件版本
    elif packages_queryset.filter(version=yaml_config["version"], is_release_version=True, is_ready=True).exists():
        logger.warning(
            "project->[%s] version->[%s] os->[%s] cpu_arch->[%s] is release, no more operations is "
            "allowed."
            % (yaml_config["name"], yaml_config["version"], package_info["package_os"], package_info["cpu_arch"])
        )
        package_parse_detail["message"] = _("已有版本插件更新")

    # 6. 判断预导入插件版本同最新版本的关系
    else:
        # 取出最新版本号
        package_release_version = sorted(
            packages_queryset.values_list("version", flat=True), key=lambda v: version.parse(v)
        )[-1]

        if version.parse(package_release_version) > version.parse(yaml_config["version"]):
            package_parse_detail["message"] = _("低版本插件仅支持导入")
        else:
            update_flag = True
            package_parse_detail["message"] = _("更新插件版本")

    logger.info(
        "project->[{project}] validate version: is_update->[{is_update}], update_flag->[{update_flag}]".format(
            project=yaml_config["name"], is_update=is_update, update_flag=update_flag
        )
    )

    # 需要校验版本更新，但该插件没有升级
    if is_update and not update_flag:
        raise PackageVersionValidationError(
            _("文件路径[{pkg_abs_path}]所在包解析版本为[{parse_version}], 最新版本为[{release_version}], 更新校验失败").format(
                pkg_abs_path=package_parse_detail["pkg_abs_path"],
                parse_version=package_parse_detail["version"],
                release_version=package_release_version,
            )
        )

    # 7. 解析配置模板
    config_templates = yaml_config.get("config_templates", [])
    for config_template in config_templates:
        source_path = config_template["source_path"]
        template_file_path = os.path.join(package_info["dir_path"], source_path)
        if not os.path.exists(template_file_path):
            logger.warning(
                "project.yaml need to import file->[%s] but is not exists, nothing will do."
                % config_template["source_path"]
            )
            package_parse_detail["result"] = False
            package_parse_detail["message"] = _("找不到需要导入的配置模板文件[%s]") % source_path
            return package_parse_detail

        package_parse_detail["config_templates"].append(
            {
                "name": config_template["name"],
                # 解析版本号转为字符串，防止x.x情况被解析为浮点型，同时便于后续写入及比较
                "version": str(config_template["version"]),
                "is_main": config_template.get("is_main_config", False),
            }
        )
    return package_parse_detail


def fetch_latest_config_templates(config_templates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    config_tmpls_gby_name = defaultdict(list)
    for config_tmpl in config_templates:
        config_tmpls_gby_name[config_tmpl["name"]].append(config_tmpl)

    latest_config_templates = []
    for config_tmpl_name, config_tmpls_with_the_same_name in config_tmpls_gby_name.items():
        config_tmpls_order_by_version = sorted(
            config_tmpls_with_the_same_name, key=lambda tmpl: version.parse(tmpl["version"])
        )
        latest_config_templates.append(config_tmpls_order_by_version[-1])

    return latest_config_templates
