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

from __future__ import unicode_literals

from enum import Enum
from typing import Dict

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from apps.utils import basic, enum

########################################################################################################
# PARAMIKO 相关配置
########################################################################################################
RECV_BUFLEN = 32768  # SSH通道recv接收缓冲区大小
RECV_TIMEOUT = 60  # SSH通道recv超时 RECV_TIMEOUT秒
SSH_CON_TIMEOUT = 30  # SSH连接最长等待时间
SSH_RUN_TIMEOUT = 30  # SSH命令执行最长等待时间
MAX_WAIT_OUTPUT = 32  # 最大重试等待recv_ready次数
SLEEP_INTERVAL = 1  # recv等待间隔


class InstNodeType(object):

    BIZ = "biz"
    SET = "set"
    MODULE = "module"


# Pipeline流程动作名称
ACTION_NAME_TUPLE = (
    "MAIN_INSTALL_PLUGIN",
    "MAIN_STOP_PLUGIN",
    "MAIN_START_PLUGIN",
    "MAIN_RESTART_PLUGIN",
    "MAIN_RELOAD_PLUGIN",
    "MAIN_DELEGATE_PLUGIN",
    "MAIN_UNDELEGATE_PLUGIN",
    "MAIN_STOP_AND_DELETE_PLUGIN",
    "STOP_AND_DELETE_PLUGIN",
    "DELEGATE_PLUGIN",
    "UNDELEGATE_PLUGIN",
    "REMOVE_PLUGIN_CONFIG",
    "RELOAD_PLUGIN",
    "DEBUG_PLUGIN",
    "STOP_DEBUG_PLUGIN",
    "INSTALL",
    "UNINSTALL",
    "PUSH_CONFIG",
    "RESTART",
    "START",
    "STOP",
    # Agent
    "INSTALL_AGENT",
    "REINSTALL_AGENT",
    "UPGRADE_AGENT",
    "RESTART_AGENT",
    "UNINSTALL_AGENT",
    "RELOAD_AGENT",
    "ACTIVATE_AGENT",
    "RESTART_PROXY",
    "INSTALL_PROXY",
    "UNINSTALL_PROXY",
    "REINSTALL_PROXY",
    "UPGRADE_PROXY",
    "REPLACE_PROXY",
    "RELOAD_PROXY",
    # Agent2
    "INSTALL_AGENT_2",
    "REINSTALL_AGENT_2",
    "INSTALL_PROXY_2",
    "REINSTALL_PROXY_2",
)
ACTION_NAME_CHOICES = basic.tuple_choices(ACTION_NAME_TUPLE)
ActionNameType = basic.choices_to_namedtuple(ACTION_NAME_CHOICES)


class PluginMigrateType:
    NEW_INSTALL = "NEW_INSTALL"
    VERSION_CHANGE = "VERSION_CHANGE"
    CONFIG_CHANGE = "CONFIG_CHANGE"
    PROC_NUM_NOT_MATCH = "PROC_NUM_NOT_MATCH"
    ABNORMAL_PROC_STATUS = "ABNORMAL_PROC_STATUS"
    NOT_CHANGE = "NOT_CHANGE"
    REMOVE_FROM_SCOPE = "REMOVE_FROM_SCOPE"
    NOT_SYNC_HOST = "NOT_SYNC_HOST"
    MANUAL_OP_EXEMPT = "MANUAL_OP_EXEMPT"
    ABNORMAL_AGENT_STATUS = "ABNORMAL_AGENT_STATUS"

    MIGRATE_TYPE_ALIAS_MAP = {
        NEW_INSTALL: _("新安装"),
        VERSION_CHANGE: _("版本变更"),
        CONFIG_CHANGE: _("配置变更"),
        PROC_NUM_NOT_MATCH: _("进程数量不匹配"),
        ABNORMAL_PROC_STATUS: _("进程状态异常"),
        ABNORMAL_AGENT_STATUS: _("Agent 状态异常"),
        NOT_CHANGE: _("无需变更"),
        REMOVE_FROM_SCOPE: _("从范围中移除"),
        NOT_SYNC_HOST: _("未同步的主机"),
        MANUAL_OP_EXEMPT: _("手动操作豁免"),
    }

    MIGRATE_TYPES = list(MIGRATE_TYPE_ALIAS_MAP.keys())


class AgentMigrateType(enum.EnhanceEnum):
    REINSTALL = "REINSTALL"
    NEW_INSTALL = "NEW_INSTALL"
    CROSS_VERSION_INSTALL = "CROSS_VERSION_INSTALL"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.REINSTALL: _("重装"), cls.NEW_INSTALL: _("新安装"), cls.CROSS_VERSION_INSTALL: _("跨级安装")}


# redis键名模板
REDIS_INSTALL_CALLBACK_KEY_TPL = f"{settings.APP_CODE}:backend:agent:log:list:" + "{sub_inst_id}"

# redis Gse Agent 配置缓存
REDIS_AGENT_CONF_KEY_TPL = f"{settings.APP_CODE}:backend:agent:config:" + "{file_name}:str:{sub_inst_id}"

# 更新订阅参数储存redis键名模板
UPDATE_SUBSCRIPTION_REDIS_KEY_TPL = f"{settings.APP_CODE}:backend:subscription:update_subscription:params"

# 执行订阅参数储存redis键名模板
RUN_SUBSCRIPTION_REDIS_KEY_TPL = f"{settings.APP_CODE}:backend:subscription:run_subscription:params"


class SubscriptionSwithBizAction(enum.EnhanceEnum):
    ENABLE = "enable"
    DISABLE = "disable"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.ENABLE: _("启用"), cls.DISABLE: _("禁用")}


class ProxyConfigFile(enum.EnhanceEnum):
    V1 = ["agent.conf", "btsvr.conf", "transit.conf", "opts.conf", "plugin_info.json", "data.conf", "dataflow.conf"]
    V2 = ["gse_agent.conf", "gse_data_proxy.conf", "gse_file_proxy.conf"]


class FilterFieldName(enum.EnhanceEnum):
    BK_HOST_LIST = "bk_host_list"
    SERVICE_INSTANCE_IDS = "service_instance_ids"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.BK_HOST_LIST: _("主机id列表"), cls.SERVICE_INSTANCE_IDS: _("服务实例id列表")}

    @property
    def needs_batch_request(self) -> bool:
        if self == FilterFieldName.BK_HOST_LIST:
            return True
        elif self == FilterFieldName.SERVICE_INSTANCE_IDS:
            return False

        return True


DEFAULT_ALIVE_TIME = 30
DEFAULT_CLEAN_RECORD_LIMIT = 5000

POWERSHELL_SERVICE_CHECK_SSHD = "powershell -c Get-Service -Name sshd"

# 处理更新订阅任务间隔
UPDATE_SUBSCRIPTION_TASK_INTERVAL = 2 * 60

# 处理执行订阅任务间隔
RUN_SUBSCRIPTION_TASK_INTERVAL = 3 * 60
# 处理卸载残留订阅任务间隔
HANDLE_UNINSTALL_REST_SUBSCRIPTION_TASK_INTERVAL = 6 * 60 * 60

# 最大订阅任务数量
MAX_SUBSCRIPTION_TASK_COUNT = 50

# 订阅删除时间小时数
SUBSCRIPTION_DELETE_HOURS = 6
