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
import os
from typing import Any, Dict, List

from django.conf import settings
from django.utils.translation import ugettext as _

from apps.backend.components.collections.agent_new import components
from pipeline.builder import ServiceActivity, Var


class AgentServiceActivity(ServiceActivity):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.component.inputs.description = Var(type=Var.SPLICE, value="${description}")
        self.component.inputs.blueking_language = Var(type=Var.SPLICE, value="${blueking_language}")
        self.component.inputs.subscription_step_id = Var(type=Var.SPLICE, value="${subscription_step_id}")
        self.component.inputs.act_name = Var(type=Var.PLAIN, value=kwargs.get("name"))


class AgentManager(object):
    """
    Agent动作管理
    """

    def __init__(self, subscription_instance_ids: List[int], step):
        self.subscription_instance_ids = subscription_instance_ids
        self.step = step
        self.creator = step.subscription.creator

    @classmethod
    def register_host(cls):
        """注册主机"""
        act = AgentServiceActivity(
            component_code=components.RegisterHostComponent.code, name=components.RegisterHostComponent.name
        )
        return act

    def query_tjj_password(self):
        """查询铁将军密码"""
        act = AgentServiceActivity(
            component_code=components.QueryPasswordComponent.code, name=components.QueryPasswordComponent.name
        )
        act.component.inputs.creator = Var(type=Var.PLAIN, value=self.creator)
        return act

    @classmethod
    def choose_ap(cls):
        """自动选择接入点"""
        act = AgentServiceActivity(
            component_code=components.ChooseAccessPointComponent.code, name=components.ChooseAccessPointComponent.name
        )
        return act

    @classmethod
    def configure_policy(cls):
        """开通网络策略"""
        act = AgentServiceActivity(
            component_code=components.ConfigurePolicyComponent.code, name=components.ConfigurePolicyComponent.name
        )
        return act

    @classmethod
    def install(cls, name=components.InstallComponent.name):
        """执行安装脚本"""
        act = AgentServiceActivity(component_code=components.InstallComponent.code, name=name)
        act.component.inputs.success_callback_step = Var(type=Var.PLAIN, value="check_deploy_result")
        return act

    @classmethod
    def uninstall_agent(cls):
        """执行卸载AGENT脚本"""
        name = _("卸载Agent")
        act = AgentServiceActivity(component_code=components.InstallComponent.code, name=name)
        act.component.inputs.is_uninstall = Var(type=Var.PLAIN, value=True)
        act.component.inputs.success_callback_step = Var(type=Var.PLAIN, value="remove_agent")
        return act

    @classmethod
    def uninstall_proxy(cls):
        """执行卸载PROXY脚本"""
        name = _("卸载Proxy")
        act = AgentServiceActivity(component_code=components.InstallComponent.code, name=name)
        act.component.inputs.is_uninstall = Var(type=Var.PLAIN, value=True)
        act.component.inputs.success_callback_step = Var(type=Var.PLAIN, value="remove_proxy")
        return act

    @classmethod
    def push_upgrade_package(cls):
        """下发升级包"""
        act = AgentServiceActivity(
            component_code=components.PushUpgradePackageComponent.code, name=components.PushUpgradePackageComponent.name
        )
        return act

    @classmethod
    def run_upgrade_command(cls):
        """执行安装命令"""
        act = AgentServiceActivity(
            component_code=components.RunUpgradeCommandComponent.code, name=components.RunUpgradeCommandComponent.name
        )
        return act

    @classmethod
    def restart(cls, skip_polling_result: bool):
        """重启"""
        act = AgentServiceActivity(
            component_code=components.RestartComponent.code, name=components.RestartComponent.name
        )
        act.component.inputs.skip_polling_result = Var(type=Var.PLAIN, value=skip_polling_result)
        return act

    @classmethod
    def wait(cls, sleep_time: int):
        """等待"""
        act = AgentServiceActivity(component_code=components.WaitComponent.code, name=components.WaitComponent.name)
        act.component.inputs.sleep_time = Var(type=Var.PLAIN, value=sleep_time)
        return act

    @classmethod
    def get_agent_status(cls, expect_status: str, name=components.GetAgentStatusComponent.name):
        """查询Agent状态"""
        act = AgentServiceActivity(component_code=components.GetAgentStatusComponent.code, name=name)
        act.component.inputs.expect_status = Var(type=Var.PLAIN, value=expect_status)
        return act

    @classmethod
    def check_agent_status(cls, name=components.CheckAgentStatusComponent.name):
        """查询Agent状态是否正常"""
        act = AgentServiceActivity(component_code=components.CheckAgentStatusComponent.code, name=name)
        return act

    @classmethod
    def update_process_status(cls, status: str, name=components.UpdateProcessStatusComponent.name):
        """更新Agent状态"""
        act = AgentServiceActivity(component_code=components.UpdateProcessStatusComponent.code, name=name)
        act.component.inputs.status = Var(type=Var.PLAIN, value=status)
        return act

    @classmethod
    def push_files_to_proxy(cls, file: Dict[str, Any]):
        """下发文件到 Proxy """
        act = AgentServiceActivity(component_code=components.PushFilesToProxyComponent.code, name=file["name"])
        act.component.inputs.file_list = Var(type=Var.PLAIN, value=file["files"])
        act.component.inputs.file_target_path = Var(type=Var.PLAIN, value=settings.DOWNLOAD_PATH)
        return act

    @classmethod
    def start_nginx(cls):
        """启动 NGINX 服务"""
        act = AgentServiceActivity(component_code=components.AgentExecuteScriptComponent.code, name=_("启动 NGINX 服务"))
        with open(os.path.join(settings.BK_SCRIPTS_PATH, "start_nginx.sh.tpl"), encoding="utf-8") as fh:
            script = fh.read()
        # 脚本模板中存在 {print $2} 等和 format 关键字冲突的片段
        # 此处的字符串渲染采用 % 的方式
        script_content = script % {
            "nginx_path": settings.DOWNLOAD_PATH,
            "bk_nodeman_nginx_download_port": settings.BK_NODEMAN_NGINX_DOWNLOAD_PORT,
            "bk_nodeman_nginx_proxy_pass_port": settings.BK_NODEMAN_NGINX_PROXY_PASS_PORT,
        }
        act.component.inputs.script_content = Var(type=Var.PLAIN, value=script_content)
        act.component.inputs.script_param = Var(type=Var.PLAIN, value="")
        return act

    @classmethod
    def delegate_plugin(cls, plugin_name: str):
        """
        托管插件
        :param plugin_name: 插件名称
        :return:
        """
        act = AgentServiceActivity(
            component_code=components.DelegatePluginProcComponent.code,
            name=_("托管 {plugin_name} 插件进程").format(plugin_name=plugin_name),
        )
        act.component.inputs.plugin_name = Var(type=Var.PLAIN, value=plugin_name)
        return act

    @classmethod
    def render_and_push_gse_config(cls, name=components.RenderAndPushGseConfigComponent.name):
        """渲染并下载 agent 配置"""
        act = AgentServiceActivity(component_code=components.RenderAndPushGseConfigComponent.code, name=name)
        return act

    @classmethod
    def reload_agent(cls, skip_polling_result: bool):
        """重载agent"""
        act = AgentServiceActivity(
            component_code=components.ReloadAgentConfigComponent.code, name=components.ReloadAgentConfigComponent.name
        )
        act.component.inputs.skip_polling_result = Var(type=Var.PLAIN, value=skip_polling_result)
        return act

    @classmethod
    def check_policy_gse_to_proxy(cls):
        """GSE Server到Proxy的策略检查"""
        act = AgentServiceActivity(
            component_code=components.CheckPolicyGseToProxyComponent.code,
            name=components.CheckPolicyGseToProxyComponent.name,
        )
        return act

    @classmethod
    def update_install_info(cls):
        """更新安装信息"""
        act = AgentServiceActivity(
            component_code=components.UpdateInstallInfoComponent.code,
            name=components.UpdateInstallInfoComponent.name,
        )
        return act
