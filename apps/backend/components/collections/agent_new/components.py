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

from django.utils.translation import ugettext_lazy as _

from pipeline.component_framework.component import Component

from .check_policy_gse_to_proxy import CheckPolicyGseToProxyService
from .choose_access_point import ChooseAccessPointService
from .configure_policy import ConfigurePolicyService
from .delegate_plugin_proc import DelegatePluginProcService
from .get_agent_status import GetAgentStatusService
from .push_upgrade_package import PushUpgradePackageService
from .query_password import QueryPasswordService
from .register_host import RegisterHostService
from .reload_agent_config import ReloadAgentConfigService
from .restart import RestartService
from .run_upgrade_command import RunUpgradeCommandService


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


class PushUpgradePackageComponent(Component):
    name = _("下发升级包")
    code = "push_upgrade_package"
    bound_service = PushUpgradePackageService


class CheckPolicyGseToProxyComponent(Component):
    name = _("检测 GSE Server 到 Proxy 策略")
    code = "check_policy_gse_to_proxy"
    bound_service = CheckPolicyGseToProxyService


class RunUpgradeCommandComponent(Component):
    name = _("下发升级脚本命令")
    code = "run_upgrade_command"
    bound_service = RunUpgradeCommandService
