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

import re
import traceback
from itertools import groupby
from typing import Dict, List, Set, Union

import jinja2schema
from jinja2 import Environment, meta
from packaging import version

from apps.node_man import models
from common.log import logger


class PluginV2Tools:
    items_iter_block_pattern = re.compile(r"{%\s*for\s*\w+\s*,\s*\w+\s*in\s*.*%}\s*.*?\s*{%\s*endfor\s*%}", re.M)
    items_var_path_pattern = re.compile(r"([\w.]+).items\(\)")
    lower_var_path_pattern = re.compile(r"{{\s*[\w.]+\s*\|\s*lower\s*}}")
    lower_var_name_pattern = re.compile(r"{{\s*([\w.]+)\s*\|\s*lower\s*}}")

    @classmethod
    def shield_tpl_unparse_content(cls, config_template_content: str):
        shield_content = config_template_content

        for iter_content in cls.items_iter_block_pattern.findall(shield_content):
            var_path = cls.items_var_path_pattern.findall(iter_content)[0]
            var_name = var_path.split(".")[-1]
            shield_content = shield_content.replace(iter_content, f"{var_name}: {{ {var_path} }}")

        for lower_content in cls.lower_var_path_pattern.findall(shield_content):
            var_path = cls.lower_var_name_pattern.findall(lower_content)[0]
            shield_content = shield_content.replace(lower_content, f"{{ {var_path} }}")
        return shield_content

    @staticmethod
    def parse_tpl2var_json(shield_content):
        try:
            return jinja2schema.to_json_schema(jinja2schema.infer(shield_content))
        except Exception as e:
            logger.warning(
                "Parse config template failed[{error}: {detail}]".format(error=e, detail=traceback.format_exc())
            )
            env = Environment()
            undeclared_variables = meta.find_undeclared_variables(env.parse(shield_content))
            return {
                "type": "object",
                "properties": {var: {"title": var, "type": "any"} for var in undeclared_variables},
            }

    @staticmethod
    def simplify_var_json(var_json: dict):
        stack = [var_json]
        while stack:
            cur_node = stack.pop()
            if cur_node.pop("anyOf", None):
                cur_node["type"] = "any"

            required = cur_node.pop("required", [])

            if cur_node.get("type") == "object":
                for name, attrs in cur_node.get("properties", {}).items():
                    if name in required:
                        attrs["_required"] = True
                    stack.append(attrs)
            elif cur_node.get("type") == "array":
                if cur_node.get("items"):
                    stack.append(cur_node["items"])
        return var_json

    @classmethod
    def get_packages_node_numbers(cls, projects: List[str], keys: List[str]) -> Dict:
        """
        统计插件包部署节点数量
        :param projects: 插件唯一标识（名称）列表
        :param keys: 统计维度
        :return:
        """
        proc_list = list(
            models.ProcessStatus.objects.filter(
                name__in=projects,
                source_type=models.ProcessStatus.SourceType.DEFAULT,
                is_latest=True,
            ).values("bk_host_id", "name", "version")
        )

        # proc_list有重复的情况会在此步骤构建映射时自动去重
        proj_host_id_proc_map = {f"{proc['name']}_{proc['bk_host_id']}": proc for proc in proc_list}

        host_list = models.Host.objects.filter(bk_host_id__in={proc["bk_host_id"] for proc in proc_list}).values(
            "bk_host_id", "os_type", "cpu_arch"
        )

        proj_deploy_infos = []
        for host in host_list:
            host.update({"os": host["os_type"].lower()})
            proj_deploy_infos.extend(
                [
                    {**host, **proj_host_id_proc_map[f"{project}_{host['bk_host_id']}"], "project": project}
                    for project in projects
                    if f"{project}_{host['bk_host_id']}" in proj_host_id_proc_map
                ]
            )
        deploy_infos_group_by_keys = groupby(
            sorted(proj_deploy_infos, key=lambda x: tuple(x[key] for key in keys)),
            key=lambda x: "_".join([x[key] for key in keys]),
        )
        return {group_key: len(list(deploy_infos)) for group_key, deploy_infos in deploy_infos_group_by_keys}

    @classmethod
    def fill_nodes_number_to_infos(cls, project: str, infos: List[Dict], keys: List[str]):
        """
        填充插件节点部署数量
        :param project:
        :param infos:
        :param keys:
        :return:
        """
        nodes_counter = cls.get_packages_node_numbers(projects=[project], keys=keys)

        # TODO 可能出现部分主机没有具体部署版本，导致统计总数出现偏差
        for info in infos:
            info["nodes_number"] = nodes_counter.get(f"{project}_{info['os']}_{info['cpu_arch']}_{info['version']}", 0)

    @classmethod
    def get_proj_os_cpu__latest_version_map(cls, projects: Union[List[str], Set[str]]) -> Dict[str, str]:
        packages = list(
            models.Packages.objects.filter(project__in=set(projects), is_release_version=True, is_ready=True).values(
                "project", "version", "os", "cpu_arch"
            )
        )

        proj_os_cpu__latest_version_map = {}
        for project, pkgs in groupby(sorted(packages, key=lambda pkg: pkg["project"]), lambda pkg: pkg["project"]):
            for pkg in sorted(pkgs, key=lambda x: version.parse(x["version"])):
                proj_os_cpu_key = f"{pkg['project']}_{pkg['os']}_{pkg['cpu_arch']}"
                proj_os_cpu__latest_version_map[proj_os_cpu_key] = pkg["version"]

        return proj_os_cpu__latest_version_map
