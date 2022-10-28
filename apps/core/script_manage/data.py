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

import typing

from django.utils.translation import ugettext_lazy as _

from apps.node_man import constants as node_man_constants

from . import base

FIREWALL_OFF_SCRIPT_INFO: base.ScriptInfo = base.ScriptInfo(
    name="firewall_off",
    filename="firewall_off.bat",
    path="script_manage_tmp/firewall_off.bat",
    description=_("关闭 Windows 防火墙"),
    support_os_list=[node_man_constants.OsType.WINDOWS],
)

ACTIVE_FIREWALL_POLICY_SCRIPT_INFO: base.ScriptInfo = base.ScriptInfo(
    name="active_firewall_policy",
    filename="active_firewall_policy.bat",
    path="script_manage_tmp/active_firewall_policy.bat",
    description=_("开通 Windows Agent 2.0 安装所需的网络策略"),
    support_os_list=[node_man_constants.OsType.WINDOWS],
)

SCRIPT_NAME__INFO_OBJ_MAP: typing.Dict[str, base.ScriptInfo] = {
    FIREWALL_OFF_SCRIPT_INFO.name: FIREWALL_OFF_SCRIPT_INFO,
    ACTIVE_FIREWALL_POLICY_SCRIPT_INFO.name: ACTIVE_FIREWALL_POLICY_SCRIPT_INFO,
}
