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

import os
import platform
import re
from copy import deepcopy
from enum import Enum
from typing import Any, Dict, List, Union

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from apps.backend import constants as backend_const
from apps.utils.basic import (
    choices_to_namedtuple,
    dict_to_choices,
    reverse_dict,
    tuple_choices,
)
from apps.utils.enum import EnhanceEnum

# 此值为历史遗留，后续蓝鲸不使用此字段后可废弃
DEFAULT_SUPPLIER_ID = 0


########################################################################################################
# 任务超时控制
########################################################################################################


class TimeUnit:
    SECOND = 1
    MINUTE = SECOND * 60
    HOUR = MINUTE * 60
    DAY = HOUR * 24


# JOB 任务超时时间
JOB_TIMEOUT = 30 * TimeUnit.MINUTE

########################################################################################################
# 周期任务周期 run_every，非特殊统一使用秒作为单位的 int 类型，不使用crontab格式
# 以便与削峰函数 calculate_countdown 所用的 duration 复用
########################################################################################################

CONFIGURATION_POLICY_INTERVAL = 1 * TimeUnit.MINUTE
GSE_SVR_DISCOVERY_INTERVAL = 1 * TimeUnit.MINUTE
COLLECT_AUTO_TRIGGER_JOB_INTERVAL = 5 * TimeUnit.MINUTE
SYNC_CMDB_CLOUD_AREA_INTERVAL = 10 * TimeUnit.SECOND
SYNC_AGENT_STATUS_TASK_INTERVAL = 10 * TimeUnit.MINUTE
SYNC_PROC_STATUS_TASK_INTERVAL = settings.SYNC_PROC_STATUS_TASK_INTERVAL
SYNC_BIZ_TO_GRAY_SCOPE_LIST_INTERVAL = 30 * TimeUnit.MINUTE

CLEAN_EXPIRED_INFO_INTERVAL = 6 * TimeUnit.HOUR

SYNC_CMDB_BIZ_TOPO_TASK_INTERVAL = 1 * TimeUnit.DAY
SYNC_CMDB_HOST_INTERVAL = 1 * TimeUnit.DAY
CLEAR_NEED_DELETE_HOST_IDS_INTERVAL = 1 * TimeUnit.MINUTE

########################################################################################################
# 第三方系统相关配置
########################################################################################################

# 默认管控区域ID
DEFAULT_CLOUD = int(os.environ.get("DEFAULT_CLOUD", 0))
DEFAULT_CLOUD_NAME = os.environ.get("DEFAULT_CLOUD_NAME", _("直连区域"))
# 自动选择接入点ID
DEFAULT_AP_ID = int(os.environ.get("DEFAULT_AP_ID", -1))
# 自动选择安装通道ID
DEFAULT_INSTALL_CHANNEL_ID = int(os.environ.get("DEFAULT_INSTALL_CHANNEL_ID", -1))
# 自动选择的云区域ID
AUTOMATIC_CHOICE_CLOUD_ID = int(os.environ.get("AUTOMATIC_CHOICE_CLOUD_ID", -1))
# 自动选择
AUTOMATIC_CHOICE = os.environ.get("AUTOMATIC_CHOICE", _("自动选择"))
# 默认安装通道
DEFAULT_INSTALL_CHANNEL_NAME = os.environ.get("DEFAULT_INSTALL_CHANNEL_NAME", _("默认通道"))
# GSE命名空间
GSE_NAMESPACE = "nodeman"

########################################################################################################
# 字符串常量
########################################################################################################

LINUX_SEP = "/"

WINDOWS_SEP = "\\"

# 临时文件存放位置
TMP_DIR = ("/tmp", "c:/")[platform.system() == "Windows"]

# 临时文件名格式模板
TMP_FILE_NAME_FORMAT = "nm_tf_{name}"


class PluginChildDir(Enum):
    EXTERNAL = "external_plugins"
    OFFICIAL = "plugins"

    @classmethod
    def get_optional_items(cls) -> List[str]:
        return [cls.EXTERNAL.value, cls.OFFICIAL.value]


# 插件默认
PLUGIN_DEFAULT_MEM_LIMIT = 10
PLUGIN_DEFAULT_CPU_LIMIT = 10

########################################################################################################
# CHOICES
########################################################################################################
AUTH_TUPLE = ("PASSWORD", "KEY", "TJJ_PASSWORD")
AUTH_CHOICES = tuple_choices(AUTH_TUPLE)
AuthType = choices_to_namedtuple(AUTH_CHOICES)

OS_TUPLE = ("LINUX", "WINDOWS", "AIX", "SOLARIS", "DARWIN")
OS_CHOICES = tuple_choices(OS_TUPLE)
OsType = choices_to_namedtuple(OS_CHOICES)
OS_CHN = {os_type: os_type if os_type == OsType.AIX else os_type.capitalize() for os_type in OS_TUPLE}
BK_OS_TYPE = {"LINUX": "1", "WINDOWS": "2", "AIX": "3", "SOLARIS": "5", "DARWIN": "8"}
# 操作系统匹配关键词
OS_KEYWORDS = {
    OsType.LINUX: ["linux", "ubuntu", "centos", "redhat", "suse", "debian", "fedora"],
    OsType.WINDOWS: ["windows", "xserver"],
    OsType.AIX: ["aix"],
}

# 操作系统->系统账户映射表
ACCOUNT_MAP = {
    OsType.WINDOWS: settings.BACKEND_WINDOWS_ACCOUNT,
    OsType.LINUX: settings.BACKEND_UNIX_ACCOUNT,
    OsType.AIX: settings.BACKEND_UNIX_ACCOUNT,
    OsType.SOLARIS: settings.BACKEND_UNIX_ACCOUNT,
    OsType.DARWIN: settings.BACKEND_UNIX_ACCOUNT,
    OsType.WINDOWS.lower(): settings.BACKEND_WINDOWS_ACCOUNT,
    OsType.LINUX.lower(): settings.BACKEND_UNIX_ACCOUNT,
    OsType.AIX.lower(): settings.BACKEND_UNIX_ACCOUNT,
    OsType.SOLARIS.lower(): settings.BACKEND_UNIX_ACCOUNT,
    OsType.DARWIN.lower(): settings.BACKEND_UNIX_ACCOUNT,
}

OS_TYPE = {"1": "LINUX", "2": "WINDOWS", "3": "AIX", "5": "SOLARIS", "8": "DARWIN"}

NODE_TUPLE = ("AGENT", "PROXY", "PAGENT")
NODE_CHOICES = tuple_choices(NODE_TUPLE)
NodeType = choices_to_namedtuple(NODE_CHOICES)
NODE_TYPE_ALIAS_MAP = {NodeType.AGENT: "Agent", NodeType.PROXY: "Proxy", NodeType.PAGENT: "P-Agent"}

NODE_FROM_TUPLE = ("CMDB", "EXCEL", "NODE_MAN")
NODE_FROM_CHOICES = tuple_choices(NODE_FROM_TUPLE)
NodeFrom = choices_to_namedtuple(NODE_FROM_CHOICES)

PROC_TUPLE = ("AGENT", "PLUGIN")
PROC_CHOICES = tuple_choices(PROC_TUPLE)
ProcType = choices_to_namedtuple(PROC_CHOICES)

# 订阅步骤类型，和NodeType的区别：NodeType是主机的节点类型（包含PAGENT），订阅步骤中，PAGENT & AGENT均视为AGENT
SUB_STEP_TUPLE = ("AGENT", "PLUGIN", "PROXY")
SUB_STEP_CHOICES = tuple_choices(SUB_STEP_TUPLE)
SubStepType = choices_to_namedtuple(SUB_STEP_CHOICES)
SUB_STEP_ALIAS_MAP = {SubStepType.AGENT: _("Agent"), SubStepType.PLUGIN: _("插件"), SubStepType.PROXY: _("Proxy")}

HEAD_TUPLE = ("total_count", "failed_count", "success_count")
HEAD_CHOICES = tuple_choices(HEAD_TUPLE)
HeadType = choices_to_namedtuple(HEAD_CHOICES)

POLICY_HEAD_TUPLE = ("name", "plugin_name", "creator", "update_time", "nodes_scope", "bk_biz_scope", "enable")
POLICY_HEAD_CHOICES = tuple_choices(POLICY_HEAD_TUPLE)
PolicyHeadType = choices_to_namedtuple(POLICY_HEAD_CHOICES)

PLUGIN_HEAD_TUPLE = ("name", "category", "scenario", "description")
PLUGIN_HEAD_CHOICES = tuple_choices(PLUGIN_HEAD_TUPLE)
PluginHeadType = choices_to_namedtuple(PLUGIN_HEAD_CHOICES)

SORT_TUPLE = ("ASC", "DEC")
SORT_CHOICES = tuple_choices(SORT_TUPLE)
SortType = choices_to_namedtuple(SORT_CHOICES)

AGENT_JOB_TUPLE = (
    "INSTALL_AGENT",
    "RESTART_AGENT",
    "REINSTALL_AGENT",
    "UNINSTALL_AGENT",
    "REMOVE_AGENT",
    "UPGRADE_AGENT",
    "IMPORT_AGENT",
    "RESTART_AGENT",
    "RELOAD_AGENT",
    "ACTIVATE_AGENT",
)

PROXY_JOB_TUPLE = (
    "INSTALL_PROXY",
    "RESTART_PROXY",
    "REINSTALL_PROXY",
    "REPLACE_PROXY",
    "UNINSTALL_PROXY",
    "UPGRADE_PROXY",
    "IMPORT_PROXY",
    "RESTART_PROXY",
    "RELOAD_PROXY",
)

PLUGIN_JOB_TUPLE = (
    "MAIN_START_PLUGIN",
    "MAIN_STOP_PLUGIN",
    "MAIN_RESTART_PLUGIN",
    "MAIN_RELOAD_PLUGIN",
    "MAIN_DELEGATE_PLUGIN",
    "MAIN_UNDELEGATE_PLUGIN",
    "MAIN_INSTALL_PLUGIN",
    "MAIN_STOP_AND_DELETE_PLUGIN",
    "DEBUG_PLUGIN",
    "STOP_DEBUG_PLUGIN",
    "PUSH_CONFIG_PLUGIN",
    "REMOVE_CONFIG_PLUGIN",
)
PACKAGE_JOB_TUPLE = ("PACKING_PLUGIN",)

JOB_TUPLE = AGENT_JOB_TUPLE + PLUGIN_JOB_TUPLE + PACKAGE_JOB_TUPLE + PROXY_JOB_TUPLE
JOB_CHOICES = tuple_choices(JOB_TUPLE)
JobType = choices_to_namedtuple(JOB_CHOICES)

JOB_TYPE_MAP = {"agent": AGENT_JOB_TUPLE, "proxy": PROXY_JOB_TUPLE, "plugin": PLUGIN_JOB_TUPLE}

JOB_TYPE_DICT = {
    JobType.INSTALL_PROXY: _("安装 Proxy"),
    JobType.INSTALL_AGENT: _("安装 Agent"),
    JobType.RESTART_AGENT: _("重启 Agent"),
    JobType.RESTART_PROXY: _("重启 Proxy"),
    JobType.REPLACE_PROXY: _("替换 Proxy"),
    JobType.REINSTALL_PROXY: _("重装 Proxy"),
    JobType.REINSTALL_AGENT: _("重装 Agent"),
    JobType.UPGRADE_PROXY: _("升级 Proxy"),
    JobType.UPGRADE_AGENT: _("升级 Agent"),
    JobType.REMOVE_AGENT: _("移除 Agent"),
    JobType.UNINSTALL_AGENT: _("卸载 Agent"),
    JobType.UNINSTALL_PROXY: _("卸载 Proxy"),
    JobType.IMPORT_PROXY: _("导入Proxy机器"),
    JobType.IMPORT_AGENT: _("导入Agent机器"),
    JobType.MAIN_START_PLUGIN: _("启动插件"),
    JobType.MAIN_STOP_PLUGIN: _("停止插件"),
    JobType.MAIN_RESTART_PLUGIN: _("重启插件"),
    JobType.MAIN_RELOAD_PLUGIN: _("重载插件"),
    JobType.MAIN_DELEGATE_PLUGIN: _("托管插件"),
    JobType.MAIN_UNDELEGATE_PLUGIN: _("取消托管插件"),
    JobType.MAIN_INSTALL_PLUGIN: _("安装插件"),
    JobType.MAIN_STOP_AND_DELETE_PLUGIN: _("停止插件并删除策略"),
    JobType.RELOAD_AGENT: _("重载配置"),
    JobType.ACTIVATE_AGENT: _("切换配置"),
    JobType.RELOAD_PROXY: _("重载配置"),
    JobType.PACKING_PLUGIN: _("打包插件"),
    JobType.PUSH_CONFIG_PLUGIN: _("下发插件配置"),
    JobType.REMOVE_CONFIG_PLUGIN: _("移除插件配置"),
    # 以下仅为表头【手动安装】做翻译，手动安装时仍传INSTALL_XXX
    "MANUAL_INSTALL_AGENT": _("手动安装 Agent"),
    "MANUAL_INSTALL_PROXY": _("手动安装 Proxy"),
}

OP_TYPE_TUPLE = (
    "INSTALL",
    "REINSTALL",
    "UNINSTALL",
    "REMOVE",
    "REPLACE",
    "UPGRADE",
    "UPDATE",
    "IMPORT",
    "UPDATE",
    "START",
    "STOP",
    "RELOAD",
    "ACTIVATE",
    "RESTART",
    "DELEGATE",
    "UNDELEGATE",
    "DEBUG",
    "MANUAL_INSTALL",
    "PACKING",
    "STOP_AND_DELETE",
    "PUSH",
    "IGNORED",
    "POLICY_CONTROL",
    "REMOVE_CONFIG",
    "PUSH_CONFIG",
)
OP_CHOICES = tuple_choices(OP_TYPE_TUPLE)
OpType = choices_to_namedtuple(OP_CHOICES)
# 操作类型 - 名称映射
OP_TYPE_ALIAS_MAP = {
    OpType.INSTALL: _("安装"),
    OpType.RESTART: _("重启"),
    OpType.REPLACE: _("替换"),
    OpType.UPGRADE: _("升级"),
    OpType.REINSTALL: _("重装"),
    OpType.UPDATE: _("更新"),
    OpType.REMOVE: _("移除"),
    OpType.UNINSTALL: _("卸载"),
    OpType.IMPORT: _("导入"),
    OpType.START: _("启动"),
    OpType.STOP: _("停止"),
    OpType.RELOAD: _("重载"),
    OpType.ACTIVATE: _("切换配置"),
    OpType.DELEGATE: _("托管"),
    OpType.UNDELEGATE: _("取消托管"),
    OpType.MANUAL_INSTALL: _("手动安装"),
    OpType.PACKING: _("打包"),
    OpType.DEBUG: _("调试"),
    OpType.STOP_AND_DELETE: _("卸载并删除"),
    OpType.PUSH: _("下发"),
    OpType.IGNORED: _("忽略"),
    OpType.REMOVE_CONFIG: _("移除配置"),
    OpType.PUSH_CONFIG: _("下发配置"),
    OpType.POLICY_CONTROL: _("策略管控"),
}
# 后台流程动作 - 任务类型 映射
ACTION_NAME_JOB_TYPE_MAP = {
    **{action_name: action_name for action_name in backend_const.ACTION_NAME_TUPLE if action_name in JOB_TUPLE},
    **{
        backend_const.ActionNameType.INSTALL: JobType.PUSH_CONFIG_PLUGIN,
        backend_const.ActionNameType.UNINSTALL: JobType.REMOVE_CONFIG_PLUGIN,
        backend_const.ActionNameType.PUSH_CONFIG: JobType.PUSH_CONFIG_PLUGIN,
        backend_const.ActionNameType.START: JobType.PUSH_CONFIG_PLUGIN,
        backend_const.ActionNameType.STOP: JobType.REMOVE_CONFIG_PLUGIN,
    },
}

STATUS_TUPLE = ("QUEUE", "PENDING", "RUNNING", "SUCCESS", "FAILED")
STATUS_CHOICES = tuple_choices(STATUS_TUPLE)
StatusType = choices_to_namedtuple(STATUS_CHOICES)

POLICY_OP_TYPE_TUPLE = ("START", "STOP", "STOP_AND_DELETE", "DELETE", "RETRY_ABNORMAL")
POLICY_OP_CHOICES = tuple_choices(POLICY_OP_TYPE_TUPLE)
PolicyOpType = choices_to_namedtuple(POLICY_OP_CHOICES)

HEAD_PLUGINS = ["basereport", "exceptionbeat", "processbeat", "bkunifylogbeat", "bkmonitorbeat"]

IAM_ACTION_DICT = {
    "cloud_view": _("管控区域查看"),
    "cloud_edit": _("管控区域编辑"),
    "cloud_delete": _("管控区域删除"),
    "cloud_create": _("管控区域创建"),
    "ap_edit": _("接入点编辑"),
    "ap_delete": _("接入点删除"),
    "ap_create": _("接入点创建"),
    "ap_view": _("接入点查看"),
    "globe_task_config": _("任务配置"),
    "task_history_view": _("任务历史查看"),
    "agent_view": _("agent查询"),
    "agent_operate": _("agent操作"),
    "proxy_operate": _("proxy操作"),
    "plugin_view": _("插件实例查询"),
    "plugin_operate": _("插件实例操作"),
    "plugin_pkg_import": _("插件包导入"),
    "plugin_pkg_operate": _("插件包操作"),
    "strategy_create": _("策略创建"),
    "strategy_view": _("策略查看"),
    "strategy_operate": _("策略编辑"),
    "strategy_range_select": _("策略目标选择"),
}
IAM_ACTION_TUPLE = tuple(IAM_ACTION_DICT.keys())
IAM_ACTION_CHOICES = tuple_choices(IAM_ACTION_TUPLE)
IamActionType = choices_to_namedtuple(IAM_ACTION_CHOICES)


class SubscriptionType:
    POLICY = "policy"


class JobStatusType(object):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PART_FAILED = "PART_FAILED"
    TERMINATED = "TERMINATED"
    REMOVED = "REMOVED"
    FILTERED = "FILTERED"
    IGNORED = "IGNORED"
    PROCESSING_STATUS = [PENDING, RUNNING]

    @classmethod
    def get_choices(cls, return_dict_choices=False):
        choices = (
            (cls.PENDING, _("等待执行")),
            (cls.RUNNING, _("正在执行")),
            (cls.SUCCESS, _("执行成功")),
            (cls.FAILED, _("执行失败")),
            (cls.PART_FAILED, _("部分失败")),
            (cls.TERMINATED, _("已终止")),
            (cls.REMOVED, _("已移除")),
            (cls.FILTERED, _("被过滤的")),
            (cls.IGNORED, _("已忽略")),
        )
        if return_dict_choices:
            return dict(choices)
        return choices


NODE_MAN_LOG_LEVEL = ("INFO", "DEBUG", "PRIMARY", "WARNING", "ERROR")


class BkAgentStatus(EnhanceEnum):
    """对应 GSE get_agent_status 中 bk_agent_alive 的取值"""

    NOT_ALIVE = 0
    ALIVE = 1
    TERMINATED = 2
    NOT_INSTALLED = 3

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.NOT_ALIVE: _("未知"), cls.ALIVE: _("正常"), cls.TERMINATED: _("异常"), cls.NOT_INSTALLED: _("未安装")}


PROC_STATE_TUPLE = (
    "RUNNING",
    "UNKNOWN",
    "TERMINATED",
    "NOT_INSTALLED",
    "UNREGISTER",
    "REMOVED",
    "MANUAL_STOP",
    "AGENT_NO_ALIVE",
)
PROC_STATE_CHOICES = tuple_choices(PROC_STATE_TUPLE)
ProcStateType = choices_to_namedtuple(PROC_STATE_CHOICES)
PROC_STATUS_DICT = {
    BkAgentStatus.NOT_ALIVE.value: ProcStateType.UNKNOWN,
    BkAgentStatus.ALIVE.value: ProcStateType.RUNNING,
    BkAgentStatus.TERMINATED.value: ProcStateType.TERMINATED,
    BkAgentStatus.NOT_INSTALLED.value: ProcStateType.NOT_INSTALLED,
}
PROC_STATUS_CHN = {
    ProcStateType.UNKNOWN: _("未知"),
    ProcStateType.NOT_INSTALLED: _("未安装"),
    ProcStateType.UNREGISTER: _("未注册"),
    ProcStateType.RUNNING: _("正常"),
    ProcStateType.TERMINATED: _("异常"),
    ProcStateType.MANUAL_STOP: _("手动停止"),
    "SUCCESS": _("成功"),
    "FAILED": _("失败"),
    "QUEUE": _("队列中"),
}
PLUGIN_STATUS_DICT = {0: ProcStateType.UNREGISTER, 1: ProcStateType.RUNNING, 2: ProcStateType.TERMINATED}
PROC_STATUS_TO_BE_DISPLAYED = [
    ProcStateType.RUNNING,
    ProcStateType.TERMINATED,
    ProcStateType.UNREGISTER,
    ProcStateType.MANUAL_STOP,
]

AUTO_STATE_TUPLE = ("AUTO", "UNAUTO")
AUTO_STATE_CHOICES = tuple_choices(AUTO_STATE_TUPLE)
AutoStateType = choices_to_namedtuple(AUTO_STATE_CHOICES)
AUTO_STATUS_DICT = {
    0: AutoStateType.UNAUTO,
    1: AutoStateType.AUTO,
}

IPROC_STATE_CHOICES = dict_to_choices(PROC_STATUS_DICT)
IPROC_STATUS_DICT = reverse_dict(PROC_STATUS_DICT)

FUNCTION_TUPLE = ("START", "STOP", "RESTART", "RELOAD", "DELEGATE", "UNDELEGATE")
FUNCTION_CHOICES = tuple_choices(FUNCTION_TUPLE)
FunctionType = choices_to_namedtuple(FUNCTION_CHOICES)

CATEGORY_TUPLE = ("official", "external", "scripts")
CATEGORY_CHOICES = tuple_choices(CATEGORY_TUPLE)
CategoryType = choices_to_namedtuple(CATEGORY_CHOICES)

CATEGORY_LIST = [
    {"id": CategoryType.official, "name": _("官方插件")},
    {"id": CategoryType.external, "name": _("第三方插件")},
    {"id": CategoryType.scripts, "name": _("脚本插件")},
]

CATEGORY_DICT = {CategoryType.official: _("官方插件"), CategoryType.external: _("第三方插件"), CategoryType.scripts: _("脚本插件")}

FUNCTION_LIST = [
    {"id": FunctionType.START, "name": _("启动")},
    {"id": FunctionType.STOP, "name": _("停止")},
    {"id": FunctionType.RESTART, "name": _("重启")},
    {"id": FunctionType.RELOAD, "name": _("重载")},
    {"id": FunctionType.DELEGATE, "name": _("托管")},
    {"id": FunctionType.UNDELEGATE, "name": _("取消托管")},
]

CONFIG_FILE_FORMAT_TUPLE = ("json", "yaml", "", None)
CONFIG_FILE_FORMAT_CHOICES = tuple_choices(CONFIG_FILE_FORMAT_TUPLE)

PLUGIN_OS_TUPLE = ("windows", "linux", "aix", "solaris", "darwin")
PLUGIN_OS_CHOICES = tuple_choices(PLUGIN_OS_TUPLE)
PluginOsType = choices_to_namedtuple(PLUGIN_OS_CHOICES)

CPU_TUPLE = ("x86", "x86_64", "powerpc", "aarch64", "sparc")
CPU_CHOICES = tuple_choices(CPU_TUPLE)
CpuType = choices_to_namedtuple(CPU_CHOICES)
DEFAULT_OS_CPU_MAP = {
    OsType.LINUX: CpuType.x86_64,
    OsType.WINDOWS: CpuType.x86_64,
    OsType.AIX: CpuType.powerpc,
    OsType.SOLARIS: CpuType.sparc,
    OsType.DARWIN: CpuType.x86_64,
}
CMDB_CPU_MAP = {"x86": CpuType.x86, "arm": CpuType.aarch64}

PACKAGE_PATH_RE = re.compile(
    f"(?P<is_external>external_)?plugins_(?P<os>({'|'.join(map(str, PLUGIN_OS_TUPLE))}))"
    f"_(?P<cpu_arch>({'|'.join(map(str, CPU_TUPLE))})?$)"
)

AGENT_PATH_RE = re.compile(
    f"agent_(?P<os>({'|'.join(map(str, PLUGIN_OS_TUPLE))}))" f"_(?P<cpu_arch>({'|'.join(map(str, CPU_TUPLE))})?$)"
)

# TODO: 部署方式，后续确认
DEPLOY_TYPE_TUPLE = ("package", "config", "agent")
DEPLOY_TYPE_CHOICES = tuple_choices(DEPLOY_TYPE_TUPLE)
DeployType = choices_to_namedtuple(DEPLOY_TYPE_CHOICES)
DEPLOY_TYPE_LIST = [
    {"id": DeployType.package, "name": _("整包部署")},
    {"id": DeployType.config, "name": _("功能部署")},
    {"id": DeployType.agent, "name": _("Agent自动部署")},
]
DEPLOY_TYPE_DICT = {DeployType.package: _("整包部署"), DeployType.config: _("功能部署"), DeployType.agent: _("Agent自动部署")}

PKG_STATUS_OP_TUPLE = ("release", "offline", "ready", "stop")
PKG_STATUS_OP_CHOICES = tuple_choices(PKG_STATUS_OP_TUPLE)
PkgStatusOpType = choices_to_namedtuple(PKG_STATUS_OP_CHOICES)
PKG_STATUS_OP_DICT = {
    PkgStatusOpType.release: _("发布（上线）插件包"),
    PkgStatusOpType.offline: _("下线插件包"),
    PkgStatusOpType.ready: _("启用插件包"),
    PkgStatusOpType.stop: _("停用插件包"),
}

PLUGIN_STATUS_OP_TUPLE = ("ready", "stop")
PLUGIN_STATUS_OP_CHOICES = tuple_choices(PLUGIN_STATUS_OP_TUPLE)
PluginStatusOpType = choices_to_namedtuple(PLUGIN_STATUS_OP_CHOICES)
PLUGIN_STATUS_OP_DICT = {PluginStatusOpType.ready: _("启用插件"), PluginStatusOpType.stop: _("停用插件")}

JOB_IP_STATUS_TUPLE = ("success", "pending", "failed", "not_job")
JOB_IP_STATUS_CHOICES = tuple_choices(JOB_IP_STATUS_TUPLE)
JobIpStatusType = choices_to_namedtuple(JOB_IP_STATUS_CHOICES)

SYNC_CMDB_HOST_BIZ_BLACKLIST = "SYNC_CMDB_HOST_BIZ_BLACKLIST"

# 周期任务相关
QUERY_EXPIRED_INFO_LENS = 2000
QUERY_AGENT_STATUS_HOST_LENS = 2000
QUERY_PROC_STATUS_HOST_LENS = 2000
QUERY_PROC_STATUS_BIZ_SHARDING_SIZE = 15
QUERY_CMDB_LIMIT = 500
WRITE_CMDB_LIMIT = 500
QUERY_CMDB_MODULE_LIMIT = 500
QUERY_CLOUD_LIMIT = 200
QUERY_HOST_SERVICE_TEMPLATE_LIMIT = 200
QUERY_MODULE_ID_THRESHOLD = 15
VERSION_PATTERN = re.compile(r"[vV]?(\d+\.){1,5}\d+(-rc\d)?$")
# 语义化版本正则，参考：https://semver.org/#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string
SEMANTIC_VERSION_PATTERN = re.compile(
    r"^v?(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)
WINDOWS_PORT = 445
WINDOWS_ACCOUNT = "Administrator"
LINUX_ACCOUNT = "root"
APPLY_RESOURCE_WATCH_EVENT_LENS = 2000

BIZ_CACHE_SUFFIX = "_biz_cache"
BIZ_CUSTOM_PROPERTY_CACHE_SUFFIX = "_property_cache"
JOB_MAX_VALUE = 100000

# 监听资源类型
RESOURCE_TUPLE = ("host", "host_relation", "process")
RESOURCE_CHOICES = tuple_choices(RESOURCE_TUPLE)
ResourceType = choices_to_namedtuple(RESOURCE_CHOICES)

QUERY_BIZ_LENS = 200

# 默认插件进程启动检查时间
DEFAULT_PLUGIN_PROC_START_CHECK_SECS = 9

# list_service_instance_detail接口调用参数配置
LIST_SERVICE_INSTANCE_DETAIL_LIMIT = 1000
LIST_SERVICE_INSTANCE_DETAIL_INTERVAL = 0.2

# redis键名模板
REDIS_NEED_DELETE_HOST_IDS_KEY_TPL = f"{settings.APP_CODE}:node_man:need_delete_host_ids:list"
# 从redis中读取bk_host_ids最大长度
MAX_HOST_IDS_LENGTH = 5000
# 操作系统对应账户名
OS_ACCOUNT = {"LINUX": LINUX_ACCOUNT, "WINDOWS": WINDOWS_ACCOUNT}


class ProxyFileFromType(Enum):
    """Proxy上传文件名称来源"""

    FILES = "files"
    AP_CONFIG = "ap_config"


class BkappRunEnvType(Enum):
    """APP运行环境"""

    CE = "ce"
    EE = "ee"


# GSE 端口默认值
GSE_PORT_DEFAULT_VALUE = {
    # 社区版GSE SERVER的端口有所不同
    "io_port": 48668,
    "trunk_port": 48329,
    "db_proxy_port": 58859,
    "file_svr_port": 58925,
    "data_port": 58625,
    "bt_port_start": 60020,
    "bt_port_end": 60030,
    "agent_thrift_port": 48669,
    "btsvr_thrift_port": 58930,
    "api_server_port": 50002,
    "proc_port": 50000,
    # Agent 2.0：这两个端口是 proxy 和 p-agent 连
    # Legacy：这两个端口 server 和 proxy，proxy 和 p-agent 都会连
    "bt_port": 10020,
    "tracker_port": 10030,
    "data_prometheus_port": 59402,
    "file_topology_bind_port": 28930,
    "file_metric_bind_port": 59404,
}

# 社区版GSE SERVER的端口有所不同，TODO 考虑把这些端口放到环境变量中
if settings.BKAPP_RUN_ENV == BkappRunEnvType.CE.value:
    GSE_PORT_DEFAULT_VALUE.update(
        {
            "io_port": 48533,
            "trunk_port": 48331,
            "db_proxy_port": 58817,
            "file_svr_port": 59173,
        }
    )

GSE_PORT_DEFAULT_VALUE["file_svr_port_v1"] = GSE_PORT_DEFAULT_VALUE["file_svr_port"]

# GSE V2 端口默认值
GSE_V2_PORT_DEFAULT_VALUE = deepcopy(GSE_PORT_DEFAULT_VALUE)
GSE_V2_PORT_DEFAULT_VALUE.update(
    {
        "bt_port": 20020,
        "io_port": 28668,
        "data_port": 28625,
        "tracker_port": 20030,
        "file_svr_port": 28925,
        "file_svr_port_v1": 58926,
        "btsvr_thrift_port": 58931,
        "data_prometheus_port": 29402,
        "file_metric_bind_port": 29404,
    }
)

CC_HOST_FIELDS = [
    "bk_host_id",
    "bk_agent_id",
    "bk_cloud_id",
    "bk_addressing",
    "bk_host_innerip",
    "bk_host_outerip",
    "bk_host_innerip_v6",
    "bk_host_outerip_v6",
    "bk_host_name",
    "bk_os_type",
    "bk_os_name",
    "bk_os_bit",
    "bk_os_version",
    "bk_cpu_module",
    "operator",
    "bk_bak_operator",
    "bk_isp_name",
    "bk_biz_id",
    "bk_province_name",
    "bk_state",
    "bk_state_name",
    "bk_supplier_account",
    "bk_cpu_architecture",
    "dept_name",
]

# 限流窗口配置，用于控制CMDB订阅触发的变更频率
# 二元组：防抖时间，防抖解除窗口大小
CMDB_SUBSCRIPTION_DEBOUNCE_WINDOWS = (
    (10, 70),
    (60, 180),
    (120, 420),
    (300, 900),
    (600, 1500),
    (900, 1800),
)


class SetupScriptFileName(Enum):
    SETUP_PROXY_SH = "setup_proxy.sh"
    SETUP_AGENT_SH = "setup_agent.sh"
    SETUP_AGENT_KSH = "setup_agent.ksh"
    SETUP_AGENT_ZSH = "setup_agent.zsh"
    SETUP_AGENT_BAT = "setup_agent.bat"
    SETUP_PAGENT_PY = "setup_pagent.py"
    GSECTL_BAT = "gsectl.bat"
    SETUP_AGENT_SOLARIS_SH = "setup_solaris_agent.sh"


SCRIPT_FILE_NAME_MAP = {
    OsType.LINUX: SetupScriptFileName.SETUP_AGENT_SH.value,
    OsType.WINDOWS: SetupScriptFileName.SETUP_AGENT_BAT.value,
    OsType.AIX: SetupScriptFileName.SETUP_AGENT_KSH.value,
    OsType.SOLARIS: SetupScriptFileName.SETUP_AGENT_SOLARIS_SH.value,
    OsType.DARWIN: SetupScriptFileName.SETUP_AGENT_ZSH.value,
}


########################################################################################################
# JOB
########################################################################################################


class BkJobStatus(object):
    """
    作业步骤状态码:
    1.等待执行; 2.正在执行; 3.执行成功; 4.执行失败; 5.跳过; 6.忽略错误;
    7.等待用户; 8.强制终止; 9.状态异常; 10.强制终止中; 11.强制终止成功,13.确认终止
    这里只用到其中三个状态码
    """

    PENDING = 1
    RUNNING = 2
    SUCCEEDED = 3
    FAILED = 4


class BkJobErrorCode(object):
    NOT_EXIST_HOST = -1
    AGENT_ABNORMAL = 117
    SUCCEED = 9
    RUNNING = 7
    EXCEED_BIZ_QUOTA_LIMIT = 1244032
    EXCEED_APP_QUOTA_LIMIT = 1244033
    EXCEED_SYSTEM_QUOTA_LIMIT = 1244034

    BK_JOB_ERROR_CODE_MAP = {
        NOT_EXIST_HOST: _("作业平台API返回中不存在此IP的日志，请联系管理员排查问题"),
        1: _("Agent异常"),
        3: _("上次已成功"),
        4: _("执行失败"),
        5: _("等待执行"),
        RUNNING: _("正在执行"),
        SUCCEED: _("执行成功"),
        11: _("任务失败"),
        12: _("任务下发失败"),
        13: _("任务超时"),
        15: _("任务日志错误"),
        101: _("脚本执行失败"),
        102: _("脚本执行超时"),
        103: _("脚本执行被终止"),
        104: _("脚本返回码非零"),
        AGENT_ABNORMAL: _("Agent异常"),
        202: _("文件传输失败"),
        203: _("源文件不存在"),
        303: _("文件任务超时"),
        310: _("Agent异常"),
        311: _("用户名不存在"),
        312: _("用户密码错误"),
        320: _("文件获取失败"),
        321: _("文件超出限制"),
        329: _("文件传输错误"),
        399: _("任务执行出错"),
        403: _("任务被强制终止"),
        EXCEED_BIZ_QUOTA_LIMIT: _("当前执行的作业总量超过业务配额限制"),
        EXCEED_APP_QUOTA_LIMIT: _("当前执行的作业总量超过应用配额限制"),
        EXCEED_SYSTEM_QUOTA_LIMIT: _("当前执行的作业总量超过系统配额限制"),
    }


class BkJobIpStatus(object):
    NOT_EXIST_HOST = -1
    SUCCEEDED = 9
    AGENT_ABNORMAL = 1
    RUNNING = 7

    BK_JOB_IP_STATUS_MAP = {
        NOT_EXIST_HOST: _("作业平台API返回中不存在此IP的日志，请联系管理员排查问题"),
        AGENT_ABNORMAL: _("Agent异常"),
        4: _("执行失败"),
        5: _("等待执行"),
        RUNNING: _("正在执行"),
        SUCCEEDED: _("执行成功"),
        11: _("执行失败"),
        12: _("任务下发失败"),
        403: _("任务强制终止成功"),
        404: _("任务强制终止失败"),
    }


class BkJobParamSensitiveType(EnhanceEnum):
    """作业平台参数是否敏感"""

    YES = 1
    NO = 0

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.YES: _("是，参数将会在执行详情页面上隐藏"), cls.NO: _("否，默认值")}


class BkJobScopeType(EnhanceEnum):
    """作业平台执行范围类型"""

    BIZ = "biz"
    BIZ_SET = "biz_set"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.BIZ: _("业务"), cls.BIZ_SET: _("业务集")}


class ScriptLanguageType(EnhanceEnum):
    """脚本语言类型"""

    SHELL = 1
    BAT = 2
    PERL = 3
    PYTHON = 4
    POWER_SHELL = 5

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {
            cls.SHELL: _("shell"),
            cls.BAT: _("bat"),
            cls.PERL: _("perl"),
            cls.PYTHON: _("python"),
            cls.POWER_SHELL: _("power_shell"),
        }


########################################################################################################
# GSE
########################################################################################################


class GseOpType(object):
    """
    GSE进程操作类型
    """

    START = 0
    STOP = 1
    STATUS = 2
    DELEGATE = 3
    UNDELEGATE = 4
    RESTART = 7
    RELOAD = 8

    GSE_OP_TYPE_MAP = {
        START: _("启动进程"),
        STOP: _("停止进程"),
        STATUS: _("查询进程"),
        DELEGATE: _("托管进程"),
        UNDELEGATE: _("取消托管进程"),
        RESTART: _("重启进程"),
        RELOAD: _("重载进程"),
    }


class GseAgentStatusCode(EnhanceEnum):
    NOT_FOUND = -2
    QUERY_FAILED = -1
    INITIAL = 0
    STARTING = 1
    RUNNING = 2
    LOSSY = 3
    BUSY = 4
    STOPPED = 5
    UPGRADING = 6

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {
            cls.NOT_FOUND: _("未找到"),
            cls.QUERY_FAILED: _("查询失败"),
            cls.INITIAL: _("初始状态"),
            cls.STARTING: _("启动中"),
            cls.RUNNING: _("运行中"),
            cls.LOSSY: _("有损状态"),
            cls.BUSY: _("繁忙状态"),
            cls.STOPPED: _("已停止"),
            cls.UPGRADING: _("升级中"),
        }


class GseProcessStatusCode(EnhanceEnum):
    UNREGISTER = 0
    RUNNING = 1
    STOPPED = 2

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {
            cls.UNREGISTER: _("未注册"),
            cls.RUNNING: _("运行中"),
            cls.STOPPED: _("已停止"),
        }


class GseProcessAutoCode(EnhanceEnum):
    """进程是否在GSE托管"""

    AUTO = True
    NOT_AUTO = False

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {
            cls.AUTO: _("已托管"),
            cls.NOT_AUTO: _("未托管"),
        }


class GseAgentRunMode(EnhanceEnum):
    """Agent 运行模式"""

    PROXY = "proxy"
    AGENT = "agent"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.PROXY: "Proxy Agent 模式", cls.AGENT: "Agent 模式"}


class GsePackageCode(EnhanceEnum):
    """安装包代号"""

    PROXY = "gse_proxy"
    AGENT = "gse_agent"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.PROXY: _("2.0 Proxy Agent 安装包代号"), cls.AGENT: _("2.0 Agent 安装包代号")}


class GsePackageEnv(EnhanceEnum):
    """安装包Env文件名称"""

    PROXY = ["gse_proxy.env"]
    AGENT = ["gse_agent.env"]


class GsePackageTemplate(EnhanceEnum):
    """安装包Template文件名称"""

    PROXY = ["gse_data_proxy.conf", "gse_file_proxy.conf"]
    AGENT = ["gse_agent.conf"]


class GsePackageTemplatePattern(EnhanceEnum):
    """安装包Template Pattern"""

    PROXY = re.compile("|".join(GsePackageTemplate.PROXY.value))
    AGENT = re.compile("|".join(GsePackageTemplate.AGENT.value))


class GsePackageDir(EnhanceEnum):
    """安装包打包根路径"""

    PROXY = "proxy"
    AGENT = "agent"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.PROXY: _("2.0 Proxy 打包根路径"), cls.AGENT: _("2.0 Agent 打包根路径")}


class GseCert(EnhanceEnum):
    """证书"""

    CA = "gseca.crt"
    SERVER_CERT = "gse_server.crt"
    SERVER_KEY = "gse_server.key"
    CERT_ENCRYPT_KEY = "cert_encrypt.key"
    AGENT_CERT = "gse_agent.crt"
    AGENT_KEY = "gse_agent.key"
    API_CLIENT_CERT = "gse_api_client.crt"
    API_CLIENT_KEY = "gse_api_client.key"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {
            cls.CA: _("证书 CA 内容配置"),
            cls.SERVER_CERT: _("Server 侧 CERT 内容配置"),
            cls.SERVER_KEY: _("Server 侧 KEY 内容配置"),
            cls.CERT_ENCRYPT_KEY: _("证书密码文件内容配置, 用于解密证书密码"),
            cls.AGENT_CERT: _("API 侧 CERT 内容配置, 用于其他服务调用 GSE"),
            cls.AGENT_KEY: _("API 侧 KEY 内容配置, 用于其他服务调用 GSE"),
            cls.API_CLIENT_CERT: _("Agent 侧 CERT 内容配置, 用于 Agent 链路"),
            cls.API_CLIENT_KEY: _("Agent 侧 KEY 内容配置, 用于 Agent 链路"),
        }


class GseAutoType(EnhanceEnum):
    """进程托管类型"""

    PERIODIC = 0
    RESIDENT = 1
    SINGLE_EXECUTION = 2

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {
            cls.PERIODIC: _("周期执行进程"),
            cls.RESIDENT: _("常驻进程"),
            cls.SINGLE_EXECUTION: _("单次执行进程"),
        }


class GseLinuxAutoType(EnhanceEnum):
    """GSE Linux 进程拉起（托管方式），该配置在 Agent 打包时，渲染到 gsectl 中"""

    CRONTAB = "crontab"
    RCLOCAL = "rclocal"
    SYSTEMD = "systemd"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {
            cls.CRONTAB: _("crontab"),
            cls.RCLOCAL: _("rclocal"),
            cls.SYSTEMD: _("systemd"),
        }


########################################################################################################
# CMDB
########################################################################################################


class CmdbObjectId:
    BIZ = "biz"
    SET = "set"
    MODULE = "module"
    HOST = "host"
    CUSTOM = "custom"

    SERVICE_TEMPLATE = "service_template"
    SET_TEMPLATE = "set_template"

    OBJ_ID_ALIAS_MAP = {BIZ: _("业务"), SET: _("集群"), MODULE: _("模块"), HOST: _("主机"), CUSTOM: _("自定义")}


class CmdbAddressingType(EnhanceEnum):
    """寻址方式"""

    STATIC = "static"
    DYNAMIC = "dynamic"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.STATIC: _("静态"), cls.DYNAMIC: _("动态")}


class CmdbIpVersion(EnhanceEnum):
    """IP 版本"""

    V4 = 4
    V6 = 6

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.V4: _("IPv4"), cls.V6: _("IPv6")}


class PolicyRollBackType:
    SUPPRESSED = "SUPPRESSED"
    LOSE_CONTROL = "LOSE_CONTROL"
    TRANSFER_TO_ANOTHER = "TRANSFER_TO_ANOTHER"

    ROLLBACK_TYPE__ALIAS_MAP = {SUPPRESSED: "已被其他策略管控", LOSE_CONTROL: "脱离策略管控", TRANSFER_TO_ANOTHER: "转移到优先级最高的策略"}


GSE_CLIENT_PACKAGES: List[str] = [
    "gse_client-windows-x86.tgz",
    "gse_client-windows-x86_64.tgz",
    "gse_client-linux-x86.tgz",
    "gse_client-linux-x86_64.tgz",
    "gse_client-aix6-powerpc.tgz",
    "gse_client-aix7-powerpc.tgz",
]

TOOLS_TO_PUSH_TO_PROXY: List[Dict[str, Union[List[str], Any]]] = [
    {"files": ["py36-x86_64.tgz", "py36-aarch64.tgz"], "name": _("检测 BT 分发策略（下发Py36包）")},
    {
        "files": [
            "ntrights.exe",
            "curl-ca-bundle.crt",
            "curl.exe",
            "libcurl-x64.dll",
            "7z.dll",
            "7z.exe",
            "jq.exe",
            "handle.exe",
            "unixdate.exe",
            "tcping.exe",
            "nginx-portable-x86_64.tgz",
            "nginx-portable-aarch64.tgz",
        ],
        "name": _("下发安装工具"),
    },
]

FILES_TO_PUSH_TO_PROXY = TOOLS_TO_PUSH_TO_PROXY + [
    {
        "files": GSE_CLIENT_PACKAGES,
        "name": _("下发安装包"),
        "from_type": ProxyFileFromType.AP_CONFIG.value,
    }
]

MANUAL_INSTALL_WINDOWS_BATCH_FILES = TOOLS_TO_PUSH_TO_PROXY + [
    {
        "files": ["base64.exe", "setup_agent.bat"],
        "name": _("下发windows手动安装工具"),
    }
]


class AgentWindowsDependencies(EnhanceEnum):
    CURL = "curl.exe"
    NTRIGHTS = "ntrights.exe"
    CURL_CA_BUNDLE = "curl-ca-bundle.crt"
    LIBCURL = "libcurl-x64.dll"
    UNIXDATE = "unixdate.exe"
    JQ_WIN = "jq.exe"
    BASE64 = "base64.exe"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {
            cls.CURL: _("数据传输工具, 用于下载文件依赖"),
            cls.NTRIGHTS: _("用户赋权工具"),
            cls.CURL_CA_BUNDLE: "TLS Certificate Verification",
            cls.LIBCURL: _("libcurl 共享库, 补丁文件"),
            cls.UNIXDATE: _("UNIX 时间工具包"),
            cls.JQ_WIN: _("命令行 JSON 处理器"),
            cls.BASE64: _("base64 工具包"),
        }


class CommonExecutionSolutionType(EnhanceEnum):
    BATCH = "batch"
    SHELL = "shell"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.BATCH: _("Windows 批处理脚本"), cls.SHELL: _("bash")}


class CommonExecutionSolutionStepType(EnhanceEnum):
    DEPENDENCIES = "dependencies"
    COMMANDS = "commands"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.DEPENDENCIES: _("依赖文件"), cls.COMMANDS: _("命令")}


class CmdbCpuArchType(EnhanceEnum):
    X86 = "x86"
    X86_64 = "x86"
    ARM = "arm"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.X86: _("CPU架构:x86"), cls.X86_64: _("CPU架构:x86_64"), cls.ARM: _("CPU架构:arm")}

    @classmethod
    def cpu_type__arch_map(cls):
        return {CpuType.x86: cls.X86.value, CpuType.x86_64: cls.X86_64.value, CpuType.aarch64: cls.ARM.value}


class OsBitType(EnhanceEnum):
    BIT32 = "32-bit"
    BIT64 = "64-bit"
    ARM = "arm-64bit"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.BIT32: _("操作系统位数:32-bit"), cls.BIT64: _("操作系统位数:64-bit"), cls.ARM: _("操作系统位数:arm-64bit")}

    @classmethod
    def cpu_type__os_bit_map(cls):
        return {CpuType.x86: cls.BIT32.value, CpuType.x86_64: cls.BIT64.value, CpuType.aarch64: cls.ARM.value}
