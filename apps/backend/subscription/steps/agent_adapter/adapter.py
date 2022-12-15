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
import typing
from collections import OrderedDict
from dataclasses import dataclass, field

from rest_framework import serializers

from apps.backend import exceptions
from apps.node_man import constants, models
from apps.utils import cache

from . import base, config_templates, legacy
from .config_context import context_helper

logger = logging.getLogger("app")

LEGACY = "legacy"


class AgentStepConfigSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, label="构件名称")
    # LEGACY 表示旧版本 Agent，仅做兼容
    version = serializers.CharField(required=False, label="构件版本", default=LEGACY)
    job_type = serializers.ChoiceField(required=True, choices=constants.JOB_TUPLE)


@dataclass
class AgentStepAdapter:

    # 订阅步骤数据对象
    subscription_step: models.SubscriptionStep

    # 是否为旧版本 Agent，用于兼容旁路判定
    is_legacy: bool = field(init=False)
    # 日志前缀
    log_prefix: str = field(init=False)

    def __post_init__(self):
        self.is_legacy = self.config["version"] == LEGACY
        self.log_prefix: str = (
            f"[{self.__class__.__name__}({self.subscription_step.step_id})] | {self.subscription_step} |"
        )

    @property
    @cache.class_member_cache()
    def config(self) -> OrderedDict:
        """
        获取订阅步骤配置
        :return:
        """
        return self.validated_data(data=self.subscription_step.config, serializer=AgentStepConfigSerializer)

    @property
    @cache.class_member_cache()
    def config_tmpl_obj_gby_os_key(self) -> typing.Dict[str, typing.List[base.AgentConfigTemplate]]:
        """
        获取按机型（os_type + cpu_arch）聚合的配置模板
        :return:
        """
        agent_config_templates: typing.List[base.AgentConfigTemplate] = [
            base.AgentConfigTemplate(name="gse_agent.conf", content=config_templates.GSE_AGENT_CONFIG_TMPL),
            base.AgentConfigTemplate(name="gse_data_proxy.conf", content=config_templates.GSE_DATA_PROXY_CONFIG_TMPL),
            base.AgentConfigTemplate(name="gse_file_proxy.conf", content=config_templates.GSE_FILE_PROXY_CONFIG_TEMPL),
        ]
        return {
            # 向 Agent 包管理过渡：AgentConfigTemplate 后续替换为数据模型对象
            self.get_os_key(constants.OsType.LINUX, constants.CpuType.x86): agent_config_templates,
            self.get_os_key(constants.OsType.LINUX, constants.CpuType.x86_64): agent_config_templates,
            self.get_os_key(constants.OsType.WINDOWS, constants.CpuType.x86): agent_config_templates,
            self.get_os_key(constants.OsType.WINDOWS, constants.CpuType.x86_64): agent_config_templates,
        }

    def get_main_config_filename(self) -> str:
        return ("gse_agent.conf", "agent.conf")[self.is_legacy]

    def _get_config(
        self,
        host: models.Host,
        filename: str,
        node_type: str,
        ap: typing.Optional[models.AccessPoint] = None,
        proxies: typing.Optional[typing.List[models.Host]] = None,
        install_channel: typing.Tuple[typing.Optional[models.Host], typing.Dict[str, typing.List]] = None,
    ) -> str:
        config_tmpl_objs: typing.List[base.AgentConfigTemplate] = self.config_tmpl_obj_gby_os_key.get(
            self.get_os_key(host.os_type, host.cpu_arch),
            [
                base.AgentConfigTemplate(name="gse_agent.conf", content=config_templates.GSE_AGENT_CONFIG_TMPL),
                base.AgentConfigTemplate(
                    name="gse_data_proxy.conf", content=config_templates.GSE_DATA_PROXY_CONFIG_TMPL
                ),
                base.AgentConfigTemplate(
                    name="gse_file_proxy.conf", content=config_templates.GSE_FILE_PROXY_CONFIG_TEMPL
                ),
            ],
        )
        # 查找机型匹配的第一个配置
        target_config_tmpl_obj: base.AgentConfigTemplate = next(
            (config_tmpl_obj for config_tmpl_obj in config_tmpl_objs if config_tmpl_obj.name == filename), None
        )

        if not target_config_tmpl_obj:
            logger.error(
                f"{self.log_prefix} agent config template not exist: name -> {self.config['name']}, "
                f"filename -> {filename}, version -> {self.config['version']}, "
                f"os_type -> {host.os_type}, cpu_arch -> {host.cpu_arch}"
            )
            raise exceptions.AgentConfigTemplateNotExistError(
                name=self.config["name"], filename=filename, os_type=host.os_type, cpu_arch=host.cpu_arch
            )

        # 渲染配置
        ch: context_helper.ConfigContextHelper = context_helper.ConfigContextHelper(
            agent_setup_info=self.get_setup_info(),
            host=host,
            node_type=node_type,
            ap=ap,
            proxies=proxies,
            install_channel=install_channel,
        )
        return ch.render(target_config_tmpl_obj.content)

    def get_config(
        self,
        host: models.Host,
        filename: str,
        node_type: str,
        ap: typing.Optional[models.AccessPoint] = None,
        proxies: typing.Optional[typing.List[models.Host]] = None,
        install_channel: typing.Tuple[typing.Optional[models.Host], typing.Dict[str, typing.List]] = None,
    ) -> str:
        """
        获取配置
        :param host: 主机对象
        :param filename: 文件名
        :param node_type: 节点类型（lower）
        :param ap: 接入点对象
        :param proxies: Proxy 主机列表
        :param install_channel: 安装通道
        :return:
        """
        func: typing.Callable[..., str] = (self._get_config, legacy.generate_gse_config)[self.is_legacy]
        return func(
            host=host, filename=filename, node_type=node_type, ap=ap, proxies=proxies, install_channel=install_channel
        )

    def get_setup_info(self) -> base.AgentSetupInfo:
        """
        获取 Agent 设置信息
        :return:
        """
        return base.AgentSetupInfo(
            is_legacy=self.is_legacy,
            agent_tools_relative_dir=("agent_tools/agent2", "")[self.is_legacy],
            name=self.config.get("name"),
            version=self.config.get("version"),
        )

    @staticmethod
    def validated_data(data, serializer) -> OrderedDict:
        data_serializer = serializer(data=data)
        data_serializer.is_valid(raise_exception=True)
        return data_serializer.validated_data

    @staticmethod
    def get_os_key(os_type: str, cpu_arch: str) -> str:
        # 默认为 linux-x86_64，兼容CMDB同步过来的主机没有操作系统和CPU架构的场景
        os_type = os_type or constants.OsType.LINUX
        cpu_arch = cpu_arch or constants.CpuType.x86_64
        return f"{os_type.lower()}-{cpu_arch}"
