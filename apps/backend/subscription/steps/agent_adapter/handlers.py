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
from collections import defaultdict
from typing import Any, Dict, List, Optional, Type

from apps.backend import exceptions
from apps.node_man import constants
from apps.node_man.constants import GsePackageCode, NodeType
from apps.node_man.models import (
    GseConfigEnv,
    GseConfigExtraEnv,
    GseConfigTemplate,
    Host,
)
from apps.utils import cache

from . import config_templates
from .base import AgentConfigTemplate

logger = logging.getLogger("app")


class GseConfigHandler:

    AGENT_NAME = None

    def __init__(self, target_version: str) -> None:
        self.target_version = target_version
        self._config_extra_env_cache: Dict[int, List[GseConfigExtraEnv]] = {}

    def fetch_config_extra_envs(self, bk_biz_id: int) -> List[GseConfigExtraEnv]:
        config_extra_envs: Optional[List[GseConfigExtraEnv]] = self._config_extra_env_cache.get(bk_biz_id)
        # 区分 None 和 []，None 表示无缓存，[] 表示没有这些数据
        if config_extra_envs is not None:
            return config_extra_envs
        # sort by id，id 越大，优先级越高
        config_extra_envs = sorted(
            list(GseConfigExtraEnv.objects.filter(bk_biz_id=bk_biz_id, enable=True)), key=lambda obj: obj.id
        )
        self._config_extra_env_cache[bk_biz_id] = config_extra_envs
        return config_extra_envs

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
        config_tmpl_obj_gby_os_key: Dict[str, List[AgentConfigTemplate]] = defaultdict(list)
        config_tmpls: List[GseConfigTemplate] = GseConfigTemplate.objects.filter(version=self.target_version)
        for config_tmpl in config_tmpls:
            config_tmpl_obj_gby_os_key[self.get_os_key(config_tmpl.os, config_tmpl.cpu_arch)].append(
                AgentConfigTemplate(name=config_tmpl.name, content=config_tmpl.content)
            )

        # 为空说明该版本的配置文件都不存在，此时直接返回默认的配置模板
        return config_tmpl_obj_gby_os_key or {
            # 向 Agent 包管理过渡：AgentConfigTemplate 后续替换为数据模型对象
            self.get_os_key(constants.OsType.LINUX, constants.CpuType.x86): self.agent_config_templates,
            self.get_os_key(constants.OsType.LINUX, constants.CpuType.x86_64): self.agent_config_templates,
            self.get_os_key(constants.OsType.WINDOWS, constants.CpuType.x86): self.agent_config_templates,
            self.get_os_key(constants.OsType.WINDOWS, constants.CpuType.x86_64): self.agent_config_templates,
        }

    @property
    @cache.class_member_cache()
    def os_key__tmpl_env_map(self) -> Dict[str, Dict[str, Any]]:
        os_key__tmpl_env_map: Dict[str, Dict[str, Any]] = {}
        config_envs: List[GseConfigEnv] = GseConfigEnv.objects.filter(
            agent_name=self.AGENT_NAME, version=self.target_version
        )
        for config_env in config_envs:
            os_key__tmpl_env_map[self.get_os_key(config_env.os, config_env.cpu_arch)] = config_env.env_value

        return os_key__tmpl_env_map

    def get_matching_config_tmpl(self, os_type: str, cpu_arch: str, config_name: str) -> AgentConfigTemplate:
        config_tmpl_objs: List[AgentConfigTemplate] = self.config_tmpl_obj_gby_os_key.get(
            self.get_os_key(os_type, cpu_arch), self.agent_config_templates
        )
        # 查找机型匹配的第一个配置
        target_config_tmpl_obj: AgentConfigTemplate = next(
            (config_tmpl_obj for config_tmpl_obj in config_tmpl_objs if config_tmpl_obj.name == config_name), None
        )
        if not target_config_tmpl_obj:
            logger.error(
                "[GseConfigHandler(get_matching_config_tmpl)] AgentConfigTemplate not exist: "
                "name -> %s, config_name -> %s, os_type -> %s, cpu_arch -> %s",
                self.AGENT_NAME,
                config_name,
                os_type,
                cpu_arch,
            )
            raise exceptions.AgentConfigTemplateNotExistError(
                name=self.AGENT_NAME, filename=config_name, os_type=os_type, cpu_arch=cpu_arch
            )
        return target_config_tmpl_obj

    def get_matching_template_env(self, os_type: str, cpu_arch: str) -> Dict[str, Any]:
        return self.os_key__tmpl_env_map.get(self.get_os_key(os_type, cpu_arch)) or {}

    def get_matching_template_extra_env(self, host: Host) -> Dict[str, Any]:
        template_extra_env: Dict[str, Any] = {}
        host_info: Dict[str, Any] = {
            "bk_host_id": host.bk_host_id,
            "cloud_ip": f"{host.bk_cloud_id}:{host.inner_ip}",
            "install_channel_id": host.install_channel_id,
            "bk_cloud_id": host.bk_cloud_id,
            "node_type": host.node_type,
            "os_type": host.os_type,
        }
        config_extra_envs: List[GseConfigExtraEnv] = self.fetch_config_extra_envs(host.bk_biz_id)
        for config_extra_env in config_extra_envs:
            hits: int = 0
            try:
                for host_property, value in host_info.items():
                    if (
                        host_property in config_extra_env.condition
                        and value in config_extra_env.condition[host_property]
                    ):
                        hits += 1
                # 命中全部规则，应用该额外配置
                if hits == len(config_extra_env.condition.keys()):
                    template_extra_env.update(config_extra_env.env_value)
            except Exception:
                logger.exception(
                    "[GseConfigHandler(get_matching_template_extra_env)] config_extra_env error: condition -> %s",
                    config_extra_env.condition,
                )
        return template_extra_env


class AgentGseConfigHandler(GseConfigHandler):
    AGENT_NAME = GsePackageCode.AGENT.value


class ProxyGseConfigHandler(GseConfigHandler):
    AGENT_NAME = GsePackageCode.PROXY.value


GSE_CONFIG_HANDLER_PACKAGE_CODE_MAP: Dict = {
    NodeType.AGENT.lower(): AgentGseConfigHandler,
    NodeType.PROXY.lower(): ProxyGseConfigHandler,
}


def get_gse_config_handler_class(node_type: str) -> Type[GseConfigHandler]:
    return GSE_CONFIG_HANDLER_PACKAGE_CODE_MAP[node_type]
