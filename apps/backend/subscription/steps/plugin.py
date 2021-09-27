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
import ntpath
import os
import posixpath
from abc import ABC
from collections import ChainMap, defaultdict
from typing import Any, Callable, Dict, List, Tuple, Union

import six
from django.db.models import Q

from apps.backend import constants as backend_const
from apps.backend.plugin.manager import PluginManager, PluginServiceActivity
from apps.backend.subscription import errors, tools
from apps.backend.subscription.constants import MAX_RETRY_TIME
from apps.backend.subscription.steps import adapter
from apps.backend.subscription.steps.base import Action, Step
from apps.node_man import constants, models
from apps.node_man.exceptions import ApIDNotExistsError
from common.log import logger
from pipeline.builder import Data, Var


class PluginStep(Step):
    STEP_TYPE = "PLUGIN"

    def __init__(self, subscription_step: models.SubscriptionStep):
        # 配置数据校验
        policy_step_adapter = adapter.PolicyStepAdapter(subscription_step)

        validated_params = policy_step_adapter.params

        # 获取插件配置模板信息

        # TODO 待修改，此处port_range需要os_cpu_arch
        self.port_range = validated_params.get("port_range")

        # 更新插件包时的可选项  -- TODO
        self.keep_config = ""
        self.no_restart = ""

        self.plugin_name = policy_step_adapter.plugin_name
        self.plugin_desc = policy_step_adapter.plugin_desc
        self.os_key_pkg_map = policy_step_adapter.os_key_pkg_map
        self.config_inst_gby_os_key = policy_step_adapter.config_inst_gby_os_key
        self.config_tmpl_gby_os_key = policy_step_adapter.config_tmpl_obj_gby_os_key

        self.target_hosts = subscription_step.subscription.target_hosts

        self.process_cache = defaultdict(dict)
        super(PluginStep, self).__init__(subscription_step)

    def get_matching_package(self, os_type: str, cpu_arch: str) -> models.Packages:
        try:
            return self.os_key_pkg_map[adapter.PolicyStepAdapter.get_os_key(os_type, cpu_arch)]
        except KeyError:
            # 此处是为了延迟报错到订阅
            if self.os_key_pkg_map:
                return list(self.os_key_pkg_map.values())[0]
            raise errors.PluginValidationError(msg="插件 [{name}] 没有可供选择的插件包")

    def get_matching_config_instances(self, os_type: str, cpu_arch: str) -> List[models.PluginConfigInstance]:
        return self.config_inst_gby_os_key.get(adapter.PolicyStepAdapter.get_os_key(os_type, cpu_arch), [])

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
        filter_condition = dict(
            bk_host_id=target_host.bk_host_id,
            name=self.plugin_name,
            source_id=self.subscription_step.subscription_id,
            proc_type=constants.ProcType.PLUGIN,
            group_id=tools.create_group_id(self.subscription, instance_info),
        )
        # TODO 查询优化
        process_status = models.ProcessStatus.objects.filter(**filter_condition).last()
        if not process_status:
            return {}

        control_info = self.generate_plugin_control_info(process_status, target_host, agent_config)
        return {"control_info": control_info}

    def generate_plugin_control_info(
        self, process_status: models.ProcessStatus, host: models.Host, agent_config: Dict
    ) -> Dict[str, Any]:
        """
        生成插件控制信息
        """
        # TODO 此处容易引发n+1查询，后续如果用到这段逻辑，需要把host_id 和 host映射后放到构造函数缓存
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
            listen_ip=process_status.listen_ip,
            listen_port=process_status.listen_port,
            group_id=process_status.group_id,
            setup_path=process_status.setup_path,
            log_path=process_status.log_path,
            data_path=process_status.data_path,
            pid_path=process_status.pid_path,
        )
        return control_info

    def check_config_change(
        self,
        subscription_step: models.SubscriptionStep,
        instance_info: Dict,
        host_map: Dict,
        ap_id_obj_map: Dict,
        process_status_list: List[models.ProcessStatus],
    ) -> bool:
        """检测配置是否有变动"""
        try:
            for process_status in process_status_list:
                # 渲染新配置
                target_host = host_map[process_status.bk_host_id]
                ap = ap_id_obj_map.get(target_host.ap_id)
                if not ap:
                    raise ApIDNotExistsError()
                agent_config = ap.agent_config[target_host.os_type.lower()]
                context = tools.get_all_subscription_steps_context(
                    subscription_step, instance_info, target_host, process_status.name, agent_config
                )

                rendered_configs = tools.render_config_files_by_config_templates(
                    self.get_matching_config_templates(target_host.os_type, target_host.cpu_arch),
                    process_status,
                    context,
                    package_obj=self.get_matching_package(target_host.os_type, target_host.cpu_arch),
                )
                old_rendered_configs = process_status.configs

                for new_config in rendered_configs:
                    for old_config in old_rendered_configs:
                        if new_config["name"] == old_config["name"] and new_config["md5"] == old_config["md5"]:
                            # 配置一致，开始下一次循环
                            break
                    else:
                        # 如果在老配置中找不到新配置，则必须重新下发
                        return True

        except Exception as e:
            logger.exception("检测配置文件变动失败：%s" % e)
            # 遇到异常也被认为有改动
            return True
        return False

    def check_version_change(self, host_map: Dict[int, models.Host], statuses: List[models.ProcessStatus]) -> Dict:
        """检查版本是否有变更，并返回当前版本及目标版本"""
        current_version = None
        target_version = None
        for status in statuses:
            host = host_map[status.bk_host_id]
            package = self.get_matching_package(host.os_type, host.cpu_arch)
            current_version = status.version
            target_version = package.version
            if package.version != status.version:
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
        if self.subscription.object_type == self.subscription.ObjectType.HOST:
            # 主机类型的订阅
            host_id_biz_map = {}
            for host_info in models.Host.objects.filter(bk_host_id__in=uninstall_ids).values("bk_host_id", "bk_biz_id"):
                host_id_biz_map[host_info["bk_host_id"]] = host_info["bk_biz_id"]
            uninstall_scope = {
                "bk_biz_id": self.subscription.bk_biz_id,
                "object_type": self.subscription.object_type,
                "node_type": self.subscription.NodeType.INSTANCE,
                "nodes": [{"bk_host_id": host_id, "bk_biz_id": host_id_biz_map[host_id]} for host_id in uninstall_ids],
            }

            uninstall_instances = tools.get_instances_by_scope(uninstall_scope)

            for instance_id in uninstall_instances:
                remove_from_scope_instance_ids.add(instance_id)
                instance_actions[instance_id] = uninstall_action
                push_migrate_reason_func(
                    _instance_id=instance_id, migrate_type=backend_const.PluginMigrateType.REMOVE_FROM_SCOPE
                )
        else:
            for _id in uninstall_ids:
                instance_id = tools.create_node_id(
                    {
                        "object_type": self.subscription.object_type,
                        "node_type": self.subscription.NodeType.INSTANCE,
                        "id": _id,
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
                ).update(source_id=None, group_id=None, bk_obj_id=None)

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
            package = self.get_matching_package(host.os_type, host.cpu_arch)
            push_migrate_reason_func(
                _instance_id=instance_id,
                migrate_type=backend_const.PluginMigrateType.NEW_INSTALL,
                target_version=package.version,
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

    def list_related_process_statuses(self, auto_trigger: bool) -> List:
        """
        查询此步骤相关联的进程状态
        :param auto_trigger: 任务是否自动触发的
        :return:
        """
        if self.subscription_step.subscription_id in [None, -1]:
            return []
        # 由于 ProcessStatus 字段太多，出于优化和节省内存的习惯，这里仅 only 出需要用到的字段
        statuses = models.ProcessStatus.objects.filter(
            source_id=self.subscription_step.subscription_id,
            name=self.plugin_name,
        ).only("id", "bk_host_id", "retry_times", "status", "version", "group_id", "configs")
        # 仅主程序部署需要获取最新的状态，第三方订阅互相不影响，没有所谓最新状态
        # 当自动触发时，不需要过滤 is_latest=True，否则会导致一些没成功的任务进程查询不出来，最终导致max_retry_times不生效
        # 非自动触发时仅筛选is_latest=True，解决策略拓扑节点减少后，变更情况与已部署节点数 & 策略编辑后实际范围 关联不一致的问题
        # 关联不一致主要是因为计入了REMOVE_FROM_SCOPE的情况，这部分机器会执行停止或被抑制
        # 情况1：部分机器执行停止，符合预期，从策略范围移除的主机需要执行停止操作（巡检仅从DB层面移除）
        # 情况2：从策略移除的主机被其他策略管控，此时这部分主机的操作被抑制，不会生成instancerecord，体现为忽略主机数增多
        # 情况2导致关联不一致的问题，但该问题仅影响数量层面，对实际结果没有影响，为了保证SaaS查看的变更正常，仅计算策略实际管控范围内的变更
        if self.subscription.is_main and not auto_trigger:
            statuses = statuses.filter(is_latest=True)
        statuses = list(statuses)
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
        **kwargs
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
            # 一次性任务，如指定了action，则对这些实例都执行action动作
            return {
                "instance_actions": {instance_id: action for instance_id in instances.keys()},
                "migrate_reasons": migrate_reasons,
            }

        bk_host_ids = set()
        id_to_instance_id = {}
        instance_key = "host" if self.subscription.object_type == models.Subscription.ObjectType.HOST else "service"
        id_key = "bk_host_id" if instance_key == "host" else "id"
        for instance_id, instance in list(instances.items()):
            id_to_instance_id[instance[instance_key][id_key]] = instance_id
            bk_host_ids.add(instance["host"]["bk_host_id"])

        statuses = self.list_related_process_statuses(auto_trigger=auto_trigger)
        for status in statuses:
            bk_host_ids.add(status.bk_host_id)

        group_id__host_key__proc_status_map = defaultdict(dict)
        bk_host_id__host_map = {
            host.bk_host_id: host for host in models.Host.objects.filter(bk_host_id__in=bk_host_ids)
        }
        for status in statuses:
            # 未同步的主机，忽略
            if status.bk_host_id not in bk_host_id__host_map:
                continue
            host_key = tools.create_host_key({"bk_host_id": status.bk_host_id})
            # group 已经可以包含主机id了，为啥还要套一层字典？
            # 因为服务实例远程采集场景中，一个 group_id 可能对应多个主机
            group_id__host_key__proc_status_map[status.group_id][host_key] = status

        uninstall_ids = []
        max_retry_instance_ids = []
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
                if process_status.retry_times > MAX_RETRY_TIME:
                    max_retry_instance_ids.append(instance_id)

            if instance_id not in id_to_instance_id.values():
                # 如果实例已经不存在且状态不是已停止，则卸载插件/停止插件
                for process_status in process_statuses:
                    if process_status.status != constants.ProcStateType.TERMINATED:
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
                instance_statuses = {status.status for status in process_statuses}
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
                    is_config_change = self.check_config_change(
                        self.subscription_step,
                        instances[instance_id],
                        bk_host_id__host_map,
                        ap_id_obj_map,
                        process_statuses,
                    )

                    if is_config_change:
                        # 如果实例的配置文件发生变化，则更新配置
                        instance_actions[instance_id] = action_dict["push_config"]
                        _push_migrate_reason(
                            _instance_id=instance_id, migrate_type=backend_const.PluginMigrateType.CONFIG_CHANGE
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

    def bulk_create_host_status_cache(self, instances: Dict[str, Dict]) -> Dict[str, Dict[str, models.ProcessStatus]]:
        """
        批量创建HostStatus，并放入内存缓存中
        """
        processes = defaultdict(dict)

        statuses = models.ProcessStatus.objects.filter(
            source_type=models.ProcessStatus.SourceType.SUBSCRIPTION,
            source_id=self.subscription_step.subscription_id,
            name=self.plugin_name,
        )

        for status in statuses:
            status.package = self.get_matching_package(status.host.os_type, status.host.cpu_arch)
            host_key = tools.create_host_key(
                {
                    "bk_supplier_id": constants.DEFAULT_SUPPLIER_ID,
                    "bk_cloud_id": status.host.bk_cloud_id,
                    "ip": status.host.inner_ip,
                }
            )
            processes[status.group_id][host_key] = status

            # 更新缓存
            self.process_cache[status.group_id][host_key] = status

        target_hosts = []
        for instance_id, instance_info in instances.items():
            group_id = tools.create_group_id(self.subscription, instance_info)
            if group_id in self.process_cache:
                continue
            if not self.subscription_step.subscription.target_hosts:
                target_hosts.append(
                    {
                        "ip": instance_info["host"]["bk_host_innerip"],
                        # 感觉可能用get(key, None)比较ok？
                        "bk_cloud_id": instance_info["host"]["bk_cloud_id"] or 0,
                        "bk_supplier_id": constants.DEFAULT_SUPPLIER_ID,
                    }
                )
            else:
                target_hosts += [target_host for target_host in self.subscription_step.subscription.target_hosts]

        condition = Q()
        for target_host in target_hosts:
            condition |= Q(
                inner_ip=target_host["ip"],
                bk_cloud_id=target_host["bk_cloud_id"],
            )

        hosts = models.Host.objects.filter(condition)
        host_dict = {(host.inner_ip, int(host.bk_cloud_id), constants.DEFAULT_SUPPLIER_ID): host for host in hosts}

        to_be_created_host_status = []
        to_be_created_group_ids = []
        for instance_id, instance_info in instances.items():
            group_id = tools.create_group_id(self.subscription, instance_info)
            if group_id in self.process_cache:
                continue
            if not self.subscription_step.subscription.target_hosts:
                target_hosts = [
                    {
                        "ip": instance_info["host"]["bk_host_innerip"],
                        "bk_cloud_id": instance_info["host"]["bk_cloud_id"] or 0,
                        "bk_supplier_id": constants.DEFAULT_SUPPLIER_ID,
                    }
                ]
            else:
                target_hosts = [target_host for target_host in self.subscription_step.subscription.target_hosts]
            for target_host in target_hosts:
                host_obj = host_dict.get((target_host["ip"], int(target_host["bk_cloud_id"]), 0))
                if not host_obj:
                    continue
                # 创建进程状态实例对象（未写入DB）
                host_status = self.generate_process_status_record(host_obj, instance_info)
                to_be_created_host_status.append(host_status)
                to_be_created_group_ids.append(group_id)

        models.ProcessStatus.objects.bulk_create(to_be_created_host_status)

        # 由于批量创建是不会返回 host_status.id 的，会对后面构造任务参数造成影响，因此这里要把数据重新查出来，重新设置一遍
        host_status_list = models.ProcessStatus.objects.filter(group_id__in=to_be_created_group_ids)
        for host_status in host_status_list:
            host_key = tools.create_host_key(
                {
                    "bk_supplier_id": constants.DEFAULT_SUPPLIER_ID,
                    "bk_cloud_id": host_status.host.bk_cloud_id,
                    "ip": host_status.host.inner_ip,
                }
            )
            self.process_cache[host_status.group_id][host_key] = host_status

        return processes

    def generate_process_status_record(
        self, host: models.Host, instance_info: Dict[str, Union[Dict, Any]]
    ) -> models.ProcessStatus:
        """
        根据目标主机生成主机进程实例记录
        :param host: Host
        :param instance_info:
        :return: ProcessStatus
        """
        group_id = tools.create_group_id(self.subscription, instance_info)

        package = self.get_matching_package(host.os_type, host.cpu_arch)

        # 配置插件进程实际运行路径配置信息
        if package.os == constants.PluginOsType.windows:
            path_handler = ntpath
        else:
            path_handler = posixpath

        if package.plugin_desc.category == constants.CategoryType.external:
            # 如果为 external 插件，需要补上插件组目录
            setup_path = path_handler.join(
                package.proc_control.install_path, constants.PluginChildDir.EXTERNAL.value, group_id, package.project
            )
            log_path = path_handler.join(package.proc_control.log_path, group_id)
            data_path = path_handler.join(package.proc_control.data_path, group_id)
            pid_path_prefix, pid_filename = path_handler.split(package.proc_control.pid_path)
            pid_path = path_handler.join(pid_path_prefix, group_id, pid_filename)
        else:
            setup_path = path_handler.join(
                package.proc_control.install_path, constants.PluginChildDir.OFFICIAL.value, "bin"
            )
            log_path = package.proc_control.log_path
            data_path = package.proc_control.data_path
            pid_path = package.proc_control.pid_path

        defaults = {
            "setup_path": setup_path,
            "log_path": log_path,
            "data_path": data_path,
            "pid_path": pid_path,
            "version": package.version,
        }
        proc_status_create_data = dict(
            bk_host_id=host.bk_host_id,
            name=self.plugin_name,
            source_id=self.subscription.id,
            source_type=models.ProcessStatus.SourceType.SUBSCRIPTION,
            group_id=group_id,
            proc_type=constants.ProcType.PLUGIN,
        )
        host_key = tools.create_host_key(
            {"bk_supplier_id": constants.DEFAULT_SUPPLIER_ID, "bk_cloud_id": host.bk_cloud_id, "ip": host.inner_ip}
        )

        proc_status_create_data.update(defaults)

        # 如果是第一次创建，将配置文件初始化，避免删除的时候找不到配置文件
        rendered_configs = []
        for config in self.get_matching_config_instances(host.os_type, host.cpu_arch):
            rendered_config = {
                "instance_id": config.id,
                "content": config.template.content,
                "file_path": config.template.file_path,
                "md5": "",
            }
            if package.plugin_desc.is_official:
                # 官方插件的部署方式为单实例多配置，在配置模板的名称上追加 group id 即可对配置文件做唯一标识
                filename, extension = os.path.splitext(config.template.name)
                rendered_config["name"] = "{filename}_{group_id}{extension}".format(
                    filename=filename, group_id=group_id, extension=extension
                )
            else:
                rendered_config["name"] = config.template.name

            rendered_configs.append(rendered_config)

        proc_status_create_data["configs"] = rendered_configs

        host_status = models.ProcessStatus(**proc_status_create_data)

        host_status.host = host
        self.process_cache[group_id][host_key] = host_status
        return host_status


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
        self, subscription_instances: List[models.SubscriptionInstanceRecord], current_activities=None
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
            if _activity:
                activities.append(_activity)

        if self.NEED_RESET_RETRY_TIMES:
            # 插入重置重试次数及结束事件
            activities.append(plugin_manager.reset_retry_times())

        # 注入公共参数
        for act in activities:
            act.component.inputs.plugin_name = Var(type=Var.PLAIN, value=self.step.plugin_name)
            act.component.inputs.subscription_step_id = Var(type=Var.PLAIN, value=self.step.subscription_step.id)
        return activities, pipeline_data

    @abc.abstractmethod
    def _generate_activities(self, plugin_manager) -> List[PluginServiceActivity]:
        """
        :param PluginManager plugin_manager:
        :return list
        """
        raise NotImplementedError


class MainPluginAction(BasePluginAction, ABC):
    def _update_or_create_process_status(self, bk_host_id, group_id, rewrite_path_info):
        return Action._update_or_create_process_status(self, bk_host_id, group_id, rewrite_path_info)


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
    ACTION_DESCRIPTION = "部署插件"

    def _generate_activities(self, plugin_manager: PluginManager):
        # 固定流程：下发插件 -> 安装插件
        activities = [
            plugin_manager.set_process_status(constants.ProcStateType.UNKNOWN),
            plugin_manager.transfer_package(),
            plugin_manager.install_package(),
            plugin_manager.allocate_port(),
            plugin_manager.set_process_status(constants.ProcStateType.RUNNING),
            plugin_manager.render_and_push_config_by_subscription(self.step.subscription_step.id),
            plugin_manager.operate_proc(op_type=constants.GseOpType.RESTART),
        ]

        return activities, None


class MainInstallPlugin(MainPluginAction, InstallPlugin):
    """
    V1.3安装插件
    """

    ACTION_NAME = backend_const.ActionNameType.MAIN_INSTALL_PLUGIN
    ACTION_DESCRIPTION = "部署插件程序"

    def _generate_activities(self, plugin_manager):
        # 固定流程：下发插件 -> 安装插件
        activities = [
            plugin_manager.set_process_status(constants.ProcStateType.UNKNOWN),
            plugin_manager.transfer_package(),
            plugin_manager.install_package(),
            plugin_manager.render_and_push_config_by_subscription(self.step.subscription_step.id),
            plugin_manager.operate_proc(constants.GseOpType.RESTART),
            plugin_manager.set_process_status(constants.ProcStateType.RUNNING),
        ]

        return activities, None


class UninstallPlugin(PluginAction):
    """
    卸载插件
    """

    ACTION_NAME = backend_const.ActionNameType.UNINSTALL
    ACTION_DESCRIPTION = "卸载插件"

    def _generate_activities(self, plugin_manager):
        # 停用插件 -> 卸载插件
        activities = [
            plugin_manager.operate_proc(constants.GseOpType.STOP),
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
    ACTION_DESCRIPTION = "下发插件配置"

    def _generate_activities(self, plugin_manager: PluginManager):
        # 下发配置 -> 重启插件
        activities = [
            plugin_manager.set_process_status(constants.ProcStateType.UNKNOWN),
            plugin_manager.render_and_push_config_by_subscription(self.step.subscription_step.id),
            plugin_manager.operate_proc(op_type=constants.GseOpType.DELEGATE),
            plugin_manager.operate_proc(op_type=constants.GseOpType.RELOAD),
            plugin_manager.set_process_status(constants.ProcStateType.RUNNING),
        ]
        return activities, None


class RemoveConfig(PluginAction):
    """
    移除配置，官方插件专用
    """

    ACTION_NAME = backend_const.ActionNameType.REMOVE_PLUGIN_CONFIG
    ACTION_DESCRIPTION = "移除插件配置"

    def _generate_activities(self, plugin_manager):
        # 移除配置 -> 重启插件
        activities = [
            plugin_manager.remove_config(),
            plugin_manager.operate_proc(constants.GseOpType.RELOAD),
            plugin_manager.set_process_status(constants.ProcStateType.REMOVED),
        ]
        return activities, None


class StartPlugin(PluginAction):
    """
    启动插件
    """

    ACTION_NAME = backend_const.ActionNameType.START
    ACTION_DESCRIPTION = "启动插件进程"

    def _generate_activities(self, plugin_manager):
        # 启动插件
        activities = [
            plugin_manager.switch_subscription_enable(enable=True),
            plugin_manager.set_process_status(constants.ProcStateType.UNKNOWN),
            plugin_manager.operate_proc(constants.GseOpType.START),
            plugin_manager.set_process_status(constants.ProcStateType.RUNNING),
        ]
        return activities, None


class MainStartPlugin(MainPluginAction, StartPlugin):
    ACTION_NAME = backend_const.ActionNameType.MAIN_START_PLUGIN


class MainReStartPlugin(MainPluginAction, StartPlugin):
    ACTION_NAME = backend_const.ActionNameType.RESTART
    ACTION_DESCRIPTION = "重启插件进程"

    def _generate_activities(self, plugin_manager):
        # 重启插件
        activities = [
            plugin_manager.set_process_status(constants.ProcStateType.UNKNOWN),
            plugin_manager.operate_proc(constants.GseOpType.RESTART),
            plugin_manager.set_process_status(constants.ProcStateType.RUNNING),
        ]
        return activities, None


class StopPlugin(PluginAction):
    """
    停用插件
    """

    ACTION_NAME = backend_const.ActionNameType.STOP
    ACTION_DESCRIPTION = "停止插件进程"

    def _generate_activities(self, plugin_manager):
        # 停止插件

        # 为了避免策略启用时
        if self.step.subscription.category == models.Subscription.CategoryType.ONCE:
            final_status = constants.ProcStateType.MANUAL_STOP
        else:
            final_status = constants.ProcStateType.REMOVED

        activities = [
            plugin_manager.set_process_status(constants.ProcStateType.UNKNOWN),
            plugin_manager.operate_proc(constants.GseOpType.STOP),
            plugin_manager.set_process_status(final_status),
        ]
        return activities, None


class MainStopPlugin(MainPluginAction, StopPlugin):
    ACTION_NAME = backend_const.ActionNameType.MAIN_STOP_PLUGIN


class ReloadPlugin(PluginAction):
    """
    重载插件
    """

    ACTION_NAME = backend_const.ActionNameType.RELOAD_PLUGIN
    ACTION_DESCRIPTION = "重载插件"

    def _generate_activities(self, plugin_manager):
        # 重载插件
        activities = [
            plugin_manager.set_process_status(constants.ProcStateType.UNKNOWN),
            plugin_manager.operate_proc(constants.GseOpType.RELOAD),
            plugin_manager.set_process_status(constants.ProcStateType.RUNNING),
        ]
        return activities, None


class MainReloadPlugin(MainPluginAction, ReloadPlugin):
    ACTION_NAME = backend_const.ActionNameType.MAIN_RELOAD_PLUGIN


class DelegatePlugin(PluginAction):
    """
    托管插件
    """

    ACTION_NAME = backend_const.ActionNameType.DELEGATE_PLUGIN
    ACTION_DESCRIPTION = "托管插件"

    def _generate_activities(self, plugin_manager):
        # 重启插件
        activities = [
            plugin_manager.set_process_status(constants.ProcStateType.UNKNOWN),
            plugin_manager.operate_proc(constants.GseOpType.DELEGATE),
            plugin_manager.set_process_status(constants.ProcStateType.RUNNING),
        ]
        return activities, None


class MainDelegatePlugin(MainPluginAction, DelegatePlugin):
    ACTION_NAME = backend_const.ActionNameType.MAIN_DELEGATE_PLUGIN


class UnDelegatePlugin(PluginAction):
    """
    取消托管插件
    """

    ACTION_NAME = backend_const.ActionNameType.UNDELEGATE_PLUGIN
    ACTION_DESCRIPTION = "取消托管插件"

    def _generate_activities(self, plugin_manager):
        # 重启插件
        activities = [
            plugin_manager.set_process_status(constants.ProcStateType.UNKNOWN),
            plugin_manager.operate_proc(constants.GseOpType.UNDELEGATE),
            plugin_manager.set_process_status(constants.ProcStateType.RUNNING),
        ]
        return activities, None


class MainUnDelegatePlugin(MainPluginAction, UnDelegatePlugin):
    ACTION_NAME = backend_const.ActionNameType.MAIN_UNDELEGATE_PLUGIN


class DebugPlugin(PluginAction):
    ACTION_NAME = backend_const.ActionNameType.DEBUG_PLUGIN
    ACTION_DESCRIPTION = "调试插件"

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
    ACTION_DESCRIPTION = "停止调试插件"

    def _generate_activities(self, plugin_manager):
        activities = [
            plugin_manager.stop_debug(),
            plugin_manager.set_process_status(constants.ProcStateType.REMOVED),
        ]
        return activities, None


class StopAndDeletePlugin(PluginAction):
    ACTION_NAME = backend_const.ActionNameType.STOP_AND_DELETE_PLUGIN
    ACTION_DESCRIPTION = "停用插件并删除订阅"
    NEED_RESET_RETRY_TIMES = False

    def _generate_activities(self, plugin_manager):
        activities = [
            # 停用时变更启用状态为False，关闭巡检
            plugin_manager.switch_subscription_enable(enable=False),
            plugin_manager.set_process_status(constants.ProcStateType.UNKNOWN),
            plugin_manager.operate_proc(constants.GseOpType.STOP),
            plugin_manager.set_process_status(constants.ProcStateType.REMOVED),
            plugin_manager.delete_subscription(),
        ]
        return activities, None


class MainStopAndDeletePlugin(MainPluginAction, StopAndDeletePlugin):
    ACTION_NAME = backend_const.ActionNameType.MAIN_STOP_AND_DELETE_PLUGIN
    ACTION_DESCRIPTION = "停用插件并删除订阅"
