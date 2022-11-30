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
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from django.conf import settings
from django.utils.translation import ugettext as _

from apps.backend import constants as backend_const
from apps.backend.agent.manager import AgentManager
from apps.backend.subscription.steps.agent_adapter.adapter import AgentStepAdapter
from apps.node_man import constants, models
from apps.node_man.models import GsePluginDesc, SubscriptionStep
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

    # Agent Step 适配器
    agent_step_adapter: Optional[AgentStepAdapter] = None

    def __init__(self, subscription_step: SubscriptionStep):
        self.agent_step_adapter = AgentStepAdapter(subscription_step)
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
        if (
            self.agent_step_adapter.config["job_type"]
            not in [
                backend_const.ActionNameType.INSTALL_AGENT,
                backend_const.ActionNameType.REINSTALL_AGENT,
                backend_const.ActionNameType.UPGRADE_AGENT,
                backend_const.ActionNameType.INSTALL_PROXY,
                backend_const.ActionNameType.REINSTALL_PROXY,
                backend_const.ActionNameType.UPGRADE_PROXY,
            ]
            or self.agent_step_adapter.is_legacy
        ):
            # 如果非安装类操作或者操作的是旧版本的 Agent，无需计算变更
            instance_actions = {instance_id: self.subscription_step.config["job_type"] for instance_id in instances}
            return {"instance_actions": instance_actions, "migrate_reasons": {}}

        bk_host_ids: Set[int] = set()
        for instance_id, instance in instances.items():
            bk_host_id: Optional[int] = instance["host"].get("bk_host_id")
            # 新装场景 Agent 不存在
            if bk_host_id is None:
                continue
            bk_host_ids.add(instance["host"]["bk_host_id"])

        host_id__host_map: Dict[int, models.Host] = {
            host.bk_host_id: host for host in models.Host.objects.filter(bk_host_id__in=bk_host_ids)
        }
        proc_status_infos = models.ProcessStatus.objects.filter(
            name=models.ProcessStatus.GSE_AGENT_PROCESS_NAME,
            bk_host_id__in=bk_host_ids,
            source_type=models.ProcessStatus.SourceType.DEFAULT,
        ).values("bk_host_id", "id", "status")
        host_id__proc_status_info_map: Dict[int, Dict[str, Any]] = {
            proc_status_info["bk_host_id"]: proc_status_info for proc_status_info in proc_status_infos
        }

        instance_actions: Dict[str, str] = {}
        migrate_reasons: Dict[str, Dict[str, Any]] = {}
        # 新版本 Agent 操作映射关系
        # TODO 实际的任务类型和 migrate_type 相关，后续仍需按场景调整
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
            bk_host_id: Optional[int] = instance["host"].get("bk_host_id")
            host_obj: Optional[models.Host] = host_id__host_map.get(bk_host_id)
            if not host_obj:
                instance_actions[instance_id] = job_type_map[self.subscription_step.config["job_type"]]
                migrate_reasons[instance_id] = {"migrate_type": backend_const.AgentMigrateType.NEW_INSTALL.value}
            elif host_obj.bk_agent_id:
                # AgentID 已存在，视为新版本 Agent 重装
                instance_actions[instance_id] = job_type_map[self.subscription_step.config["job_type"]]
                migrate_reasons[instance_id] = {"migrate_type": backend_const.AgentMigrateType.REINSTALL.value}
            else:
                proc_status_info: Dict[str, Any] = host_id__proc_status_info_map.get(bk_host_id) or {}
                version_str_or_none: Optional[str] = proc_status_info.get("version")
                if version_str_or_none:
                    # AgentID 不存在并且版本存在，说明旧版本 Agent 存在，视为跨版本安装
                    instance_actions[instance_id] = job_type_map[self.subscription_step.config["job_type"]]
                    migrate_reasons[instance_id] = {
                        "migrate_type": backend_const.AgentMigrateType.CROSS_VERSION_INSTALL.value,
                        "version": version_str_or_none,
                    }
                else:
                    # 版本不存在，视为新装
                    instance_actions[instance_id] = job_type_map[self.subscription_step.config["job_type"]]
                    migrate_reasons[instance_id] = {"migrate_type": backend_const.AgentMigrateType.NEW_INSTALL.value}

        return {"instance_actions": instance_actions, "migrate_reasons": migrate_reasons}

    def bulk_create_host_status_cache(self, *args, **kwargs):
        """
        todo 此函数作占位用防止重试功能报错暂无具体功能
        :return:
        """
        pass


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

    def generate_activities(
        self,
        subscription_instances: List[models.SubscriptionInstanceRecord],
        global_pipeline_data: builder.Data,
        current_activities=None,
    ) -> Tuple[List[Union[builder.ServiceActivity, Element]], Optional[builder.Data]]:
        agent_manager = self.get_agent_manager(subscription_instances)
        activities, pipeline_data = self._generate_activities(agent_manager)
        for act in activities:
            act.component.inputs.subscription_step_id = Var(type=Var.PLAIN, value=self.step.subscription_step.id)
        self.inject_vars_to_global_data(global_pipeline_data)
        return activities, pipeline_data

    def append_delegate_activities(self, agent_manager, activities):
        for plugin in self.step.auto_launch_plugins:
            activities.append(agent_manager.delegate_plugin(plugin.name))
        return activities

    @staticmethod
    def append_push_file_activities(agent_manager, activities):
        for file in constants.FILES_TO_PUSH_TO_PROXY:
            activities.append(agent_manager.push_files_to_proxy(file))
        return activities


class InstallAgent(AgentAction):
    """
    安装Agent
    """

    ACTION_NAME = backend_const.ActionNameType.INSTALL_AGENT
    ACTION_DESCRIPTION = "安装"

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.add_or_update_hosts() if settings.BKAPP_ENABLE_DHCP else agent_manager.register_host(),
            agent_manager.query_password(),
            agent_manager.choose_ap(),
            agent_manager.install(),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING),
            agent_manager.push_host_identifier() if self.enable_push_host_identifier else None,
            agent_manager.install_plugins() if self.is_install_latest_plugins else None,
        ]

        return list(filter(None, activities)), None


class ReinstallAgent(AgentAction):
    """
    重装Agent
    """

    ACTION_NAME = backend_const.ActionNameType.REINSTALL_AGENT
    ACTION_DESCRIPTION = "重装"

    def _generate_activities(self, agent_manager: AgentManager):

        activities = [
            agent_manager.add_or_update_hosts() if settings.BKAPP_ENABLE_DHCP else None,
            agent_manager.query_password(),
            agent_manager.choose_ap(),
            agent_manager.install(),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING),
            agent_manager.push_host_identifier() if self.enable_push_host_identifier else None,
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
    ACTION_DESCRIPTION = "升级"

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.push_upgrade_package(),
            agent_manager.run_upgrade_command(),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING),
        ]
        return activities, None


class RestartAgent(AgentAction):
    """
    重启Agent
    """

    ACTION_NAME = backend_const.ActionNameType.RESTART_AGENT
    ACTION_DESCRIPTION = "重启"

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.restart(skip_polling_result=True),
            agent_manager.wait(5),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING),
        ]

        return activities, None


class RestartProxy(AgentAction):
    """
    重启Proxy
    """

    ACTION_NAME = backend_const.ActionNameType.RESTART_PROXY
    ACTION_DESCRIPTION = "重启"

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.restart(skip_polling_result=True),
            agent_manager.wait(5),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING, name=_("查询Proxy状态")),
        ]
        return activities, None


class InstallProxy(AgentAction):
    """
    安装Proxy，与安装Agent流程一致
    """

    ACTION_NAME = backend_const.ActionNameType.INSTALL_PROXY
    ACTION_DESCRIPTION = "安装"

    def _generate_activities(self, agent_manager: AgentManager):
        register_host = agent_manager.register_host()
        activities = [
            register_host,
            agent_manager.query_password(),
            agent_manager.configure_policy(),
            agent_manager.choose_ap(),
            agent_manager.install(),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING, name=_("查询Proxy状态")),
            agent_manager.check_policy_gse_to_proxy(),
            agent_manager.push_host_identifier() if self.enable_push_host_identifier else None,
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
    ACTION_DESCRIPTION = "重装"

    def _generate_activities(self, agent_manager: AgentManager):

        activities = [
            agent_manager.query_password(),
            agent_manager.configure_policy(),
            agent_manager.choose_ap(),
            agent_manager.install(),
            # 重装时由于初始 Proxy 的状态仍是RUNNING，这里等待30秒再重新查询
            agent_manager.wait(30),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING, name=_("查询Proxy状态")),
            agent_manager.check_policy_gse_to_proxy(),
            agent_manager.push_host_identifier() if self.enable_push_host_identifier else None,
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
    ACTION_DESCRIPTION = "升级"

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.push_upgrade_package(),
            agent_manager.run_upgrade_command(),
            agent_manager.wait(30),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING),
        ]

        # 推送文件到proxy
        activities = self.append_push_file_activities(agent_manager, activities)
        activities.append(agent_manager.start_nginx())

        return activities, None


class ReplaceProxy(InstallProxy):
    """
    替换Proxy
    """

    ACTION_NAME = backend_const.ActionNameType.REPLACE_PROXY
    ACTION_DESCRIPTION = "替换"


class UninstallAgent(AgentAction):
    """
    卸载Agent
    """

    ACTION_NAME = backend_const.ActionNameType.UNINSTALL_AGENT
    ACTION_DESCRIPTION = "卸载"

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
    ACTION_DESCRIPTION = "卸载"

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
    ACTION_DESCRIPTION = "重载配置"

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.check_agent_status(),
            agent_manager.update_install_info(),
            agent_manager.render_and_push_gse_config(),
            agent_manager.reload_agent(skip_polling_result=True),
            agent_manager.wait(5),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING),
        ]
        return activities, None


class ReloadProxy(ReloadAgent):
    """
    重载proxy
    """

    ACTION_NAME = backend_const.ActionNameType.RELOAD_PROXY
    ACTION_DESCRIPTION = "重载配置"


class InstallAgent2(AgentAction):
    """安装新版本 Agent"""

    ACTION_NAME = backend_const.ActionNameType.INSTALL_AGENT_2
    ACTION_DESCRIPTION = _("安装")

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.add_or_update_hosts() if settings.BKAPP_ENABLE_DHCP else agent_manager.register_host(),
            agent_manager.query_password(),
            agent_manager.choose_ap(),
            agent_manager.install(),
            agent_manager.bind_host_agent(),
            agent_manager.upgrade_to_agent_id(),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING),
            agent_manager.push_host_identifier() if self.enable_push_host_identifier else None,
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
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING, name=_("查询Proxy状态")),
            agent_manager.check_policy_gse_to_proxy(),
        ]

        activities = self.append_push_file_activities(agent_manager, activities)
        activities.append(agent_manager.start_nginx())
        if self.enable_push_host_identifier:
            activities.append(agent_manager.push_host_identifier())
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
