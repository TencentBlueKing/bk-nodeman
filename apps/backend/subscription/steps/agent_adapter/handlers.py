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
from typing import Dict, List, Tuple

from apps.backend import exceptions
from apps.node_man import constants
from apps.node_man.constants import GsePackageCode, NodeType
from apps.node_man.models import GlobalSettings, GseConfigEnv, GseConfigTemplate
from apps.utils import cache

from . import config_templates
from .base import AgentConfigTemplate

logger = logging.getLogger("app")


class GseConfigHandler:
    AGENT_NAME = None

    def __init__(self, os_type: str, cpu_arch: str, target_version: str) -> None:
        self.os_type = os_type
        self.cpu_arch = cpu_arch
        self.target_version = target_version
        self.enable_agent_pkg_manage: bool = GlobalSettings.get_config(
            key=GlobalSettings.KeyEnum.ENABLE_AGENT_PKG_MANAGE.value, default=False
        )

    @staticmethod
    def get_os_key(os_type: str, cpu_arch: str) -> str:
        # 默认为 linux-x86_64，兼容CMDB同步过来的主机没有操作系统和CPU架构的场景
        os_type = os_type or constants.OsType.LINUX
        cpu_arch = cpu_arch or constants.CpuType.x86_64
        return f"{os_type.lower()}-{cpu_arch}"

    @property
    @cache.class_member_cache()
    def agent_config_templates(self) -> List[AgentConfigTemplate]:
        return [
            AgentConfigTemplate(name="gse_agent.conf", content=config_templates.GSE_AGENT_CONFIG_TMPL),
            AgentConfigTemplate(name="gse_data_proxy.conf", content=config_templates.GSE_DATA_PROXY_CONFIG_TMPL),
            AgentConfigTemplate(name="gse_file_proxy.conf", content=config_templates.GSE_FILE_PROXY_CONFIG_TEMPL),
        ]

    @property
    @cache.class_member_cache()
    def config_tmpl_obj_gby_os_key(self) -> Dict[str, List[AgentConfigTemplate]]:
        """
        获取按机型（os_type + cpu_arch）聚合的配置模板
        :return:
        """
        return {
            # 向 Agent 包管理过渡：AgentConfigTemplate 后续替换为数据模型对象
            self.get_os_key(constants.OsType.LINUX, constants.CpuType.x86): self.agent_config_templates,
            self.get_os_key(constants.OsType.LINUX, constants.CpuType.x86_64): self.agent_config_templates,
            self.get_os_key(constants.OsType.WINDOWS, constants.CpuType.x86): self.agent_config_templates,
            self.get_os_key(constants.OsType.WINDOWS, constants.CpuType.x86_64): self.agent_config_templates,
        }

    def _get_template_from_file(self, config_name) -> Tuple[bool, AgentConfigTemplate]:
        config_tmpl_objs: List[AgentConfigTemplate] = self.config_tmpl_obj_gby_os_key.get(
            self.get_os_key(self.os_type, self.cpu_arch),
            self.agent_config_templates,
        )
        # 查找机型匹配的第一个配置
        target_config_tmpl_obj: AgentConfigTemplate = next(
            (config_tmpl_obj for config_tmpl_obj in config_tmpl_objs if config_tmpl_obj.name == config_name), None
        )
        if not target_config_tmpl_obj:
            return False, None
        return True, target_config_tmpl_obj

    def _get_template_from_db(self, config_name) -> Tuple[bool, AgentConfigTemplate]:
        try:
            template = GseConfigTemplate.objects.get(
                os=self.os_type.lower(), cpu_arch=self.cpu_arch, version=self.target_version, name=config_name
            )
        except GseConfigTemplate.DoesNotExist:
            return False, None

        return True, AgentConfigTemplate(name=config_name, content=template.content)

    def get_template_by_config_name(self, config_name: str) -> AgentConfigTemplate:
        # 兼容原运行模式
        is_ok, config_tmpl_obj = [self._get_template_from_file, self._get_template_from_db][
            self.enable_agent_pkg_manage
        ](config_name=config_name)
        if not is_ok:
            logger.error(
                f"Agent config template not exist: name -> {self.AGENT_NAME}, "
                f"filename -> {config_name}, version -> {self.target_version}, "
                f"os_type -> {self.os_type}, cpu_arch -> {self.cpu_arch}"
            )
            raise exceptions.AgentConfigTemplateNotExistError(
                name=self.AGENT_NAME, filename=config_name, os_type=self.os_type, cpu_arch=self.cpu_arch
            )

        return config_tmpl_obj

    @property
    def template_env(self) -> Dict:
        if not self.enable_agent_pkg_manage:
            # 兼容 未开启Agent包管理情况
            return {}
        try:
            template_env: GseConfigEnv = GseConfigEnv.objects.get(
                agent_name=self.AGENT_NAME,
                os=self.os_type,
                cpu_arch=self.cpu_arch,
                version=self.target_version,
            )
        except GseConfigEnv.DoesNotExist:
            logger.error(
                f"Agent config template env not exist: name -> {self.AGENT_NAME}, "
                f"version -> {self.target_version}, os_type -> {self.os_type}, cpu_arch -> {self.cpu_arch}"
            )
            raise exceptions.AgentConfigTemplateEnvNotExistError(
                name=self.AGENT_NAME,
                version=self.target_version,
                os_type=self.os_type,
                cpu_arch=self.cpu_arch,
            )
        return template_env.env_value


class AgentGseConfigHandler(GseConfigHandler):
    AGENT_NAME = GsePackageCode.AGENT.value


class ProxyGseConfigHandler(GseConfigHandler):
    AGENT_NAME = GsePackageCode.PROXY.value


GSE_CONFIG_HANDLER_PACKAGE_CODE_MAP: Dict = {
    NodeType.AGENT.lower(): AgentGseConfigHandler,
    NodeType.PROXY.lower(): ProxyGseConfigHandler,
}


def get_gse_config_handler_class(node_type: str) -> GseConfigHandler:
    return GSE_CONFIG_HANDLER_PACKAGE_CODE_MAP[node_type]
