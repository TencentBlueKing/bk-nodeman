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

import abc
from typing import Any, Dict, List, Optional, Tuple, Union

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from apps.backend import constants as backend_const
from apps.backend.agent.manager import AgentManager
from apps.node_man import constants, models
from apps.node_man.constants import DEFAULT_CLOUD
from apps.node_man.models import GsePluginDesc, SubscriptionStep
from env.constants import GseVersion
from pipeline import builder
from pipeline.builder import Var
from pipeline.builder.flow.base import Element

# 需分发到 PROXY 的文件（由于放到一次任务中会给用户等待过久的体验，因此拆分成多次任务）
from .base import Action, Step


class AgentStep(Step):
    # 订阅步骤类型
    STEP_TYPE = constants.SubStepType.AGENT

    # 需要自动拉起的插件列表
    auto_launch_plugins: Optional[List[models.GsePluginDesc]] = None

    def __init__(self, subscription_step: SubscriptionStep):
        self.auto_launch_plugins = GsePluginDesc.get_auto_launch_plugins()
        super(AgentStep, self).__init__(subscription_step)

    def get_package_by_os(self, os_type):
        return

    def get_supported_actions(self):
        supported_actions = [
            InstallAgent,
            ReinstallAgent,
            UninstallAgent,
            UpgradeAgent,
            RestartAgent,
            InstallProxy,
            ReinstallProxy,
            UninstallProxy,
            ReplaceProxy,
            UpgradeProxy,
            RestartProxy,
            ReloadAgent,
            ReloadProxy,
            ActivateAgent,
            InstallAgent2,
            ReinstallAgent2,
            InstallProxy2,
            ReinstallProxy2,
        ]
        return {action.ACTION_NAME: action for action in supported_actions}

    def get_step_data(self, instance_info, target_host, agent_config):
        """
        获取步骤上下文数据
        """
        return

    def generate_agent_control_info(self, host_status):
        """
        生成Agent控制信息
        """
        return

    def make_instances_migrate_actions(self, instances, auto_trigger=False, preview_only=False, **kwargs):
        """
        安装Agent不需要监听CMDB变更
        若有需要按CMDB拓扑变更自动安装Agent的需求，需完善此方法
        """

        if self.subscription_step.config["job_type"] not in [
            backend_const.ActionNameType.INSTALL_AGENT,
            backend_const.ActionNameType.REINSTALL_AGENT,
            backend_const.ActionNameType.UPGRADE_AGENT,
            backend_const.ActionNameType.INSTALL_PROXY,
            backend_const.ActionNameType.REINSTALL_PROXY,
            backend_const.ActionNameType.UPGRADE_PROXY,
        ]:
            # 如果非安装类操作或者操作无需计算变更
            instance_actions = {instance_id: self.subscription_step.config["job_type"] for instance_id in instances}
            return {"instance_actions": instance_actions, "migrate_reasons": {}}

        instance_actions: Dict[str, str] = {}
        migrate_reasons: Dict[str, Dict[str, Any]] = {}
        # 新版本 Agent 操作映射关系
        job_type_map: Dict[str, str] = {
            backend_const.ActionNameType.INSTALL_AGENT: backend_const.ActionNameType.INSTALL_AGENT_2,
            backend_const.ActionNameType.REINSTALL_AGENT: backend_const.ActionNameType.REINSTALL_AGENT_2,
            # Agent2 走自更新，仍需调整
            backend_const.ActionNameType.UPGRADE_AGENT: backend_const.ActionNameType.UPGRADE_AGENT,
            backend_const.ActionNameType.INSTALL_PROXY: backend_const.ActionNameType.INSTALL_PROXY_2,
            backend_const.ActionNameType.REINSTALL_PROXY: backend_const.ActionNameType.REINSTALL_PROXY_2,
            # Agent2 走自更新，仍需调整
            backend_const.ActionNameType.UPGRADE_PROXY: backend_const.ActionNameType.UPGRADE_PROXY,
        }
        for instance_id, instance in instances.items():
            if instance["meta"]["GSE_VERSION"] == GseVersion.V1.value:
                instance_actions[instance_id] = self.subscription_step.config["job_type"]
                continue
            instance_actions[instance_id] = job_type_map[self.subscription_step.config["job_type"]]

        return {"instance_actions": instance_actions, "migrate_reasons": migrate_reasons}


class AgentAction(Action, abc.ABC):
    """
    步骤动作调度器
    """

    ACTION_NAME = ""
    # 动作描述
    ACTION_DESCRIPTION = ""

    step: AgentStep = None
    is_install_latest_plugins: bool = None
    enable_push_host_identifier: bool = None
    is_install_other_agent: bool = None
    is_install_other_agent_v1: bool = None
    is_install_other_agent_v2: bool = None

    def __init__(self, action_name, step: AgentStep, instance_record_ids: List[int]):
        """
        :param Step step: 步骤实例
        :param models.SubscriptionInstanceRecord instance_record_ids: 订阅实例执行记录
        """
        self.step = step
        self.is_install_latest_plugins = self.step.subscription_step.params.get("is_install_latest_plugins", True)
        self.enable_push_host_identifier = models.GlobalSettings.get_config(
            models.GlobalSettings.KeyEnum.ENABLE_PUSH_HOST_IDENTIFIER.value, False
        )

        self.is_install_other_agent = self.step.subscription_step.params.get("is_install_other_agent", False)

        self.is_install_other_agent_v1 = models.GlobalSettings.get_config(
            models.GlobalSettings.KeyEnum.IS_INSTALL_OTHER_AGENT_V1.value, False
        )
        self.is_install_other_agent_v2 = models.GlobalSettings.get_config(
            models.GlobalSettings.KeyEnum.IS_INSTALL_OTHER_AGENT_V2.value, False
        )
        super().__init__(action_name, step, instance_record_ids)

    def get_agent_manager(self, subscription_instances: List[models.SubscriptionInstanceRecord]):
        """
        根据主机生成Agent管理器
        """
        subscription_instance_ids = [sub_inst.id for sub_inst in subscription_instances]
        return AgentManager(subscription_instance_ids, self.step)

    @abc.abstractmethod
    def _generate_activities(self, agent_manager):
        pass

    @property
    def install_other_agent_codes(self):

        return [
            # 安装或重装code
            "query_password",
            "bind_host_agent",
            "upgrade_to_agent_id",
            "push_agent_pkg_to_proxy",
            "install",
            "check_policy_gse_to_proxy",
            "configure_policy",
            # 重载配置相关code
            "agent_check_agent_status",
            "update_install_info",
            "render_and_push_gse_config",
            "reload_agent_config",
            "wait",
            "check_agent_ability",
            # 共用code
            "get_agent_status",
        ]

    def generate_activities(
        self,
        subscription_instances: List[models.SubscriptionInstanceRecord],
        global_pipeline_data: builder.Data,
        meta: Dict[str, Any],
        current_activities=None,
        is_multi_paralle_gateway=False,
    ) -> Tuple[List[Union[builder.ServiceActivity, Element]], Optional[builder.Data]]:
        agent_manager = self.get_agent_manager(subscription_instances)
        activities, pipeline_data = self._generate_activities(agent_manager)
        for act in activities:
            act.component.inputs.subscription_step_id = Var(type=Var.PLAIN, value=self.step.subscription_step.id)
            act.component.inputs.meta = Var(type=Var.PLAIN, value=meta)
            act.component.inputs.is_multi_paralle_gateway = Var(type=Var.PLAIN, value=is_multi_paralle_gateway)
        self.inject_vars_to_global_data(global_pipeline_data, meta)
        if self.is_install_other_agent:
            activities = list(filter(lambda x: x.component["code"] in self.install_other_agent_codes, activities))
        return activities, pipeline_data

    def append_delegate_activities(self, agent_manager, activities):
        for plugin in self.step.auto_launch_plugins:
            activities.append(agent_manager.delegate_plugin(plugin.name))
        return activities

    def has_non_lan_host(self) -> bool:
        """判断这批任务中是否包含非直连的主机"""
        for node in self.step.subscription.nodes:
            try:
                instance_info = node["instance_info"]
            except KeyError:
                # Agent 重装场景下不存在 instance_info
                # refer：apps/node_man/handlers/validator.py bulk_update_validate
                instance_info = node
            # 只要包含一台非默认管控区域的机器，或者存在安装通道，则认为是非直连机器
            if instance_info.get("bk_cloud_id") != DEFAULT_CLOUD:
                return True
            if instance_info.get("install_channel_id"):
                return True
        return False

    @staticmethod
    def append_push_file_activities(agent_manager, activities, files=None):
        if files is None:
            files = constants.FILES_TO_PUSH_TO_PROXY
        for file in files:
            activities.append(agent_manager.push_files_to_proxy(file))
        return activities


class InstallAgent(AgentAction):
    """
    安装Agent
    """

    ACTION_NAME = backend_const.ActionNameType.INSTALL_AGENT
    ACTION_DESCRIPTION = _("安装")

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.add_or_update_hosts() if settings.BKAPP_ENABLE_DHCP else agent_manager.register_host(),
            agent_manager.query_password(),
            agent_manager.choose_ap(),
            agent_manager.push_agent_pkg_to_proxy() if self.has_non_lan_host() else None,
            agent_manager.install(),
            # 安装1.0完成后，安装2.0
            agent_manager.install_other_agent(extra_agent_version=GseVersion.V2.value)
            if all(
                [
                    not self.is_install_other_agent,
                    self.is_install_other_agent_v2,
                ]
            )
            else None,
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING),
            agent_manager.push_host_identifier() if self.enable_push_host_identifier else None,
            agent_manager.push_environ_files() if settings.GSE_ENABLE_PUSH_ENVIRON_FILE else None,
            agent_manager.install_plugins() if self.is_install_latest_plugins else None,
        ]

        return list(filter(None, activities)), None


class ReinstallAgent(AgentAction):
    """
    重装Agent
    """

    ACTION_NAME = backend_const.ActionNameType.REINSTALL_AGENT
    ACTION_DESCRIPTION = _("重装")

    def _generate_activities(self, agent_manager: AgentManager):

        activities = [
            agent_manager.add_or_update_hosts() if settings.BKAPP_ENABLE_DHCP else None,
            agent_manager.query_password(),
            agent_manager.choose_ap(),
            agent_manager.push_agent_pkg_to_proxy() if self.has_non_lan_host() else None,
            agent_manager.install(),
            # 安装1.0完成后，安装2.0
            agent_manager.install_other_agent(extra_agent_version=GseVersion.V2.value)
            if all(
                [
                    not self.is_install_other_agent,
                    self.is_install_other_agent_v2,
                ]
            )
            else None,
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING),
            agent_manager.push_host_identifier() if self.enable_push_host_identifier else None,
            agent_manager.push_environ_files() if settings.GSE_ENABLE_PUSH_ENVIRON_FILE else None,
            agent_manager.install_plugins() if self.is_install_latest_plugins else None,
        ]

        return list(filter(None, activities)), None


class UpgradeAgent(ReinstallAgent):
    """
    升级Agent，仅适用于 1.x 升级到 1.x 或 2.x 升级到 2.x ，不支持 1.x 升级到 2.x 的场景
    1.x 升级到 2.x 到场景，使用 InstallAgent2 覆盖安装
    TODO 2.x 升级到 2.x 的场景暂时沿用替换二进制后 reload 的方案，待 GSE 提供自升级方案后再调整
    """

    ACTION_NAME = backend_const.ActionNameType.UPGRADE_AGENT
    ACTION_DESCRIPTION = _("升级")

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.push_upgrade_package(),
            agent_manager.render_and_push_gse_config(),
            agent_manager.run_upgrade_command(),
            agent_manager.wait(30),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING),
            agent_manager.check_agent_ability(),
        ]
        return activities, None


class RestartAgent(AgentAction):
    """
    重启Agent
    """

    ACTION_NAME = backend_const.ActionNameType.RESTART_AGENT
    ACTION_DESCRIPTION = _("重启")

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.restart(skip_polling_result=True),
            agent_manager.wait(5),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING),
            agent_manager.check_agent_ability(),
        ]

        return activities, None


class RestartProxy(AgentAction):
    """
    重启Proxy
    """

    ACTION_NAME = backend_const.ActionNameType.RESTART_PROXY
    ACTION_DESCRIPTION = _("重启")

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.restart(skip_polling_result=True),
            # Proxy 重启后，需要等待一段时间才能正常工作, 需要等待 30s
            agent_manager.wait(30),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING, name=_("查询Proxy状态")),
            agent_manager.check_agent_ability(),
        ]
        return activities, None


class InstallProxy(AgentAction):
    """
    安装Proxy，与安装Agent流程一致
    """

    ACTION_NAME = backend_const.ActionNameType.INSTALL_PROXY
    ACTION_DESCRIPTION = _("安装")

    def _generate_activities(self, agent_manager: AgentManager):
        register_host = agent_manager.register_host()
        activities = [
            register_host,
            agent_manager.query_password(),
            agent_manager.configure_policy(),
            agent_manager.choose_ap(),
            agent_manager.install(),
            agent_manager.install_other_agent(
                extra_agent_version=GseVersion.V2.value,
                node_type=constants.NodeType.PROXY,
            )
            if all(
                [
                    not self.is_install_other_agent,
                    self.is_install_other_agent_v2,
                ]
            )
            else None,
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING, name=_("查询Proxy状态")),
            agent_manager.check_policy_gse_to_proxy(),
            agent_manager.push_host_identifier() if self.enable_push_host_identifier else None,
            agent_manager.push_environ_files() if settings.GSE_ENABLE_PUSH_ENVIRON_FILE else None,
        ]

        activities = self.append_push_file_activities(agent_manager, activities)
        activities.append(agent_manager.start_nginx())
        if self.is_install_latest_plugins:
            activities.append(agent_manager.install_plugins())

        return list(filter(None, activities)), None


class ReinstallProxy(AgentAction):
    """
    重装Proxy
    """

    ACTION_NAME = backend_const.ActionNameType.REINSTALL_PROXY
    ACTION_DESCRIPTION = _("重装")

    def _generate_activities(self, agent_manager: AgentManager):

        activities = [
            agent_manager.query_password(),
            agent_manager.configure_policy(),
            agent_manager.choose_ap(),
            agent_manager.install(),
            # 重装时由于初始 Proxy 的状态仍是RUNNING，这里等待30秒再重新查询
            agent_manager.wait(30),
            agent_manager.install_other_agent(
                extra_agent_version=GseVersion.V2.value,
                node_type=constants.NodeType.PROXY,
            )
            if all(
                [
                    not self.is_install_other_agent,
                    self.is_install_other_agent_v2,
                ]
            )
            else None,
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING, name=_("查询Proxy状态")),
            agent_manager.check_policy_gse_to_proxy(),
            agent_manager.push_host_identifier() if self.enable_push_host_identifier else None,
            agent_manager.push_environ_files() if settings.GSE_ENABLE_PUSH_ENVIRON_FILE else None,
        ]

        # 推送文件到proxy
        activities = self.append_push_file_activities(agent_manager, activities)
        activities.append(agent_manager.start_nginx())
        if self.is_install_latest_plugins:
            activities.append(agent_manager.install_plugins())

        return list(filter(None, activities)), None


class UpgradeProxy(ReinstallProxy):
    """
    升级Proxy
    """

    ACTION_NAME = backend_const.ActionNameType.UPGRADE_PROXY
    ACTION_DESCRIPTION = _("升级")

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.push_upgrade_package(),
            agent_manager.render_and_push_gse_config(),
            agent_manager.run_upgrade_command(),
            agent_manager.wait(30),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING),
            agent_manager.check_agent_ability(),
        ]

        # 推送文件到proxy
        if settings.BKAPP_ENABLE_DHCP:
            activities = self.append_push_file_activities(
                agent_manager, activities, files=constants.TOOLS_TO_PUSH_TO_PROXY
            )
        else:
            activities = self.append_push_file_activities(agent_manager, activities)
        activities.append(agent_manager.start_nginx())

        return activities, None


class ReplaceProxy(InstallProxy):
    """
    替换Proxy
    """

    ACTION_NAME = backend_const.ActionNameType.REPLACE_PROXY
    ACTION_DESCRIPTION = _("替换")


class UninstallAgent(AgentAction):
    """
    卸载Agent
    """

    ACTION_NAME = backend_const.ActionNameType.UNINSTALL_AGENT
    ACTION_DESCRIPTION = _("卸载")

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.query_password(),
            agent_manager.uninstall_agent(),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.UNKNOWN),
            agent_manager.update_process_status(status=constants.ProcStateType.NOT_INSTALLED),
        ]

        return list(filter(None, activities)), None


class UninstallProxy(AgentAction):
    """
    卸载Proxy
    """

    ACTION_NAME = backend_const.ActionNameType.UNINSTALL_PROXY
    ACTION_DESCRIPTION = _("卸载")

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.uninstall_proxy(),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.UNKNOWN, name=_("查询Proxy状态")),
            agent_manager.update_process_status(status=constants.ProcStateType.NOT_INSTALLED),
        ]

        return activities, None


class ReloadAgent(AgentAction):
    """
    重载Agent
    """

    ACTION_NAME = backend_const.ActionNameType.RELOAD_AGENT
    ACTION_DESCRIPTION = _("重载配置")

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.check_agent_status(),
            agent_manager.update_install_info(),
            agent_manager.render_and_push_gse_config(is_need_request_agent_version=True),
            agent_manager.reload_agent(skip_polling_result=True),
            agent_manager.wait(5),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING),
            agent_manager.check_agent_ability(),
            agent_manager.push_environ_files() if settings.GSE_ENABLE_PUSH_ENVIRON_FILE else None,
        ]
        return list(filter(None, activities)), None


class ReloadProxy(ReloadAgent):
    """
    重载proxy
    """

    ACTION_NAME = backend_const.ActionNameType.RELOAD_PROXY

    pass


class InstallAgent2(AgentAction):
    """安装新版本 Agent"""

    ACTION_NAME = backend_const.ActionNameType.INSTALL_AGENT_2
    ACTION_DESCRIPTION = _("安装")

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.add_or_update_hosts() if settings.BKAPP_ENABLE_DHCP else agent_manager.register_host(),
            agent_manager.query_password(),
            agent_manager.choose_ap(),
            agent_manager.push_agent_pkg_to_proxy() if self.has_non_lan_host() else None,
            agent_manager.install(),
            agent_manager.bind_host_agent(),
            agent_manager.upgrade_to_agent_id(),
            # 全业务文件分发依赖GSE 1.0 安装2.0时需要先安装1.0
            agent_manager.install_other_agent(extra_agent_version=GseVersion.V1.value)
            if all(
                [
                    not self.is_install_other_agent,
                    self.is_install_other_agent_v1,
                ]
            )
            else None,
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING),
            agent_manager.push_host_identifier() if self.enable_push_host_identifier else None,
            agent_manager.push_environ_files() if settings.GSE_ENABLE_PUSH_ENVIRON_FILE else None,
            agent_manager.install_plugins() if self.is_install_latest_plugins else None,
        ]
        return list(filter(None, activities)), None


class ReinstallAgent2(InstallAgent2):
    """重装新版本 Agent"""

    ACTION_NAME = backend_const.ActionNameType.REINSTALL_AGENT_2
    ACTION_DESCRIPTION = _("重装")

    def _generate_activities(self, agent_manager: AgentManager):
        activities, __ = super()._generate_activities(agent_manager)
        activities[0] = agent_manager.add_or_update_hosts() if settings.BKAPP_ENABLE_DHCP else None
        return list(filter(None, activities)), None


class InstallProxy2(AgentAction):
    """安装新版本 Proxy"""

    ACTION_NAME = backend_const.ActionNameType.INSTALL_PROXY_2
    ACTION_DESCRIPTION = _("安装")

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.add_or_update_hosts() if settings.BKAPP_ENABLE_DHCP else agent_manager.register_host(),
            agent_manager.query_password(),
            agent_manager.configure_policy(),
            agent_manager.choose_ap(),
            agent_manager.install(),
            agent_manager.bind_host_agent(),
            agent_manager.upgrade_to_agent_id(),
            # 全业务文件分发依赖GSE 1.0 安装2.0时需要先安装1.0
            agent_manager.install_other_agent(
                extra_agent_version=GseVersion.V1.value, node_type=constants.NodeType.PROXY
            )
            if all([not self.is_install_other_agent, self.is_install_other_agent_v1])
            else None,
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING, name=_("查询Proxy状态")),
            agent_manager.check_policy_gse_to_proxy(),
        ]

        activities = self.append_push_file_activities(agent_manager, activities, files=constants.TOOLS_TO_PUSH_TO_PROXY)
        activities.append(agent_manager.start_nginx())
        if self.enable_push_host_identifier:
            activities.append(agent_manager.push_host_identifier())
        if settings.GSE_ENABLE_PUSH_ENVIRON_FILE:
            activities.append(agent_manager.push_environ_files())
        if self.is_install_latest_plugins:
            activities.append(agent_manager.install_plugins())

        return list(filter(None, activities)), None


class ReinstallProxy2(InstallProxy2):
    """重装新版本 Proxy"""

    ACTION_NAME = backend_const.ActionNameType.REINSTALL_PROXY_2
    ACTION_DESCRIPTION = _("重装")

    def _generate_activities(self, agent_manager: AgentManager):
        activities, __ = super()._generate_activities(agent_manager)
        activities[0] = None
        return list(filter(None, activities)), None


class ActivateAgent(AgentAction):
    ACTION_NAME = backend_const.ActionNameType.ACTIVATE_AGENT
    ACTION_DESCRIPTION = _("切换配置")

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [agent_manager.push_environ_files()]
        return activities, None
