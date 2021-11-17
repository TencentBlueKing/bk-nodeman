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

from .check_agent_status import CheckAgentStatusService
from .choose_access_point import ChooseAccessPointService
from .configure_policy import ConfigurePolicyService
from .get_agent_status import GetAgentStatusService
from .query_password import QueryPasswordService
from .register_host import RegisterHostService


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


class GetAgentStatusComponent(Component):
    name = _("查询Agent状态")
    code = "get_agent_status"
    bound_service = GetAgentStatusService


class CheckAgentStatusComponent(Component):
    name = _("检查Agent状态")
    code = "agent_check_agent_status"
    bound_service = CheckAgentStatusService
