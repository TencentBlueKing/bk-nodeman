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

from __future__ import absolute_import, unicode_literals

import logging
from typing import List

from django.utils.translation import ugettext as _

from apps.backend.components.collections import plugin
from apps.backend.utils.pipeline_parser import PipelineParser as CustomPipelineParser
from apps.backend.utils.pipeline_parser import parse_pipeline
from apps.node_man import constants
from pipeline.builder import ServiceActivity, Var

logger = logging.getLogger("app")


class PluginServiceActivity(ServiceActivity):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.component.inputs.subscription_step_id = Var(type=Var.SPLICE, value="${plugin_name}")
        self.component.inputs.subscription_step_id = Var(type=Var.SPLICE, value="${subscription_step_id}")
        self.component.inputs.description = Var(type=Var.SPLICE, value="${description}")
        self.component.inputs.act_name = Var(type=Var.PLAIN, value=kwargs.get("name"))


class StatusType(object):
    QUEUE = "QUEUE"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


SCRIPT_TIMEOUT = 60 * 5


class PluginManager(object):
    def __init__(self, subscription_instance_ids: List[int], step):
        self.subscription_instance_ids = subscription_instance_ids
        self.step = step

    def init_process_status(self, action: str):
        act = PluginServiceActivity(component_code=plugin.InitProcessStatusComponent.code, name=_("初始化进程状态"))
        act.component.inputs.action = Var(type=Var.PLAIN, value=action)
        return act

    def check_agent_status(self):
        """
        查询Agent状态是否正常
        """
        act = PluginServiceActivity(component_code=plugin.CheckAgentStatusComponent.code, name=_("查询Agent状态"))
        return act

    def set_process_status(self, status):
        """
        设置插件状态
        """
        act = PluginServiceActivity(
            component_code=plugin.UpdateHostProcessStatusComponent.code,
            name=_("更新插件部署状态为{status}").format(status=status),
        )
        act.component.inputs.status = Var(type=Var.PLAIN, value=status)
        return act

    def transfer_package(self):
        act = PluginServiceActivity(component_code=plugin.TransferPackageComponent.code, name=_("下发安装包"))
        return act

    def install_package(self):
        act = PluginServiceActivity(component_code=plugin.InstallPackageComponent.code, name=_("安装插件包"))
        return act

    def uninstall_package(self):
        act = PluginServiceActivity(component_code=plugin.UnInstallPackageComponent.code, name=_("卸载插件包"))
        return act

    def reset_retry_times(self):
        """
        重置重试次数
        """
        act = PluginServiceActivity(component_code=plugin.ResetRetryTimesComponent.code, name=_("重置重试次数"))
        return act

    def allocate_port(self):
        """
        分配可用端口
        """
        act = PluginServiceActivity(component_code=plugin.JobAllocatePortComponent.code, name=_("分配可用端口"))
        return act

    def delete_subscription(self):
        act = PluginServiceActivity(component_code=plugin.DeleteSubscriptionComponent.code, name=_("删除策略"))
        return act

    def switch_subscription_enable(self, enable: bool):
        act = PluginServiceActivity(component_code=plugin.SwitchSubscriptionEnableComponent.code, name=_("切换订阅启用状态"))
        act.component.inputs.enable = Var(type=Var.PLAIN, value=enable)
        return act

    def render_and_push_config_by_subscription(self, subscription_step_id):
        """根据订阅配置生成并下发插件配置"""
        act = PluginServiceActivity(component_code=plugin.RenderAndPushConfigComponent.code, name=_("渲染下发配置"))
        act.component.inputs.subscription_step_id = Var(type=Var.PLAIN, value=subscription_step_id)

        return act

    def debug(self, script_timeout=SCRIPT_TIMEOUT):
        """
        调试插件
        :param script_timeout: 脚本时间
        :return:
        """
        act = PluginServiceActivity(component_code=plugin.DebugComponent.code, name=_("调试插件"), error_ignorable=True)
        act.component.inputs.timeout = Var(type=Var.PLAIN, value=script_timeout)
        return act

    def stop_debug(self):
        """
        停止调试插件
        """
        act = PluginServiceActivity(
            component_code=plugin.StopDebugComponent.code, name=_("停止调试插件"), error_ignorable=True
        )
        return act

    def operate_proc(self, op_type):
        """调用GSE操作插件进程"""
        if self.step.plugin_name in ["gsecmdline", "pluginscripts"]:
            # gsecmdline, pluginscripts 不是严格意义的插件，不能执行常规的启停操作
            return None
        op_type_name = constants.GseOpType.GSE_OP_TYPE_MAP.get(op_type, _("操作进程"))
        act = PluginServiceActivity(component_code=plugin.GseOperateProcComponent.code, name=op_type_name)
        act.component.inputs.op_type = Var(type=Var.PLAIN, value=op_type)
        return act

    def remove_config(self):
        act = PluginServiceActivity(component_code=plugin.RemoveConfigComponent.code, name=_("移除配置"))
        return act

    @staticmethod
    def get_debug_status(pipeline):
        def get_log_by_task_result(task_result):
            log = list()
            for res in task_result["failed"] + task_result["success"] + task_result["pending"]:
                log.append(res["log_content"])
            return "\n".join(log)

        def step_format_string(msg):
            """
            步骤分割符
            """
            return "\n************ %s ************\n" % msg

        tree_data = parse_pipeline(pipeline.tree)
        sorted_tree_data = sorted(list(tree_data.keys()), key=lambda key: tree_data[key]["index"])
        deploy, install, push_config, debug, stop_debug = (sorted_tree_data[i] for i in range(5))
        log_content = list()

        pipeline_parser = CustomPipelineParser([pipeline.id])

        steps = [
            (deploy, "DEPLOY_PLUGIN", _("下发插件包")),
            (install, "INSTALL_PLUGIN", _("安装插件包")),
            (push_config, "PUSH_CONFIG", _("下发配置文件")),
            (debug, "DEBUG_PROCESS", _("执行插件调试进程")),
            (stop_debug, "STOP_DEBUG_PROCESS", _("结束调试并回收资源")),
        ]

        for node_id, step_name, step_desc in steps:
            log_content.append(step_format_string("{} -【正在执行】".format(step_desc)))
            node_state = pipeline_parser.get_node_state(node_id)["status"]
            node_data = pipeline_parser.get_node_data(node_id)

            if node_state == "PENDING":
                return log_content, StatusType.RUNNING, step_name

            task_result = node_data["outputs"]
            if task_result and "task_result" in task_result:
                log_content.append(get_log_by_task_result(task_result["task_result"]))

            if node_state == "RUNNING":
                return log_content, StatusType.RUNNING, step_name

            if node_state == "FAILED" or node_data["ex_data"]:
                log_content.append(step_format_string("{} -【执行失败】".format(step_desc)))
                log_content.append("失败原因：{}".format(node_data["ex_data"]))
                return log_content, StatusType.FAILED, step_name

            log_content.append(step_format_string("{} -【执行成功】".format(step_desc)))

        return log_content, StatusType.SUCCESS, "STOP_DEBUG_PROCESS"
