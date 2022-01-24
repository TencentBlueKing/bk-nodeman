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

from django.utils.translation import ugettext_lazy as _

from pipeline.component_framework.component import Component

from . import base
from .check_agent_status import CheckAgentStatusService
from .check_policy_gse_to_proxy import CheckPolicyGseToProxyService
from .choose_access_point import ChooseAccessPointService
from .configure_policy import ConfigurePolicyService
from .delegate_plugin_proc import DelegatePluginProcService
from .get_agent_status import GetAgentStatusService
from .install import InstallService
from .push_files_to_proxy import PushFilesToProxyService
from .push_upgrade_package import PushUpgradeFileService
from .query_password import QueryPasswordService
from .register_host import RegisterHostService
from .reload_agent_config import ReloadAgentConfigService
from .render_and_push_gse_config import RenderAndPushGseConfigService
from .restart import RestartService
from .run_upgrade_command import RunUpgradeCommandService
from .update_install_info import UpdateInstallInfoService
from .update_process_status import UpdateProcessStatusService
from .wait import WaitService


class QueryPasswordComponent(Component):
    name = _("查询主机密码")
    code = "query_password"
    bound_service = QueryPasswordService


class ChooseAccessPointComponent(Component):
    name = _("选择接入点")
    code = "choose_access_point"
    bound_service = ChooseAccessPointService


class RegisterHostComponent(Component):
    name = _("注册主机到配置平台")
    code = "register_host_to_cmdb"
    bound_service = RegisterHostService


class InstallComponent(Component):
    name = _("安装")
    code = "install"
    bound_service = InstallService


class ConfigurePolicyComponent(Component):
    name = _("配置策略")
    code = "configure_policy"
    bound_service = ConfigurePolicyService


class DelegatePluginProcComponent(Component):
    name = _("托管插件进程")
    code = "delegate_plugin_proc"
    bound_service = DelegatePluginProcService


class GetAgentStatusComponent(Component):
    name = _("查询Agent状态")
    code = "get_agent_status"
    bound_service = GetAgentStatusService


class ReloadAgentConfigComponent(Component):
    name = _("重载Agent配置")
    code = "reload_agent_config"
    bound_service = ReloadAgentConfigService


class RestartComponent(Component):
    name = _("重启")
    code = "restart"
    bound_service = RestartService


class UpdateProcessStatusComponent(Component):
    name = _("更新主机进程状态")
    code = "update_process_status"
    bound_service = UpdateProcessStatusService


class CheckAgentStatusComponent(Component):
    name = _("检查Agent状态")
    code = "agent_check_agent_status"
    bound_service = CheckAgentStatusService


class PushUpgradePackageComponent(Component):
    name = _("下发升级包")
    code = "push_upgrade_package"
    bound_service = PushUpgradeFileService


class CheckPolicyGseToProxyComponent(Component):
    name = _("检测 GSE Server 到 Proxy 策略")
    code = "check_policy_gse_to_proxy"
    bound_service = CheckPolicyGseToProxyService


class RunUpgradeCommandComponent(Component):
    name = _("下发升级脚本命令")
    code = "run_upgrade_command"
    bound_service = RunUpgradeCommandService


class RenderAndPushGseConfigComponent(Component):
    name = _("渲染并下发Agent配置")
    code = "render_and_push_gse_config"
    bound_service = RenderAndPushGseConfigService


class WaitComponent(Component):
    name = _("等待")
    code = "wait"
    bound_service = WaitService


class AgentExecuteScriptComponent(Component):
    name = _("执行脚本")
    code = "agent_execute_script"
    bound_service = base.AgentExecuteScriptService


class AgentTransferFiletComponent(Component):
    name = _("分发文件")
    code = "agent_transfer_file"
    bound_service = base.AgentTransferFileService


class AgentPushConfigComponent(Component):
    name = _("分发配置")
    code = "agent_push_config"
    bound_service = base.AgentPushConfigService


class PushFilesToProxyComponent(Component):
    name = _("下发文件到Proxy")
    code = "push_files_to_proxy"
    bound_service = PushFilesToProxyService


class UpdateInstallInfoComponent(Component):
    name = _("更新安装信息")
    code = "update_install_info"
    bound_service = UpdateInstallInfoService
