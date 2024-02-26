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

from apps.backend.agent.tools import fetch_proxies
from apps.backend.constants import ProxyConfigFile
from apps.backend.subscription import errors
from apps.core.tag.constants import TargetType
from apps.core.tag.targets import get_target_helper
from apps.node_man import constants, models
from apps.utils import cache
from env.constants import GseVersion

from . import base, legacy
from .config_context import context_helper
from .handlers import GseConfigHandler

logger = logging.getLogger("app")


LEGACY = "legacy"


class AgentVersionSerializer(serializers.Serializer):
    os_cpu_arch = serializers.CharField(label="系统CPU架构", required=False)
    bk_host_id = serializers.IntegerField(label="主机ID", required=False)
    version = serializers.CharField(label="Agent Version")


class AgentStepConfigSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, label="构件名称")
    # LEGACY 表示旧版本 Agent，仅做兼容
    version = serializers.CharField(required=False, label="构件版本", default=LEGACY)
    job_type = serializers.ChoiceField(required=True, choices=constants.JOB_TUPLE)
    choice_version_type = serializers.ChoiceField(
        required=False, choices=constants.AgentVersionType.list_choices(), label="选择Agent Version类型"
    )
    version_map_list = AgentVersionSerializer(many=True)


@dataclass
class AgentStepAdapter:

    # 订阅步骤数据对象
    subscription_step: models.SubscriptionStep

    # GSE 版本
    # From Pipeline Meta or models.Host.ap_id
    gse_version: str = GseVersion.V1.value

    # 是否为旧版本 Agent，用于兼容旁路判定
    is_legacy: bool = field(init=False)
    # 日志前缀
    log_prefix: str = field(init=False)
    # 配置处理模块缓存
    _config_handler_cache: typing.Dict[str, GseConfigHandler] = field(init=False)
    _setup_info_cache: typing.Dict[str, base.AgentSetupInfo] = field(init=False)
    _target_version_cache: typing.Dict[str, str] = field(init=False)
    agent_name: str = field(init=False)

    def __post_init__(self):
        self.is_legacy = self.gse_version == GseVersion.V1.value
        self.log_prefix: str = (
            f"[{self.__class__.__name__}({self.subscription_step.step_id})] | {self.subscription_step} |"
        )
        self._config_handler_cache: typing.Dict[str, GseConfigHandler] = {}
        self._setup_info_cache: typing.Dict[str, base.AgentSetupInfo] = {}
        self._target_version_cache: typing.Dict[str, str] = {}
        self.agent_name = self.config.get("name")

    def get_config_handler(self, agent_name: str, target_version: str) -> GseConfigHandler:

        # 预留 AgentStepAdapter 支持多 Agent 版本的场景
        cache_key: str = f"agent_name:{agent_name}:version:{target_version}"
        config_handler: typing.Optional[GseConfigHandler] = self._config_handler_cache.get(cache_key)
        if config_handler:
            return config_handler

        config_handler: GseConfigHandler = GseConfigHandler(agent_name=agent_name, target_version=target_version)
        self._config_handler_cache[cache_key] = config_handler
        return config_handler

    @property
    @cache.class_member_cache()
    def config(self) -> OrderedDict:
        """
        获取订阅步骤配置
        :return:
        """
        return self.validated_data(data=self.subscription_step.config, serializer=AgentStepConfigSerializer)

    def get_main_config_filename(self) -> str:
        return ("gse_agent.conf", "agent.conf")[self.is_legacy]

    def get_config_filename_by_node_type(self, node_type: str) -> typing.List[str]:
        if node_type == constants.NodeType.PROXY:
            return (ProxyConfigFile.V2.value, ProxyConfigFile.V1.value)[self.is_legacy]
        return [self.get_main_config_filename()]

    def _get_config(
        self,
        host: models.Host,
        filename: str,
        node_type: str,
        ap: models.AccessPoint,
        proxies: typing.List[models.Host],
        install_channel: typing.Tuple[typing.Optional[models.Host], typing.Dict[str, typing.List]],
        target_version: typing.Optional[typing.Dict[int, str]] = None,
    ) -> str:
        agent_setup_info: base.AgentSetupInfo = self.get_host_setup_info(host)
        # 目标版本优先使用传入版本，传入版本必不会是标签所以可直接使用
        config_handler: GseConfigHandler = self.get_config_handler(
            agent_setup_info.name, target_version or agent_setup_info.version
        )

        config_tmpl_obj: base.AgentConfigTemplate = config_handler.get_matching_config_tmpl(
            os_type=host.os_type,
            cpu_arch=host.cpu_arch,
            config_name=filename,
        )

        # 渲染配置
        ch: context_helper.ConfigContextHelper = context_helper.ConfigContextHelper(
            agent_setup_info=agent_setup_info,
            host=host,
            node_type=node_type,
            ap=ap,
            proxies=proxies,
            install_channel=install_channel,
        )
        return ch.render(
            config_tmpl_obj.content,
            config_handler.get_matching_template_env(host.os_type, host.cpu_arch, config_tmpl_obj.agent_name_from),
            config_handler.get_matching_template_extra_env(host),
        )

    def get_config(
        self,
        host: models.Host,
        filename: str,
        node_type: str,
        ap: typing.Optional[models.AccessPoint] = None,
        proxies: typing.Optional[typing.List[models.Host]] = None,
        install_channel: typing.Tuple[typing.Optional[models.Host], typing.Dict[str, typing.List]] = None,
        target_version: typing.Optional[str] = None,
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

        ap = ap or host.ap
        proxies = proxies if proxies is not None else fetch_proxies(host, ap)
        install_channel = install_channel or host.install_channel(ap_id=ap.id)

        func: typing.Callable[..., str] = (self._get_config, legacy.generate_gse_config)[self.is_legacy]
        return func(
            host=host,
            filename=filename,
            node_type=node_type,
            ap=ap,
            proxies=proxies,
            install_channel=install_channel,
            target_version=target_version,
        )

    @property
    @cache.class_member_cache()
    def bk_host_id_version_map(self) -> typing.Dict[int, str]:
        return {versiom_map["bk_host_id"]: versiom_map["version"] for versiom_map in self.config["version_map_list"]}

    def get_host_setup_info(self, host: models.Host) -> base.AgentSetupInfo:
        """
        获取 Agent 设置信息
        :return:
        """
        # 如果版本号匹配到标签名称，取对应标签下的真实版本号，否则取原来的版本号
        if self.agent_name is None:
            # 1.0 Install 或者 2.0统一版本
            target_version = self.config.get("version")
            setup_info_cache_key: str = f"agent_name_is_none:version:{target_version}"
        else:
            if self.config["choice_version_type"] == constants.AgentVersionType.UNIFIED.value:
                agent_version = self.config.get("version")
                setup_info_cache_key: str = (
                    f"agent_name:{self.agent_name}:"
                    f"type:{constants.AgentVersionType.UNIFIED.value}:version:{agent_version}"
                )
            elif self.config["choice_version_type"] == constants.AgentVersionType.BY_SYSTEM_ARCH.value:
                # TODO 按系统架构维度, 当前只支持按系统，后续需求完善按系统架构
                os_cpu_arch_version_list: typing.List[str] = [
                    versiom_map["version"]
                    for versiom_map in self.config["version_map_list"]
                    if host.os_type.lower() in versiom_map["os_cpu_arch"]
                ]
                agent_version: str = os_cpu_arch_version_list[0] if os_cpu_arch_version_list else "stable"
                setup_info_cache_key: str = (
                    f"agent_name:{self.agent_name}:type:{constants.AgentVersionType.BY_SYSTEM_ARCH.value}:"
                    f"os:{host.os_type.lower()}:version:{agent_version}"
                )
            else:
                # 按主机维度
                agent_version: str = self.bk_host_id_version_map[host.bk_host_id]

            target_version_cache_key: str = f"agent_desc_id:{self.agent_desc.id}:agent_version:{agent_version}"
            target_version: str = self._target_version_cache.get(target_version_cache_key)
            if target_version is None:
                target_version: str = get_target_helper(TargetType.AGENT.value).get_target_version(
                    target_id=self.agent_desc.id,
                    target_version=agent_version,
                )
                self._target_version_cache[target_version_cache_key] = target_version

        if self.config["choice_version_type"] != constants.AgentVersionType.BY_HOST.value:
            agent_setup_info: typing.Optional[base.AgentSetupInfo] = self._setup_info_cache.get(setup_info_cache_key)
            if agent_setup_info:
                return agent_setup_info

        agent_setup_info: base.AgentSetupInfo = base.AgentSetupInfo(
            is_legacy=self.is_legacy,
            agent_tools_relative_dir=("agent_tools/agent2", "")[self.is_legacy],
            name=self.config.get("name"),
            version=target_version,
        )
        if self.config["choice_version_type"] != constants.AgentVersionType.BY_HOST.value:
            self._setup_info_cache[setup_info_cache_key] = agent_setup_info
        return agent_setup_info

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

    @property
    def agent_desc(self) -> models.GsePackageDesc:
        if hasattr(self, "_agent_desc") and self._agent_desc:
            return self._agent_desc
        try:
            agent_desc = models.GsePackageDesc.objects.get(project=self.agent_name)
        except models.GsePackageDesc.DoesNotExist:
            raise errors.AgentPackageValidationError(msg="GsePackageDesc [{name}] 不存在".format(name=self.agent_name))

        setattr(self, "_agent_desc", agent_desc)
        return self._agent_desc
