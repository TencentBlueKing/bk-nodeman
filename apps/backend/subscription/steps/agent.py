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

import abc
from functools import reduce
from typing import List, Tuple

from django.conf import settings
from django.utils.translation import ugettext as _

from apps.backend import constants as backend_const
from apps.backend.agent.manager import AgentManager
from apps.node_man import constants, models
from apps.node_man.constants import ProcStateType
from apps.node_man.models import GsePluginDesc, Host, SubscriptionStep
from pipeline import builder
from pipeline.builder import Data, NodeOutput, Var

# 需分发到 PROXY 的文件（由于放到一次任务中会给用户等待过久的体验，因此拆分成多次任务）
from ...components.collections.agent import RegisterHostComponent
from ...plugin.manager import PluginServiceActivity
from .base import Action, Step


class AgentStep(Step):
    STEP_TYPE = "AGENT"

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
        instance_actions = {instance_id: self.subscription_step.config["job_type"] for instance_id in instances}
        return {"instance_actions": instance_actions, "migrate_reasons": {}}

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

    def __init__(self, action_name, step: Step, instance_record_ids: List[int]):
        """
        :param Step step: 步骤实例
        :param models.SubscriptionInstanceRecord instance_record_ids: 订阅实例执行记录
        """
        self.step = step
        super().__init__(action_name, step, instance_record_ids)

    def get_agent_manager(self, subscription_instances: List[models.SubscriptionInstanceRecord]):
        """
        根据主机生成Agent管理器
        """
        subscription_instance_ids = [sub_inst.id for sub_inst in subscription_instances]
        return AgentManager(subscription_instance_ids, self.step)

        # agent_manager = AgentManager(
        #     instance_record=instance_record,
        #     creator=self.step.subscription.creator,
        #     blueking_language=self.step.subscription_step.params.get("blueking_language"),
        # )
        # return agent_manager

    def generate_pipeline(self, agent_manager):
        """
        :param PluginManager agent_manager:
        :return builder.SubProcess
        """
        start_event = builder.EmptyStartEvent()
        end_event = builder.EmptyEndEvent()

        activities, pipeline_data = self.generate_activities(agent_manager)
        pipeline_data.inputs["${description}"] = Var(type=Var.PLAIN, value=self.ACTION_DESCRIPTION)

        activities.insert(0, start_event)
        need_register = False
        for activity in activities:
            if getattr(getattr(activity, "component", None), "code", "") == RegisterHostComponent.code:
                # 需要注册主机得到bk_host_id后才能插入update_job_status
                need_register = True
        if need_register:
            activities.insert(2, agent_manager.update_job_status())
        else:
            activities.insert(1, agent_manager.update_job_status())
        activities.append(agent_manager.update_job_status())
        activities.append(end_event)

        # activity 编排
        reduce(lambda l, r: l.extend(r), [act for act in activities if act])

        sub_process = builder.SubProcess(
            start=start_event,
            name="[{}] {} {}:{}".format(
                self.ACTION_NAME,
                self.ACTION_DESCRIPTION,
                agent_manager.host_info["bk_cloud_id"],
                agent_manager.host_info["bk_host_innerip"],
            ),
            data=pipeline_data,
        )
        return sub_process

    @abc.abstractmethod
    def _generate_activities(self, agent_manager):
        pass

    def generate_activities(
        self, subscription_instances: List[models.SubscriptionInstanceRecord], current_activities=None
    ) -> Tuple[List[PluginServiceActivity], Data]:
        agent_manager = self.get_agent_manager(subscription_instances)
        return self._generate_activities(agent_manager)

    def append_delegate_activities(self, agent_manager, activities):
        for plugin in self.step.auto_launch_plugins:
            activities.append(agent_manager.delegate_plugin(plugin.name))
        return activities

    @staticmethod
    def append_push_file_activities(agent_manager, activities):
        for file in constants.FILES_TO_PUSH_TO_PROXY:
            activities.append(agent_manager.push_files_to_proxy(file))
        return activities

    def execute(self, instance_record):
        agent_manager = self.get_agent_manager(instance_record)
        return self.generate_pipeline(agent_manager)


class InstallAgent(AgentAction):
    """
    安装Agent
    """

    ACTION_NAME = backend_const.ActionNameType.INSTALL_AGENT
    ACTION_DESCRIPTION = "安装"

    def _generate_activities(self, agent_manager: AgentManager):
        register_host = agent_manager.register_host()

        if agent_manager.host_info["is_manual"]:
            self.ACTION_DESCRIPTION = "手动安装"
            install_name = _("手动安装")
        else:
            install_name = _("安装")

        activities = [
            register_host,
            agent_manager.choose_ap(),
            agent_manager.install(install_name),
            agent_manager.get_agent_status(expect_status=ProcStateType.RUNNING),
        ]

        # 把注册 CMDB 得到的bk_host_id 作为输出给到后续节点使用
        pipeline_data = Data()
        pipeline_data.inputs["${bk_host_id}"] = NodeOutput(
            source_act=register_host.id,
            source_key="bk_host_id",
            type=Var.SPLICE,
            value="",
        )
        pipeline_data.inputs["${is_manual}"] = NodeOutput(
            source_act=register_host.id,
            source_key="is_manual",
            type=Var.SPLICE,
            value=False,
        )

        # 验证类型为TJJ需要查询密码增加在第一步
        if agent_manager.host_info["auth_type"] == constants.AuthType.TJJ_PASSWORD:
            activities.insert(1, agent_manager.query_tjj_password())

        activities = self.append_delegate_activities(agent_manager, activities)

        return activities, pipeline_data


class ReinstallAgent(AgentAction):
    """
    重装Agent
    """

    ACTION_NAME = backend_const.ActionNameType.REINSTALL_AGENT
    ACTION_DESCRIPTION = "重装"

    def _generate_activities(self, agent_manager: AgentManager):

        # is_manual = Host.objects.get(bk_host_id=agent_manager.host_info["bk_host_id"]).is_manual
        # if is_manual:
        #     install_name = _("手动安装")
        # else:
        #     install_name = _("安装")

        activities = [
            agent_manager.choose_ap(),
            # agent_manager.install(install_name),
            # agent_manager.get_agent_status(expect_status=ProcStateType.RUNNING),
        ]

        # 上云增加查询密码原子
        # if settings.USE_TJJ:
        #     activities.insert(0, agent_manager.query_tjj_password())

        pipeline_data = Data()
        # pipeline_data.inputs["${bk_host_id}"] = Var(type=Var.PLAIN, value=agent_manager.host_info["bk_host_id"])

        # activities = self.append_delegate_activities(agent_manager, activities)

        return activities, pipeline_data


class UpgradeAgent(ReinstallAgent):
    """
    升级Agent
    """

    ACTION_NAME = backend_const.ActionNameType.UPGRADE_AGENT
    ACTION_DESCRIPTION = "升级"

    def _generate_activities(self, agent_manager: AgentManager):
        push_upgrade_package = agent_manager.bulk_push_upgrade_package_redis()
        activities = [
            push_upgrade_package,
            agent_manager.run_upgrade_command(),
            agent_manager.get_agent_status(expect_status=ProcStateType.RUNNING),
        ]

        pipeline_data = Data()
        pipeline_data.inputs["${package_name}"] = NodeOutput(
            source_act=push_upgrade_package.id,
            source_key="package_name",
            type=Var.SPLICE,
            value="",
        )
        pipeline_data.inputs["${bk_host_id}"] = Var(type=Var.PLAIN, value=agent_manager.host_info["bk_host_id"])

        return activities, pipeline_data


class RestartAgent(AgentAction):
    """
    重启Agent
    """

    ACTION_NAME = backend_const.ActionNameType.RESTART_AGENT
    ACTION_DESCRIPTION = "重启"

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.restart(),
            agent_manager.get_agent_status(expect_status=ProcStateType.RUNNING),
        ]

        pipeline_data = Data()
        pipeline_data.inputs["${bk_host_id}"] = Var(type=Var.PLAIN, value=agent_manager.host_info["bk_host_id"])

        return activities, pipeline_data


class RestartProxy(AgentAction):
    """
    重启Proxy
    """

    ACTION_NAME = backend_const.ActionNameType.RESTART_PROXY
    ACTION_DESCRIPTION = "重启"

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.restart(),
            agent_manager.get_agent_status(expect_status=ProcStateType.RUNNING, name=_("查询Proxy状态")),
        ]

        pipeline_data = Data()
        pipeline_data.inputs["${bk_host_id}"] = Var(type=Var.PLAIN, value=agent_manager.host_info["bk_host_id"])

        return activities, pipeline_data


class InstallProxy(AgentAction):
    """
    安装Proxy，与安装Agent流程一致
    """

    ACTION_NAME = backend_const.ActionNameType.INSTALL_PROXY
    ACTION_DESCRIPTION = "安装"

    def _generate_activities(self, agent_manager: AgentManager):
        register_host = agent_manager.register_host()
        if agent_manager.host_info["is_manual"]:
            self.ACTION_DESCRIPTION = "手动安装"
            install_name = _("手动安装")
        else:
            install_name = _("安装")

        activities = [
            register_host,
            agent_manager.query_tjj_password() if settings.USE_TJJ else None,
            agent_manager.configure_policy_by_sops() if settings.CONFIG_POLICY_BY_SOPS else None,
            agent_manager.configure_policy() if settings.CONFIG_POLICY_BY_TENCENT_VPC else None,
            agent_manager.choose_ap(),
            agent_manager.install(install_name),
            agent_manager.get_agent_status(expect_status=ProcStateType.RUNNING, name=_("查询Proxy状态")),
            # agent_manager.check_policy_gse_to_proxy(),
        ]

        activities = self.append_push_file_activities(agent_manager, activities)
        activities.append(agent_manager.start_nginx())

        # 把注册 CMDB 得到的bk_host_id 作为输出给到后续节点使用
        pipeline_data = Data()
        pipeline_data.inputs["${bk_host_id}"] = NodeOutput(
            source_act=register_host.id,
            source_key="bk_host_id",
            type=Var.SPLICE,
            value="",
        )
        pipeline_data.inputs["${is_manual}"] = NodeOutput(
            source_act=register_host.id,
            source_key="is_manual",
            type=Var.SPLICE,
            value=False,
        )

        activities = self.append_delegate_activities(agent_manager, activities)

        return activities, pipeline_data


class ReinstallProxy(AgentAction):
    """
    重装Proxy
    """

    ACTION_NAME = backend_const.ActionNameType.REINSTALL_PROXY
    ACTION_DESCRIPTION = "重装"

    def _generate_activities(self, agent_manager: AgentManager):

        is_manual = Host.objects.get(bk_host_id=agent_manager.host_info["bk_host_id"]).is_manual
        if is_manual:
            install_name = _("手动安装")
        else:
            install_name = _("安装")

        activities = [
            agent_manager.query_tjj_password() if settings.USE_TJJ else None,
            agent_manager.configure_policy_by_sops() if settings.CONFIG_POLICY_BY_SOPS else None,
            agent_manager.configure_policy() if settings.CONFIG_POLICY_BY_TENCENT_VPC else None,
            agent_manager.choose_ap(),
            agent_manager.install(install_name),
            agent_manager.wait(30),  # 重装时由于初始 Proxy 的状态仍是RUNNING，这里等待30秒再重新查询
            agent_manager.get_agent_status(expect_status=ProcStateType.RUNNING, name=_("查询Proxy状态")),
            # agent_manager.check_policy_gse_to_proxy(),
        ]

        activities = self.append_delegate_activities(agent_manager, activities)

        # 推送文件到proxy
        activities = self.append_push_file_activities(agent_manager, activities)
        activities.append(agent_manager.start_nginx())

        pipeline_data = Data()
        pipeline_data.inputs["${bk_host_id}"] = Var(type=Var.PLAIN, value=agent_manager.host_info["bk_host_id"])
        pipeline_data.inputs["${is_manual}"] = Var(type=Var.PLAIN, value=is_manual)

        return activities, pipeline_data


class UpgradeProxy(ReinstallProxy):
    """
    升级Proxy
    """

    ACTION_NAME = backend_const.ActionNameType.UPGRADE_PROXY
    ACTION_DESCRIPTION = "升级"

    def _generate_activities(self, agent_manager: AgentManager):
        push_upgrade_package = agent_manager.bulk_push_upgrade_package_redis()
        activities = [
            push_upgrade_package,
            agent_manager.run_upgrade_command(),
            agent_manager.wait(30),
            agent_manager.get_agent_status(expect_status=ProcStateType.RUNNING),
        ]

        # 推送文件到proxy
        activities = self.append_push_file_activities(agent_manager, activities)
        activities.append(agent_manager.start_nginx())

        pipeline_data = Data()
        pipeline_data.inputs["${package_name}"] = NodeOutput(
            source_act=push_upgrade_package.id,
            source_key="package_name",
            type=Var.SPLICE,
            value="",
        )
        pipeline_data.inputs["${bk_host_id}"] = Var(type=Var.PLAIN, value=agent_manager.host_info["bk_host_id"])

        return activities, pipeline_data


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
            agent_manager.query_tjj_password() if settings.USE_TJJ else None,
            agent_manager.uninstall_agent(),
            agent_manager.get_agent_status(expect_status=ProcStateType.UNKNOWN),
            agent_manager.update_process_status(status=ProcStateType.NOT_INSTALLED),
        ]

        pipeline_data = Data()
        pipeline_data.inputs["${bk_host_id}"] = Var(type=Var.PLAIN, value=agent_manager.host_info["bk_host_id"])

        return activities, pipeline_data


class UninstallProxy(AgentAction):
    """
    卸载Proxy
    """

    ACTION_NAME = backend_const.ActionNameType.UNINSTALL_PROXY
    ACTION_DESCRIPTION = "卸载"

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.uninstall_proxy(),
            agent_manager.get_agent_status(expect_status=ProcStateType.UNKNOWN, name=_("查询Proxy状态")),
            agent_manager.update_process_status(status=ProcStateType.NOT_INSTALLED),
        ]

        pipeline_data = Data()
        pipeline_data.inputs["${bk_host_id}"] = Var(type=Var.PLAIN, value=agent_manager.host_info["bk_host_id"])

        return activities, pipeline_data


class ReloadAgent(AgentAction):
    """
    重载Agent
    """

    ACTION_NAME = backend_const.ActionNameType.RELOAD_AGENT
    ACTION_DESCRIPTION = "重载配置"

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.check_agent_status(),
            agent_manager.render_and_push_gse_config(),
        ]

        os_type = constants.OS_TYPE.get(agent_manager.host_info.get("bk_os_type"))
        if os_type != constants.OsType.WINDOWS:
            activities.append(agent_manager.reload_agent())
        else:
            activities.append(agent_manager.restart()),
            activities.append(agent_manager.get_agent_status(expect_status=ProcStateType.RUNNING)),

        pipeline_data = Data()
        pipeline_data.inputs["${bk_host_id}"] = Var(type=Var.PLAIN, value=agent_manager.host_info["bk_host_id"])

        return activities, pipeline_data


class ReloadProxy(ReloadAgent):
    """
    重载proxy
    """

    ACTION_NAME = backend_const.ActionNameType.RELOAD_PROXY
    ACTION_DESCRIPTION = "重载配置"
