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
from abc import ABC
from collections import ChainMap, defaultdict
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import six
from django.db.models import QuerySet
from django.utils.translation import ugettext_lazy as _

from apps.adapters.api.gse import get_gse_api_helper
from apps.backend import constants as backend_const
from apps.backend.components.collections import plugin
from apps.backend.plugin.manager import PluginManager, PluginServiceActivity
from apps.backend.subscription import errors, tools
from apps.backend.subscription.constants import MAX_RETRY_TIME
from apps.backend.subscription.steps import adapter
from apps.backend.subscription.steps.base import Action, Step
from apps.core.tag import targets
from apps.core.tag.models import Tag
from apps.node_man import constants, models
from apps.node_man.exceptions import ApIDNotExistsError
from apps.utils import concurrent
from common.log import logger
from pipeline.builder import Data, Var


class PluginStep(Step):
    STEP_TYPE = "PLUGIN"

    # 进程配置缓存，用于 get_all_subscription_steps_context
    group_id_host_id__last_proc_status_map: Dict[str, Dict[str, Any]] = None

    def __init__(self, subscription_step: models.SubscriptionStep):

        super(PluginStep, self).__init__(subscription_step)

        # 配置数据校验
        self.policy_step_adapter = adapter.PolicyStepAdapter(subscription_step)

        validated_params = self.policy_step_adapter.params

        # 获取插件配置模板信息

        # TODO 待修改，此处port_range需要os_cpu_arch
        self.port_range: Optional[str] = validated_params.get("port_range")

        self.check_and_skip: bool = self.policy_step_adapter.config["check_and_skip"]
        self.is_version_sensitive: bool = self.policy_step_adapter.config["is_version_sensitive"]

        # 更新插件包时的可选项  -- TODO
        self.keep_config: str = ""
        self.no_restart: str = ""

        self.plugin_name: str = self.policy_step_adapter.plugin_name
        self.plugin_desc: models.GsePluginDesc = self.policy_step_adapter.plugin_desc
        self.os_key_pkg_map: Dict[str, models.Packages] = self.policy_step_adapter.os_key_pkg_map
        self.config_tmpl_gby_os_key: Dict[
            str, List[models.PluginConfigTemplate]
        ] = self.policy_step_adapter.config_tmpl_obj_gby_os_key

        self.target_hosts: List[Dict[str, Any]] = subscription_step.subscription.target_hosts

        self.process_cache = defaultdict(dict)

        self.group_id_host_id__last_proc_status_map: Dict[str, Dict[str, Any]] = {}
        # 初次部署预览时订阅 ID 为空 或 -1，此时不会执行配置对比，无需进行查询
        if self.subscription.id not in [-1, None]:
            # 1. 原逻辑是查询 source_id & bk_host_id 最后一个 proc_status
            # 2. 通过 is_latest 查询所得数据是 1. 提及范围的子集，目的是避免主机下存在 proc_status 数据过多
            # 3. 兜底，get_step_data 在 get 不到数据时会捞 DB
            proc_status_infos = models.ProcessStatus.objects.filter(
                name=self.plugin_name,
                source_id=self.subscription.id,
                proc_type=constants.ProcType.PLUGIN,
                is_latest=True,
            ).values(
                "bk_host_id", "group_id", "listen_ip", "listen_port", "setup_path", "log_path", "data_path", "pid_path"
            )
            for proc_status_info in proc_status_infos:
                self.group_id_host_id__last_proc_status_map[
                    f"{proc_status_info['group_id']}-{proc_status_info['bk_host_id']}"
                ] = proc_status_info

        self.tag_name__obj_map: Dict[str, Tag] = targets.PluginTargetHelper.get_tag_name__obj_map(
            target_id=self.plugin_desc.id
        )

    def get_matching_package(self, os_type: str, cpu_arch: str) -> models.Packages:
        try:
            return self.os_key_pkg_map[adapter.PolicyStepAdapter.get_os_key(os_type, cpu_arch)]
        except KeyError:
            # 此处是为了延迟报错到订阅
            if self.os_key_pkg_map:
                return list(self.os_key_pkg_map.values())[0]
            raise errors.PluginValidationError(msg="插件 [{name}] 没有可供选择的插件包")

    def get_matching_pkg_real_version(self, os_type: str, cpu_arch: str) -> str:
        package: models.Packages = self.get_matching_package(os_type, cpu_arch)
        if package.version in self.tag_name__obj_map:
            return self.tag_name__obj_map[package.version].target_version
        else:
            return package.version

    def get_matching_config_templates(self, os_type: str, cpu_arch: str) -> List[models.PluginConfigTemplate]:
        return self.config_tmpl_gby_os_key.get(adapter.PolicyStepAdapter.get_os_key(os_type, cpu_arch), [])

    def get_supported_actions(self) -> Dict:
        actions = {
            backend_const.ActionNameType.MAIN_INSTALL_PLUGIN: MainInstallPlugin,
            backend_const.ActionNameType.MAIN_STOP_PLUGIN: MainStopPlugin,
            backend_const.ActionNameType.MAIN_START_PLUGIN: MainStartPlugin,
            backend_const.ActionNameType.MAIN_RESTART_PLUGIN: MainReStartPlugin,
            backend_const.ActionNameType.MAIN_RELOAD_PLUGIN: MainReloadPlugin,
            backend_const.ActionNameType.MAIN_DELEGATE_PLUGIN: MainDelegatePlugin,
            backend_const.ActionNameType.MAIN_UNDELEGATE_PLUGIN: MainUnDelegatePlugin,
            backend_const.ActionNameType.MAIN_STOP_AND_DELETE_PLUGIN: MainStopAndDeletePlugin,
            backend_const.ActionNameType.DEBUG_PLUGIN: DebugPlugin,
            backend_const.ActionNameType.STOP_DEBUG_PLUGIN: StopDebugPlugin,
        }
        if self.plugin_desc.is_official:
            # 官方插件是基于多配置的管理模式，安装、卸载、启用、停用等操作仅涉及到配置的增删
            actions.update(
                {
                    backend_const.ActionNameType.INSTALL: PushConfig,
                    backend_const.ActionNameType.UNINSTALL: RemoveConfig,
                    backend_const.ActionNameType.PUSH_CONFIG: PushConfig,
                    backend_const.ActionNameType.START: PushConfig,
                    backend_const.ActionNameType.STOP: RemoveConfig,
                }
            )
        else:
            actions.update(
                {
                    backend_const.ActionNameType.INSTALL: InstallPlugin,
                    backend_const.ActionNameType.UNINSTALL: UninstallPlugin,
                    backend_const.ActionNameType.PUSH_CONFIG: PushConfig,
                    backend_const.ActionNameType.START: StartPlugin,
                    backend_const.ActionNameType.STOP: StopPlugin,
                }
            )
        return actions

    def get_step_data(
        self, instance_info: Dict, target_host: models.Host, agent_config: Dict
    ) -> Dict[str, Dict[str, Any]]:
        """
        获取步骤上下文数据
        """
        group_id = tools.create_group_id(self.subscription, instance_info)
        proc_status_info = self.group_id_host_id__last_proc_status_map.get(f"{group_id}-{target_host.bk_host_id}")
        if not proc_status_info:
            filter_condition = dict(
                bk_host_id=target_host.bk_host_id,
                name=self.plugin_name,
                source_id=self.subscription.id,
                proc_type=constants.ProcType.PLUGIN,
                group_id=tools.create_group_id(self.subscription, instance_info),
            )
            proc_status_info = (
                models.ProcessStatus.objects.filter(**filter_condition)
                .values(
                    "bk_host_id",
                    "group_id",
                    "listen_ip",
                    "listen_port",
                    "setup_path",
                    "log_path",
                    "data_path",
                    "pid_path",
                )
                .last()
            )

        if not proc_status_info:
            return {}

        control_info = self.generate_plugin_control_info(proc_status_info, target_host, agent_config)
        return {"control_info": control_info}

    def generate_plugin_control_info(
        self, process_status_info: Dict[str, Any], host: models.Host, agent_config: Dict
    ) -> Dict[str, Any]:
        """
        生成插件控制信息
        """
        package = self.get_matching_package(host.os_type, host.cpu_arch)
        # 序列化器效率较低，直接通过getattr将模型转为字典
        proc_control = package.proc_control
        control_info_fields = {
            "id",
            "module",
            "project",
            "plugin_package_id",
            "install_path",
            "log_path",
            "data_path",
            "pid_path",
            "start_cmd",
            "stop_cmd",
            "restart_cmd",
            "reload_cmd",
            "kill_cmd",
            "version_cmd",
            "health_cmd",
            "debug_cmd",
            "os",
            "process_name",
            "port_range",
            "need_delegate",
        }
        control_info = {}
        for field in control_info_fields:
            control_info[field] = getattr(proc_control, field)

        control_info.update(
            gse_agent_home=agent_config["setup_path"],
            listen_ip=process_status_info["listen_ip"],
            listen_port=process_status_info["listen_port"],
            group_id=process_status_info["group_id"],
            setup_path=process_status_info["setup_path"],
            log_path=process_status_info["log_path"],
            data_path=process_status_info["data_path"],
            pid_path=process_status_info["pid_path"],
        )
        return control_info

    def check_config_change(
        self,
        instance_id: str,
        subscription_step: models.SubscriptionStep,
        instance_info: Dict,
        host_map: Dict,
        ap_id_obj_map: Dict,
        process_status_list: List[Dict[str, Any]],
        proc_status_id__configs_map: Dict[int, List[Dict]],
    ) -> Dict[str, Union[bool, str]]:
        """检测配置是否有变动"""
        try:
            for process_status in process_status_list:
                # 渲染新配置
                target_host = host_map[process_status["bk_host_id"]]
                ap = ap_id_obj_map.get(target_host.ap_id)
                if not ap:
                    raise ApIDNotExistsError()
                agent_config = ap.agent_config[target_host.os_type.lower()]
                context = tools.get_all_subscription_steps_context(
                    subscription_step,
                    instance_info,
                    target_host,
                    process_status["name"],
                    agent_config,
                    self.policy_step_adapter,
                )

                rendered_configs = tools.render_config_files_by_config_templates(
                    self.get_matching_config_templates(target_host.os_type, target_host.cpu_arch),
                    process_status,
                    context,
                    package_obj=self.get_matching_package(target_host.os_type, target_host.cpu_arch),
                    source="migrate",
                )

                old_rendered_configs = proc_status_id__configs_map[process_status["id"]]

                for new_config in rendered_configs:
                    for old_config in old_rendered_configs:
                        if new_config["name"] == old_config["name"] and new_config["md5"] == old_config["md5"]:
                            # 配置一致，开始下一次循环
                            break
                    else:
                        # 如果在老配置中找不到新配置，则必须重新下发
                        return {"instance_id": instance_id, "is_config_change": True}

        except Exception as e:

            logger.exception("检测配置文件变动失败：%s" % e)
            # 遇到异常也被认为有改动
            return {"instance_id": instance_id, "is_config_change": True}
        return {"instance_id": instance_id, "is_config_change": False}

    def check_version_change(self, host_map: Dict[int, models.Host], statuses: List[Dict[str, Any]]) -> Dict:
        """检查版本是否有变更，并返回当前版本及目标版本"""
        current_version = None
        target_version = None
        for status in statuses:
            host = host_map[status["bk_host_id"]]
            target_version = self.get_matching_pkg_real_version(host.os_type, host.cpu_arch)
            current_version = status["version"]
            if target_version != status["version"]:
                return {"has_change": True, "current_version": current_version, "target_version": target_version}
        return {"has_change": False, "current_version": current_version, "target_version": target_version}

    def handle_uninstall_instances(
        self,
        auto_trigger: bool,
        preview_only: bool,
        uninstall_action: str,
        instance_actions: Dict[str, str],
        uninstall_ids: List[int],
        push_migrate_reason_func: Callable,
    ):
        """处理要卸载的订阅实例"""
        if not uninstall_ids:
            return

        remove_from_scope_instance_ids = set()

        instance_key = "host" if self.subscription.object_type == models.Subscription.ObjectType.HOST else "service"
        id_key = "bk_host_id" if instance_key == "host" else "id"

        for _id in uninstall_ids:
            instance_id = tools.create_node_id(
                {
                    "object_type": self.subscription.object_type,
                    "node_type": self.subscription.NodeType.INSTANCE,
                    id_key: _id,
                }
            )
            remove_from_scope_instance_ids.add(instance_id)
            instance_actions[instance_id] = uninstall_action
            push_migrate_reason_func(
                _instance_id=instance_id, migrate_type=backend_const.PluginMigrateType.REMOVE_FROM_SCOPE
            )

        # 仅策略的巡检需要假移除插件
        if self.subscription.category == models.Subscription.CategoryType.POLICY and auto_trigger:
            for remove_from_scope_instance_id in remove_from_scope_instance_ids:
                instance_actions.pop(remove_from_scope_instance_id, None)
                # 添加标记，便于回溯
                push_migrate_reason_func(_instance_id=remove_from_scope_instance_id, only_remove_from_sub=True)
            # 仅预览情况下不执行操作
            if not preview_only:
                # 移除进程归属，但不执行删除，仅将 process status 中订阅相关的信息抹除
                # 被移除的记录如果is_latest=True，周期任务同步回插件最新状态，交由用户决定是否从机器中移除插件
                models.ProcessStatus.objects.filter(
                    source_id=self.subscription.id, name=self.plugin_name, bk_host_id__in=uninstall_ids
                ).update(source_id=None, group_id="", bk_obj_id=None)

        elif self.subscription.object_type == self.subscription.ObjectType.HOST:
            # 如果 Agent 状态异常，标记异常并且不执行变更，等到 Agent 状态恢复再执行卸载
            host_ids_with_alive_agent = models.ProcessStatus.objects.filter(
                name=models.ProcessStatus.GSE_AGENT_PROCESS_NAME,
                source_type=models.ProcessStatus.SourceType.DEFAULT,
                bk_host_id__in=uninstall_ids,
                status=constants.ProcStateType.RUNNING,
            ).values_list("bk_host_id", flat=True)

            host_ids_with_no_alive_agent = set(uninstall_ids) - set(host_ids_with_alive_agent)
            for host_id in host_ids_with_no_alive_agent:
                instance_id = tools.create_node_id(
                    {
                        "object_type": self.subscription.object_type,
                        "node_type": self.subscription.NodeType.INSTANCE,
                        id_key: host_id,
                    }
                )
                instance_actions.pop(instance_id, None)
                push_migrate_reason_func(
                    _instance_id=instance_id, migrate_type=backend_const.PluginMigrateType.ABNORMAL_AGENT_STATUS
                )

            if host_ids_with_no_alive_agent and not preview_only:
                models.ProcessStatus.objects.filter(
                    source_id=self.subscription.id, name=self.plugin_name, bk_host_id__in=host_ids_with_no_alive_agent
                ).update(status=constants.ProcStateType.AGENT_NO_ALIVE)
                logger.info(
                    f"[handle_uninstall_instances] set proc to AGENT_NO_ALIVE, subscription_id -> "
                    f"{self.subscription.id}, name -> {self.plugin_name}, host_ids -> {host_ids_with_no_alive_agent}",
                )

    def handle_new_add_instances(
        self,
        install_action: str,
        instances: Dict[str, Dict],
        instance_actions: Dict[str, str],
        bk_host_id__host_map: Dict[int, models.Host],
        group_id__host_key__proc_status_map: Dict[str, Dict[str, models.ProcessStatus]],
        push_migrate_reason_func: Callable,
    ):
        not_sync_instance_ids = set()
        for instance_id, instance in instances.items():
            group_id = tools.create_group_id(self.subscription, instance)
            if group_id in group_id__host_key__proc_status_map:
                continue
            # 如果是新的实例，则安装插件
            bk_host_id = instance["host"]["bk_host_id"]
            if bk_host_id not in bk_host_id__host_map:
                # 暂未同步的主机，跳过
                not_sync_instance_ids.add(instance_id)
                continue
            instance_actions[instance_id] = install_action
            # 新安装主机需要填充目标版本
            host = bk_host_id__host_map[instance["host"]["bk_host_id"]]
            push_migrate_reason_func(
                _instance_id=instance_id,
                migrate_type=backend_const.PluginMigrateType.NEW_INSTALL,
                target_version=self.get_matching_pkg_real_version(host.os_type, host.cpu_arch),
            )

        # 记录未同步主机
        for not_sync_instance_id in not_sync_instance_ids:
            push_migrate_reason_func(
                _instance_id=not_sync_instance_id, migrate_type=backend_const.PluginMigrateType.NOT_SYNC_HOST
            )

    def handle_exceed_max_retry_times_instances(
        self,
        instance_actions: Dict[str, str],
        max_retry_instance_ids: List[str],
        auto_trigger: bool,
        preview_only: bool,
        push_migrate_reason_func: Callable,
    ):
        # 自动触发时，重试次数大于 MAX_RETRY_TIME 的实例，不进行操作
        if auto_trigger:
            for instance_id in max_retry_instance_ids:
                instance_actions.pop(instance_id, None)
                push_migrate_reason_func(_instance_id=instance_id, exceed_max_retry_times=True)
            return

        # 仅预览情况下无需重置重试次数
        if preview_only:
            return
        # 非自动触发，把重试次数清零
        models.ProcessStatus.objects.filter(
            source_id=self.subscription_step.subscription_id,
            name=self.plugin_name,
        ).update(retry_times=0)

    def handle_manual_op_instances(
        self,
        instances: Dict[str, Dict],
        instance_actions: Dict[str, str],
        auto_trigger: bool,
        push_migrate_reason_func: Callable,
    ):
        """
        处理手动操作豁免的情况
        背景：策略自动巡检时，不自动拉起手动操作（目前仅针对手动停止）过的主机
        :param instances: 实例ID - 实例信息 映射关系
        :param instance_actions: 实例ID - 实例动作 映射关系
        :param auto_trigger: 是否为自动触发
        :param push_migrate_reason_func: 变更原因归档函数
        :return:
        """

        # 仅策略考虑豁免手动操作
        if self.subscription.category != models.Subscription.CategoryType.POLICY:
            return

        # 非自动触发，用户自动触发的情况下，不对手动操作（暂时仅考虑手动停止）的机器执行进行豁免
        if not auto_trigger:
            return

        action_host_ids = []
        host_id__instance_id_map = {}
        # 统计具有触发任务的主机ID，并建立 主机ID - 实例ID 的映射关系，用于后续从instance_actions排除手动操作主机
        for instance_id in instance_actions:
            instance = instances.get(instance_id)
            if not instance:
                continue
            action_host_ids.append(instance["host"]["bk_host_id"])
            host_id__instance_id_map[instance["host"]["bk_host_id"]] = instance_id

        # 查询具有最新手动操作记录的主机ID列表并去重
        manual_op_host_ids = set(
            models.ProcessStatus.objects.filter(
                name=self.plugin_name,
                bk_host_id__in=action_host_ids,
                status=constants.ProcStateType.MANUAL_STOP,
                is_latest=True,
            ).values_list("bk_host_id", flat=True)
        )
        # 对手动操作主机进行豁免，并归档变更原因
        for manual_op_host_id in manual_op_host_ids:
            instance_id = host_id__instance_id_map[manual_op_host_id]
            instance_actions.pop(instance_id, None)
            push_migrate_reason_func(
                _instance_id=instance_id, migrate_type=backend_const.PluginMigrateType.MANUAL_OP_EXEMPT
            )

    def handle_not_change_instances(
        self, instances: Dict[str, Dict], migrate_reasons: Dict[str, Dict], push_migrate_reason_func: Callable
    ):
        """
        处理无需变更实例，请在最后调用该钩子
        :param instances: 实例ID - 实例信息 映射关系，当前订阅范围的实际范围
        :param migrate_reasons: 实例ID - 变更原因 映射关系
        :param push_migrate_reason_func: 变更原因归档函数
        :return:
        """
        # 统计已归档变更原因的实例ID
        exist_migrate_type_instance_ids = set()
        for instance_id, migrate_reason in migrate_reasons.items():
            if "migrate_type" in migrate_reason:
                exist_migrate_type_instance_ids.add(instance_id)

        # 取当前订阅实际范围的差级，当其他情况处理后，认为还未归档变更原因的实例是无需变更的
        no_change_instance_ids = set(instances.keys()) - exist_migrate_type_instance_ids
        for instance_id in no_change_instance_ids:
            push_migrate_reason_func(_instance_id=instance_id, migrate_type=backend_const.PluginMigrateType.NOT_CHANGE)

    def handle_config_change_instances(
        self,
        auto_trigger: bool,
        instance_ids: List[str],
        push_config_action: str,
        instance_actions: Dict[str, str],
        push_migrate_reason_func: Callable,
        ap_id_obj_map: Dict[int, models.AccessPoint],
        bk_host_id__host_map: Dict[int, models.Host],
        instances: Dict[str, Dict[str, Union[Dict, Any]]],
        instance_id__proc_statuses_map: Dict[str, List[Dict[str, Any]]],
    ):
        """
        处理配置变更的情况
        :param auto_trigger: 是否为自动触发任务
        :param instance_ids: 需要处理配置变更的实例ID列表
        :param push_config_action: 配置变更动作
        :param instance_actions: 实例ID - 实例动作 映射关系
        :param push_migrate_reason_func: 变更原因归档函数
        :param ap_id_obj_map: 接入点 ID - 接入点对象映射关系
        :param bk_host_id__host_map: 主机 ID - 主机对象映射关系
        :param instances: 实例ID - 实例信息 映射关系，当前订阅范围的实际范围
        :param instance_id__proc_statuses_map: 实例ID - 进程实例信息映射
        :return:
        """
        bk_host_ids: List[int] = []
        for proc_statuses in instance_id__proc_statuses_map.values():
            bk_host_ids.extend([proc_status["bk_host_id"] for proc_status in proc_statuses])
        # 延迟查询配置
        # 配置变更作为一个可能发生的 case，要避免在上层将 JSON 数据查出，因为这部分数据对其他 case 而言是多余的
        proc_configs_list = (
            self.filter_related_process_statuses(auto_trigger=auto_trigger)
            .filter(bk_host_id__in=set(bk_host_ids))
            .values("id", "configs")
        )
        proc_status_id__configs_map: Dict[int, List[Dict]] = {
            proc_configs["id"]: proc_configs["configs"] for proc_configs in proc_configs_list
        }

        check_config_change_params_list: List[Dict] = []
        for instance_id in instance_ids:
            check_config_change_params_list.append(
                {
                    "instance_id": instance_id,
                    "subscription_step": self.subscription_step,
                    "instance_info": instances[instance_id],
                    "host_map": bk_host_id__host_map,
                    "ap_id_obj_map": ap_id_obj_map,
                    "process_status_list": instance_id__proc_statuses_map[instance_id],
                    "proc_status_id__configs_map": proc_status_id__configs_map,
                }
            )

        # 计算密集型任务，通过多线程并行加速
        check_results = concurrent.batch_call(
            func=self.check_config_change, params_list=check_config_change_params_list
        )

        for check_result in check_results:
            if not check_result["is_config_change"]:
                continue
            instance_actions[check_result["instance_id"]] = push_config_action
            push_migrate_reason_func(
                _instance_id=check_result["instance_id"], migrate_type=backend_const.PluginMigrateType.CONFIG_CHANGE
            )

    def handle_check_and_skip_instances(
        self,
        install_action: str,
        instance_actions: Dict[str, str],
        push_migrate_reason_func: Callable,
        bk_host_id__host_map: Dict[int, models.Host],
        instances: Dict[str, Dict[str, Union[Dict, Any]]],
    ):
        """
        插件状态及版本检查，确定是否执行安装
        :param install_action:
        :param instance_actions:
        :param push_migrate_reason_func:
        :param bk_host_id__host_map:
        :param instances:
        :return:
        """
        gse_version__host_info_list_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        host_id__instance_id_map: Dict[int, Dict] = {}
        gse_version__bk_host_id__host_map: Dict[str, Dict[int, models.Host]] = defaultdict(dict)
        for instance_id, instance in instances.items():
            bk_host_id = instance["host"].get("bk_host_id")
            # dict in 是近似 O(1) 的操作复杂度：https://stackoverflow.com/questions/17539367/
            if bk_host_id not in bk_host_id__host_map:
                # 忽略未同步主机
                continue
            host_obj = bk_host_id__host_map[bk_host_id]
            gse_version__host_info_list_map[instance["meta"]["GSE_VERSION"]].append(
                {
                    "ip": host_obj.inner_ip or host_obj.inner_ipv6,
                    "bk_cloud_id": host_obj.bk_cloud_id,
                    "bk_agent_id": host_obj.bk_agent_id,
                    "meta": instance["meta"],
                }
            )
            gse_version__bk_host_id__host_map[instance["meta"]["GSE_VERSION"]][bk_host_id] = host_obj
            host_id__instance_id_map[bk_host_id] = instance_id

        agent_id__readable_proc_status_map: Dict[str, Dict[str, Any]] = {}
        for gse_version, host_info_list in gse_version__host_info_list_map.items():
            gse_api_helper = get_gse_api_helper(gse_version)
            agent_id__readable_proc_status_map.update(
                gse_api_helper.list_proc_state(
                    namespace=constants.GSE_NAMESPACE,
                    proc_name=self.plugin_name,
                    labels={"proc_name": self.plugin_name},
                    host_info_list=host_info_list,
                    extra_meta_data={},
                )
            )

        logger.info(f"agent_id__readable_proc_status_map -> {agent_id__readable_proc_status_map}")

        for gse_version, _bk_host_id__host_map in gse_version__bk_host_id__host_map.items():
            gse_api_helper = get_gse_api_helper(gse_version)
            for bk_host_id, host_obj in _bk_host_id__host_map.items():
                agent_id: str = gse_api_helper.get_agent_id(host_obj)
                instance_id: str = host_id__instance_id_map[bk_host_id]
                proc_status: Optional[Dict[str, Any]] = agent_id__readable_proc_status_map.get(agent_id)
                if not proc_status:
                    # 查询不到进程状态信息视为插件状态异常
                    instance_actions[host_id__instance_id_map[bk_host_id]] = install_action
                    push_migrate_reason_func(
                        _instance_id=instance_id, migrate_type=backend_const.PluginMigrateType.ABNORMAL_PROC_STATUS
                    )
                    continue

                # 记录必要信息，便于溯源
                base_reason_info = {
                    "status": proc_status["status"],
                    "current_version": proc_status["version"],
                    "target_version": self.get_matching_pkg_real_version(host_obj.os_type, host_obj.cpu_arch),
                }

                if base_reason_info["status"] != constants.ProcStateType.RUNNING:
                    # 插件状态异常时进行重装
                    instance_actions[host_id__instance_id_map[bk_host_id]] = install_action
                    push_migrate_reason_func(
                        _instance_id=instance_id,
                        migrate_type=backend_const.PluginMigrateType.ABNORMAL_PROC_STATUS,
                        **base_reason_info,
                    )

                elif self.is_version_sensitive:
                    # 版本不一致时进行重装
                    if base_reason_info["current_version"] != base_reason_info["target_version"]:
                        instance_actions[host_id__instance_id_map[bk_host_id]] = install_action
                        push_migrate_reason_func(
                            _instance_id=instance_id,
                            migrate_type=backend_const.PluginMigrateType.VERSION_CHANGE,
                            **base_reason_info,
                        )

    def filter_related_process_statuses(self, auto_trigger: bool) -> QuerySet:
        """
        查询此步骤相关联的进程状态
        :param auto_trigger: 任务是否自动触发的
        :return:
        """
        if self.subscription_step.subscription_id in [None, -1]:
            return models.ProcessStatus.objects.none()
        # 默认仅查出需要使用的非 JSON 字段
        # 此处不考虑用 only，only 隐式仅加载某些字段，容易在引用对象处造成 n+1 查询
        statuses = models.ProcessStatus.objects.filter(
            source_id=self.subscription_step.subscription_id,
            name=self.plugin_name,
        ).values("id", "bk_host_id", "retry_times", "status", "version", "group_id", "name")
        # 仅主程序部署需要获取最新的状态，第三方订阅互相不影响，没有所谓最新状态
        # 当自动触发时，不需要过滤 is_latest=True，否则会导致一些没成功的任务进程查询不出来，最终导致max_retry_times不生效
        # 非自动触发时仅筛选is_latest=True，解决策略拓扑节点减少后，变更情况与已部署节点数 & 策略编辑后实际范围 关联不一致的问题
        # 关联不一致主要是因为计入了REMOVE_FROM_SCOPE的情况，这部分机器会执行停止或被抑制
        # 情况1：部分机器执行停止，符合预期，从策略范围移除的主机需要执行停止操作（巡检仅从DB层面移除）
        # 情况2：从策略移除的主机被其他策略管控，此时这部分主机的操作被抑制，不会生成instancerecord，体现为忽略主机数增多
        # 情况2导致关联不一致的问题，但该问题仅影响数量层面，对实际结果没有影响，为了保证SaaS查看的变更正常，仅计算策略实际管控范围内的变更
        if self.subscription.is_main and not auto_trigger:
            statuses = statuses.filter(is_latest=True)
        return statuses

    def get_action_dict(self) -> Dict[str, str]:
        if self.subscription.is_main:
            return {
                "install_action": backend_const.ActionNameType.MAIN_INSTALL_PLUGIN,
                "uninstall_action": backend_const.ActionNameType.MAIN_STOP_PLUGIN,
                "start_action": backend_const.ActionNameType.MAIN_START_PLUGIN,
                "push_config": backend_const.ActionNameType.MAIN_INSTALL_PLUGIN,
            }
        else:
            return {
                "install_action": backend_const.ActionNameType.INSTALL,
                "uninstall_action": backend_const.ActionNameType.UNINSTALL,
                "start_action": backend_const.ActionNameType.START,
                "push_config": backend_const.ActionNameType.PUSH_CONFIG,
            }

    def make_instances_migrate_actions(
        self,
        instances: Dict[str, Dict[str, Union[Dict, Any]]],
        auto_trigger: bool = False,
        preview_only: bool = False,
        **kwargs,
    ) -> Dict[str, Dict]:
        """
        计算实例变化所需要变更动作
        :param instances: dict 变更后的实例列表
        :param auto_trigger: bool 是否自动触发
        :param preview_only: 是否仅预览，若为true则不做任何保存或执行动作
        :return: dict 需要对哪些实例做哪些动作
        """
        migrate_reasons = {}

        def _push_migrate_reason(_instance_id: str, **_extra_info):
            migrate_reason = migrate_reasons.get(_instance_id, {})
            # 优先使用新传入的参数extra_info
            migrate_reasons[_instance_id] = dict(ChainMap(_extra_info, migrate_reason))

        instance_actions = {}
        action = self.subscription_step.config.get("job_type")
        if action:
            if self.check_and_skip and action == backend_const.ActionNameType.MAIN_INSTALL_PLUGIN:
                bk_host_ids: Set[int] = {instance["host"].get("bk_host_id") for instance in instances.values()}
                bk_host_id__host_map: Dict[int, models.Host] = {
                    host.bk_host_id: host
                    for host in models.Host.objects.filter(bk_host_id__in=bk_host_ids).only(
                        "bk_host_id", "bk_agent_id", "inner_ip", "bk_cloud_id", "os_type", "cpu_arch", "inner_ipv6"
                    )
                }
                self.handle_check_and_skip_instances(
                    install_action=action,
                    instance_actions=instance_actions,
                    push_migrate_reason_func=_push_migrate_reason,
                    bk_host_id__host_map=bk_host_id__host_map,
                    instances=instances,
                )
                self.handle_not_change_instances(
                    instances=instances, migrate_reasons=migrate_reasons, push_migrate_reason_func=_push_migrate_reason
                )
            else:
                # 一次性任务，如指定了action，则对这些实例都执行action动作
                instance_actions = {instance_id: action for instance_id in instances.keys()}
            return {"instance_actions": instance_actions, "migrate_reasons": migrate_reasons}

        bk_host_ids = set()
        instance_ids = set()
        id_to_instance_id = {}
        instance_key = "host" if self.subscription.object_type == models.Subscription.ObjectType.HOST else "service"
        id_key = "bk_host_id" if instance_key == "host" else "id"
        for instance_id, instance in list(instances.items()):
            instance_ids.add(instance_id)
            bk_host_ids.add(instance["host"]["bk_host_id"])
            id_to_instance_id[instance[instance_key][id_key]] = instance_id

        statuses = list(self.filter_related_process_statuses(auto_trigger=auto_trigger))
        for status in statuses:
            bk_host_ids.add(status["bk_host_id"])

        group_id__host_key__proc_status_map = defaultdict(dict)
        bk_host_id__host_map = {
            host.bk_host_id: host for host in models.Host.objects.filter(bk_host_id__in=bk_host_ids)
        }
        for status in statuses:
            # 未同步的主机，忽略
            if status["bk_host_id"] not in bk_host_id__host_map:
                continue
            host_key = tools.create_host_key({"bk_host_id": status["bk_host_id"]})
            # group 已经可以包含主机id了，为啥还要套一层字典？
            # 因为服务实例远程采集场景中，一个 group_id 可能对应多个主机
            group_id__host_key__proc_status_map[status["group_id"]][host_key] = status

        uninstall_ids: List[int] = []
        max_retry_instance_ids: List[str] = []
        wait_for_config_check_instance_ids: List[str] = []
        instance_id__proc_statuses_map: Dict[str, List[Dict[str, Any]]] = {}

        action_dict = self.get_action_dict()
        ap_id_obj_map = models.AccessPoint.ap_id_obj_map()
        for group_id, host_key__proc_status_map in list(group_id__host_key__proc_status_map.items()):
            _id = int(tools.parse_group_id(group_id)["id"])
            instance_id = tools.create_node_id(
                {
                    "object_type": self.subscription.object_type,
                    "node_type": self.subscription.NodeType.INSTANCE,
                    id_key: _id,
                }
            )
            process_statuses = list(host_key__proc_status_map.values())

            for process_status in process_statuses:
                if process_status["retry_times"] > MAX_RETRY_TIME:
                    max_retry_instance_ids.append(instance_id)

            if instance_id not in instance_ids:
                # 如果实例已经不存在且状态不是已停止，则卸载插件/停止插件
                for process_status in process_statuses:
                    if process_status["status"] != constants.ProcStateType.TERMINATED:
                        uninstall_ids.append(_id)
                        break
            else:
                # 获取当前实例需要下发的机器
                if not self.subscription_step.subscription.target_hosts:
                    target_host_keys = [tools.create_host_key(instances[instance_id]["host"])]
                else:
                    target_host_keys = [
                        tools.create_host_key(target_host)
                        for target_host in self.subscription_step.subscription.target_hosts
                    ]

                check_version_result = self.check_version_change(bk_host_id__host_map, process_statuses)
                _push_migrate_reason(
                    _instance_id=instance_id,
                    current_version=check_version_result["current_version"],
                    target_version=check_version_result["target_version"],
                )

                # 如果需要下发的机器数量与正在运行的进程数量不符
                if len(process_statuses) != len(target_host_keys):
                    instance_actions[instance_id] = action_dict["install_action"]
                    _push_migrate_reason(
                        _instance_id=instance_id, migrate_type=backend_const.PluginMigrateType.PROC_NUM_NOT_MATCH
                    )
                    continue

                # 如果运行中进程存在任何异常，则重新下发
                instance_statuses = {status["status"] for status in process_statuses}
                if {constants.ProcStateType.UNKNOWN, constants.ProcStateType.TERMINATED} & instance_statuses:
                    if constants.ProcStateType.UNKNOWN in instance_statuses:
                        instance_actions[instance_id] = action_dict["install_action"]
                    elif constants.ProcStateType.TERMINATED in instance_statuses:
                        instance_actions[instance_id] = action_dict["start_action"]
                    _push_migrate_reason(
                        _instance_id=instance_id, migrate_type=backend_const.PluginMigrateType.ABNORMAL_PROC_STATUS
                    )

                # 如果下发版本发生变化，则重新下发
                if self.subscription.category == constants.SubscriptionType.POLICY:
                    if check_version_result["has_change"]:
                        instance_actions[instance_id] = action_dict["install_action"]
                        _push_migrate_reason(
                            _instance_id=instance_id, migrate_type=backend_const.PluginMigrateType.VERSION_CHANGE
                        )

                # 如果配置文件变化，则需要重新下发
                if instance_actions.get(instance_id) in [None, action_dict["start_action"]]:
                    wait_for_config_check_instance_ids.append(instance_id)
                    instance_id__proc_statuses_map[instance_id] = process_statuses

        self.handle_config_change_instances(
            auto_trigger=auto_trigger,
            instance_ids=wait_for_config_check_instance_ids,
            push_config_action=action_dict["push_config"],
            instance_actions=instance_actions,
            push_migrate_reason_func=_push_migrate_reason,
            ap_id_obj_map=ap_id_obj_map,
            bk_host_id__host_map=bk_host_id__host_map,
            instances=instances,
            instance_id__proc_statuses_map=instance_id__proc_statuses_map,
        )

        # 处理已不在订阅范围内实例
        self.handle_uninstall_instances(
            auto_trigger=auto_trigger,
            preview_only=preview_only,
            uninstall_action=action_dict["uninstall_action"],
            uninstall_ids=uninstall_ids,
            instance_actions=instance_actions,
            push_migrate_reason_func=_push_migrate_reason,
        )

        # 处理新增实例
        self.handle_new_add_instances(
            install_action=action_dict["install_action"],
            instances=instances,
            instance_actions=instance_actions,
            bk_host_id__host_map=bk_host_id__host_map,
            group_id__host_key__proc_status_map=group_id__host_key__proc_status_map,
            push_migrate_reason_func=_push_migrate_reason,
        )

        # 处理超出最大重试次数的实例
        self.handle_exceed_max_retry_times_instances(
            instance_actions, max_retry_instance_ids, auto_trigger, preview_only, _push_migrate_reason
        )

        # 豁免手动操作实例
        self.handle_manual_op_instances(instances, instance_actions, auto_trigger, _push_migrate_reason)

        # 归档无需变更的实例，该钩子需要最后处理
        self.handle_not_change_instances(instances, migrate_reasons, _push_migrate_reason)

        # TODO 实际执行安装数量 < 策略部署范围，未及时同步CC主机（拓扑下主机数量减少），暂不处理该问题

        return {"instance_actions": instance_actions, "migrate_reasons": migrate_reasons}


class BasePluginAction(six.with_metaclass(abc.ABCMeta, Action)):
    """
    步骤动作调度器
    """

    # 作业类型
    JOB_TYPE = None

    # 操作类型
    OP_TYPE = None

    # 动作描述
    ACTION_DESCRIPTION = ""

    # 是否需要重置重试次数
    NEED_RESET_RETRY_TIMES = True

    def __init__(self, action_name: str, step: PluginStep, instance_record_ids: List[int]):
        """
        冗余构造函数，便于溯源step
        :param Step step: 步骤实例
        :param models.SubscriptionInstanceRecord instance_record_ids: 订阅实例执行记录
        """
        self.step = step
        super().__init__(action_name, step, instance_record_ids)

    def get_plugin_manager(self, subscription_instances: List[models.SubscriptionInstanceRecord]):
        """
        根据主机生成插件管理器
        """
        subscription_instance_ids = [sub_inst.id for sub_inst in subscription_instances]
        return PluginManager(subscription_instance_ids, self.step)

    def generate_activities(
        self,
        subscription_instances: List[models.SubscriptionInstanceRecord],
        global_pipeline_data: Data,
        meta: Dict[str, Any],
        current_activities=None,
    ) -> Tuple[List[PluginServiceActivity], Data]:
        plugin_manager = self.get_plugin_manager(subscription_instances)
        activities = []
        if not current_activities:
            # 初始化进程状态
            activities = [plugin_manager.init_process_status(action=self.ACTION_NAME)]

        # 插入生成的流程
        _activities, pipeline_data = self._generate_activities(plugin_manager)
        for _activity in _activities:
            # 排除特殊条件下，_activity为None的场景
            if not _activity:
                continue

            activities.append(_activity)
            if _activity.component.code == plugin.TransferScriptComponent.code:
                activities.append(plugin_manager.init_proc_script())

        if self.NEED_RESET_RETRY_TIMES:
            # 插入重置重试次数及结束事件
            activities.append(plugin_manager.reset_retry_times())

        # 注入公共参数
        self.inject_vars_to_global_data(global_pipeline_data, meta)
        # 流程由多个 step 拼接而成，对于 step 特有的属性，需要通过 activities 注入，避免多段覆盖
        for act in activities:
            act.component.inputs.plugin_name = Var(type=Var.PLAIN, value=self.step.plugin_name)
            act.component.inputs.subscription_step_id = Var(type=Var.PLAIN, value=self.step.subscription_step.id)
            act.component.inputs.meta = Var(type=Var.PLAIN, value=meta)
        return activities, pipeline_data

    @abc.abstractmethod
    def _generate_activities(self, plugin_manager) -> Tuple[List[PluginServiceActivity], Data]:
        """
        :param PluginManager plugin_manager:
        :return list
        """
        raise NotImplementedError


class MainPluginAction(BasePluginAction, ABC):
    pass


class PluginAction(six.with_metaclass(abc.ABCMeta, BasePluginAction)):
    """
    插件主进程操作
    """

    pass


class InstallPlugin(PluginAction):
    """
    安装插件
    """

    ACTION_NAME = backend_const.ActionNameType.INSTALL
    ACTION_DESCRIPTION = _("部署插件")

    def _generate_activities(self, plugin_manager: PluginManager):
        # 固定流程：下发插件 -> 安装插件
        activities = [
            plugin_manager.set_process_status(constants.ProcStateType.UNKNOWN),
            plugin_manager.transfer_package(),
            plugin_manager.install_package(),
            plugin_manager.allocate_port(),
            plugin_manager.render_and_push_config_by_subscription(self.step.subscription_step.id),
            plugin_manager.operate_proc(op_type=constants.GseOpType.RESTART, plugin_desc=self.step.plugin_desc),
            plugin_manager.set_process_status(constants.ProcStateType.RUNNING),
        ]

        return activities, None


class MainInstallPlugin(MainPluginAction, InstallPlugin):
    """
    V1.3安装插件
    """

    ACTION_NAME = backend_const.ActionNameType.MAIN_INSTALL_PLUGIN
    ACTION_DESCRIPTION = _("部署插件程序")

    def _generate_activities(self, plugin_manager):
        # 固定流程：下发插件 -> 安装插件
        activities = [
            plugin_manager.set_process_status(constants.ProcStateType.UNKNOWN),
            plugin_manager.transfer_script(
                op_types=[
                    constants.GseOpType.START,
                    constants.GseOpType.RESTART,
                    constants.GseOpType.RELOAD,
                    constants.GseOpType.STOP,
                ]
            ),
            plugin_manager.transfer_package(),
            plugin_manager.install_package(),
            plugin_manager.render_and_push_config_by_subscription(self.step.subscription_step.id),
            plugin_manager.operate_proc(constants.GseOpType.RESTART, self.step.plugin_desc),
            # 如果是单次执行进程，启动后需要取消托管，防止 Agent 反复拉起
            plugin_manager.operate_proc(constants.GseOpType.UNDELEGATE, plugin_desc=self.step.plugin_desc)
            if self.step.plugin_desc.auto_type == constants.GseAutoType.SINGLE_EXECUTION.value
            else None,
            plugin_manager.set_process_status(constants.ProcStateType.RUNNING),
        ]

        return list(filter(None, activities)), None


class UninstallPlugin(PluginAction):
    """
    卸载插件
    """

    ACTION_NAME = backend_const.ActionNameType.UNINSTALL
    ACTION_DESCRIPTION = _("卸载插件")

    def _generate_activities(self, plugin_manager):
        # 停用插件 -> 卸载插件
        activities = [
            plugin_manager.operate_proc(constants.GseOpType.STOP, self.step.plugin_desc),
            # TODO 卸载时需要在GSE注销进程
            plugin_manager.uninstall_package(),
            plugin_manager.set_process_status(constants.ProcStateType.REMOVED),
        ]
        return activities, None


class PushConfig(PluginAction):
    """
    下发插件配置
    """

    ACTION_NAME = backend_const.ActionNameType.PUSH_CONFIG
    ACTION_DESCRIPTION = _("下发插件配置")

    def _generate_activities(self, plugin_manager: PluginManager):
        # 下发配置 -> 重启插件
        activities = [
            plugin_manager.set_process_status(constants.ProcStateType.UNKNOWN),
            plugin_manager.render_and_push_config_by_subscription(self.step.subscription_step.id),
            plugin_manager.operate_proc(op_type=constants.GseOpType.RELOAD, plugin_desc=self.step.plugin_desc),
            plugin_manager.operate_proc(op_type=constants.GseOpType.DELEGATE, plugin_desc=self.step.plugin_desc),
            plugin_manager.set_process_status(constants.ProcStateType.RUNNING),
        ]
        return activities, None


class RemoveConfig(PluginAction):
    """
    移除配置，官方插件专用
    """

    ACTION_NAME = backend_const.ActionNameType.REMOVE_PLUGIN_CONFIG
    ACTION_DESCRIPTION = _("移除插件配置")

    def _generate_activities(self, plugin_manager):
        # 移除配置 -> 重启插件
        activities = [
            plugin_manager.remove_config(),
            plugin_manager.operate_proc(constants.GseOpType.RELOAD, plugin_desc=self.step.plugin_desc),
            plugin_manager.set_process_status(constants.ProcStateType.REMOVED),
        ]
        return activities, None


class StartPlugin(PluginAction):
    """
    启动插件
    """

    ACTION_NAME = backend_const.ActionNameType.START
    ACTION_DESCRIPTION = _("启动插件进程")

    def _generate_activities(self, plugin_manager):
        # 启动插件
        activities = [
            plugin_manager.switch_subscription_enable(enable=True),
            plugin_manager.set_process_status(constants.ProcStateType.UNKNOWN),
            plugin_manager.operate_proc(constants.GseOpType.START, plugin_desc=self.step.plugin_desc),
            # 如果是单次执行进程，启动后需要取消托管，防止 Agent 反复拉起
            plugin_manager.operate_proc(constants.GseOpType.UNDELEGATE, plugin_desc=self.step.plugin_desc)
            if self.step.plugin_desc.auto_type == constants.GseAutoType.SINGLE_EXECUTION.value
            else None,
            plugin_manager.set_process_status(constants.ProcStateType.RUNNING),
        ]
        return list(filter(None, activities)), None


class MainStartPlugin(MainPluginAction, StartPlugin):
    ACTION_NAME = backend_const.ActionNameType.MAIN_START_PLUGIN

    def _generate_activities(self, plugin_manager):
        _activities, pipeline_data = super()._generate_activities(plugin_manager)
        _activities.insert(2, plugin_manager.transfer_script(op_types=[constants.GseOpType.START]))
        return _activities, None


class MainReStartPlugin(MainPluginAction, StartPlugin):
    ACTION_NAME = backend_const.ActionNameType.RESTART
    ACTION_DESCRIPTION = _("重启插件进程")

    def _generate_activities(self, plugin_manager):
        # 重启插件
        activities = [
            plugin_manager.set_process_status(constants.ProcStateType.UNKNOWN),
            plugin_manager.transfer_script(
                op_types=[constants.GseOpType.RESTART, constants.GseOpType.START, constants.GseOpType.STOP]
            ),
            plugin_manager.operate_proc(constants.GseOpType.RESTART, self.step.plugin_desc),
            # 如果是单次执行进程，启动后需要取消托管，防止 Agent 反复拉起
            plugin_manager.operate_proc(constants.GseOpType.UNDELEGATE, plugin_desc=self.step.plugin_desc)
            if self.step.plugin_desc.auto_type == constants.GseAutoType.SINGLE_EXECUTION.value
            else None,
            plugin_manager.set_process_status(constants.ProcStateType.RUNNING),
        ]
        return list(filter(None, activities)), None


class StopPlugin(PluginAction):
    """
    停用插件
    """

    ACTION_NAME = backend_const.ActionNameType.STOP
    ACTION_DESCRIPTION = _("停止插件进程")

    def _generate_activities(self, plugin_manager):
        # 停止插件

        # 为了避免策略启用时
        if self.step.subscription.category == models.Subscription.CategoryType.ONCE:
            final_status = constants.ProcStateType.MANUAL_STOP
        else:
            final_status = constants.ProcStateType.REMOVED

        activities = [
            plugin_manager.set_process_status(constants.ProcStateType.UNKNOWN),
            plugin_manager.operate_proc(constants.GseOpType.STOP, self.step.plugin_desc),
            plugin_manager.set_process_status(final_status),
        ]
        return activities, None


class MainStopPlugin(MainPluginAction, StopPlugin):
    ACTION_NAME = backend_const.ActionNameType.MAIN_STOP_PLUGIN

    def _generate_activities(self, plugin_manager):
        _activities, pipeline_data = super()._generate_activities(plugin_manager)
        _activities.insert(1, plugin_manager.transfer_script(op_types=[constants.GseOpType.STOP]))
        return _activities, None


class ReloadPlugin(PluginAction):
    """
    重载插件
    """

    ACTION_NAME = backend_const.ActionNameType.RELOAD_PLUGIN
    ACTION_DESCRIPTION = _("重载插件")

    def _generate_activities(self, plugin_manager):
        # 重载插件
        activities = [
            plugin_manager.set_process_status(constants.ProcStateType.UNKNOWN),
            plugin_manager.operate_proc(constants.GseOpType.RELOAD, self.step.plugin_desc),
            plugin_manager.set_process_status(constants.ProcStateType.RUNNING),
        ]
        return activities, None


class MainReloadPlugin(MainPluginAction, ReloadPlugin):
    ACTION_NAME = backend_const.ActionNameType.MAIN_RELOAD_PLUGIN

    def _generate_activities(self, plugin_manager):
        _activities, pipeline_data = super()._generate_activities(plugin_manager)
        _activities.insert(1, plugin_manager.transfer_script(op_types=[constants.GseOpType.RELOAD]))
        return _activities, None


class DelegatePlugin(PluginAction):
    """
    托管插件
    """

    ACTION_NAME = backend_const.ActionNameType.DELEGATE_PLUGIN
    ACTION_DESCRIPTION = _("托管插件")

    def _generate_activities(self, plugin_manager):
        # 重启插件
        activities = [
            plugin_manager.set_process_status(constants.ProcStateType.UNKNOWN),
            plugin_manager.transfer_script(op_types=[constants.GseOpType.START]),
            plugin_manager.operate_proc(constants.GseOpType.DELEGATE, self.step.plugin_desc),
            plugin_manager.set_process_status(constants.ProcStateType.RUNNING),
        ]
        return activities, None


class MainDelegatePlugin(MainPluginAction, DelegatePlugin):
    ACTION_NAME = backend_const.ActionNameType.MAIN_DELEGATE_PLUGIN

    def _generate_activities(self, plugin_manager):
        _activities, pipeline_data = super()._generate_activities(plugin_manager)
        _activities.insert(1, plugin_manager.transfer_script(op_types=[constants.GseOpType.START]))
        return _activities, None


class UnDelegatePlugin(PluginAction):
    """
    取消托管插件
    """

    ACTION_NAME = backend_const.ActionNameType.UNDELEGATE_PLUGIN
    ACTION_DESCRIPTION = _("取消托管插件")

    def _generate_activities(self, plugin_manager):
        # 重启插件
        activities = [
            plugin_manager.set_process_status(constants.ProcStateType.UNKNOWN),
            plugin_manager.operate_proc(constants.GseOpType.UNDELEGATE, self.step.plugin_desc),
            plugin_manager.set_process_status(constants.ProcStateType.RUNNING),
        ]
        return activities, None


class MainUnDelegatePlugin(MainPluginAction, UnDelegatePlugin):
    ACTION_NAME = backend_const.ActionNameType.MAIN_UNDELEGATE_PLUGIN


class DebugPlugin(PluginAction):
    ACTION_NAME = backend_const.ActionNameType.DEBUG_PLUGIN
    ACTION_DESCRIPTION = _("调试插件")

    def _generate_activities(self, plugin_manager):
        activities = [
            plugin_manager.transfer_package(),
            plugin_manager.install_package(),
            plugin_manager.render_and_push_config_by_subscription(self.step.subscription_step.id),
            plugin_manager.debug(),
            plugin_manager.stop_debug(),
            plugin_manager.set_process_status(constants.ProcStateType.REMOVED),
        ]
        return activities, None


class StopDebugPlugin(PluginAction):
    ACTION_NAME = backend_const.ActionNameType.STOP_DEBUG_PLUGIN
    ACTION_DESCRIPTION = _("停止调试插件")

    def _generate_activities(self, plugin_manager):
        activities = [
            plugin_manager.stop_debug(),
            plugin_manager.set_process_status(constants.ProcStateType.REMOVED),
        ]
        return activities, None


class StopAndDeletePlugin(PluginAction):
    ACTION_NAME = backend_const.ActionNameType.STOP_AND_DELETE_PLUGIN
    ACTION_DESCRIPTION = _("停用插件并删除订阅")
    NEED_RESET_RETRY_TIMES = False

    def _generate_activities(self, plugin_manager):
        activities = [
            # 停用时变更启用状态为False，关闭巡检
            plugin_manager.switch_subscription_enable(enable=False),
            plugin_manager.set_process_status(constants.ProcStateType.UNKNOWN),
            plugin_manager.transfer_script(op_types=[constants.GseOpType.STOP]),
            plugin_manager.operate_proc(constants.GseOpType.STOP, self.step.plugin_desc),
            plugin_manager.set_process_status(constants.ProcStateType.REMOVED),
            plugin_manager.delete_subscription(),
        ]
        return activities, None


class MainStopAndDeletePlugin(MainPluginAction, StopAndDeletePlugin):
    ACTION_NAME = backend_const.ActionNameType.MAIN_STOP_AND_DELETE_PLUGIN
    ACTION_DESCRIPTION = _("停用插件并删除订阅")
