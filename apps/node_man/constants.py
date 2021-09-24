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

from __future__ import unicode_literals

import os
import platform
import re
from enum import Enum
from typing import List

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from apps.backend import constants as backend_const
from apps.utils.basic import (
    choices_to_namedtuple,
    dict_to_choices,
    reverse_dict,
    tuple_choices,
)

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


TASK_TIMEOUT = 0  # 脚本超时控制在180s=3min
TASK_MAX_TIMEOUT = 3600  # 脚本超时控制在180s=3min
JOB_MAX_RETRY = 60  # 默认轮询作业最大次数 100次=3min
JOB_SLEEP_SECOND = 3  # 默认轮询作业周期 3s
MAX_POLL_TIMES = JOB_MAX_RETRY
MAX_UNINSTALL_RETRY = JOB_MAX_RETRY

########################################################################################################
# 第三方系统相关配置
########################################################################################################

# 默认云区域ID
DEFAULT_CLOUD = int(os.environ.get("DEFAULT_CLOUD", 0))
DEFAULT_CLOUD_NAME = os.environ.get("DEFAULT_CLOUD_NAME", str(_("直连区域")))
# 自动选择接入点ID
DEFAULT_AP_ID = int(os.environ.get("DEFAULT_AP_ID", -1))
# GSE命名空间
GSE_NAMESPACE = "nodeman"

CC_HOST_FIELDS = ["bk_host_id", "bk_cloud_id", "bk_host_innerip", "bk_host_outerip", "bk_os_type", "bk_os_name"]


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


PACKAGE_PATH_RE = re.compile(
    "(?P<is_external>external_)?plugins_(?P<os>(linux|windows|aix))_(?P<cpu_arch>(x86_64|x86|powerpc|aarch64))"
)

########################################################################################################
# CHOICES
########################################################################################################
AUTH_TUPLE = ("PASSWORD", "KEY", "TJJ_PASSWORD")
AUTH_CHOICES = tuple_choices(AUTH_TUPLE)
AuthType = choices_to_namedtuple(AUTH_CHOICES)

OS_TUPLE = ("LINUX", "WINDOWS", "AIX")
OS_CHOICES = tuple_choices(OS_TUPLE)
OsType = choices_to_namedtuple(OS_CHOICES)
OS_CHN = {"WINDOWS": "Windows", "LINUX": "Linux", "AIX": "Aix"}
BK_OS_TYPE = {"LINUX": "1", "WINDOWS": "2", "AIX": "3"}

# 操作系统->系统账户映射表
ACCOUNT_MAP = {
    OsType.WINDOWS: settings.BACKEND_WINDOWS_ACCOUNT,
    OsType.LINUX: "root",
    OsType.AIX: "root",
    OsType.WINDOWS.lower(): settings.BACKEND_WINDOWS_ACCOUNT,
    OsType.LINUX.lower: "root",
    OsType.AIX.lower: "root",
}

OS_TYPE = {"1": "LINUX", "2": "WINDOWS", "3": "AIX"}

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

POLICY_HEAD_TUPLE = ("name", "plugin_name", "creator", "update_time", "nodes_scope", "bk_biz_scope")
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

HEAD_PLUGINS = ["basereport", "exceptionbeat", "processbeat", "bkunifylogbeat", "bkmonitorbeat", "gsecmdline"]

IAM_ACTION_DICT = {
    "cloud_view": _("云区域查看"),
    "cloud_edit": _("云区域编辑"),
    "cloud_delete": _("云区域删除"),
    "cloud_create": _("云区域创建"),
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

    @classmethod
    def get_choices(cls):
        return (
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


NODE_MAN_LOG_LEVEL = ("INFO", "DEBUG", "PRIMARY", "WARNING", "ERROR")

PROC_STATE_TUPLE = ("RUNNING", "UNKNOWN", "TERMINATED", "NOT_INSTALLED", "UNREGISTER", "REMOVED", "MANUAL_STOP")
PROC_STATE_CHOICES = tuple_choices(PROC_STATE_TUPLE)
ProcStateType = choices_to_namedtuple(PROC_STATE_CHOICES)
PROC_STATUS_DICT = {
    0: ProcStateType.UNKNOWN,
    1: ProcStateType.RUNNING,
    2: ProcStateType.TERMINATED,
    3: ProcStateType.NOT_INSTALLED,
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

PLUGIN_OS_TUPLE = ("windows", "linux", "aix")
PLUGIN_OS_CHOICES = tuple_choices(PLUGIN_OS_TUPLE)
PluginOsType = choices_to_namedtuple(PLUGIN_OS_CHOICES)

CPU_TUPLE = ("x86", "x86_64", "powerpc", "aarch64")
CPU_CHOICES = tuple_choices(CPU_TUPLE)
CpuType = choices_to_namedtuple(CPU_CHOICES)
DEFAULT_OS_CPU_MAP = {
    OsType.LINUX: CpuType.x86_64,
    OsType.WINDOWS: CpuType.x86_64,
    OsType.AIX: CpuType.powerpc,
}

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
QUERY_AGENT_STATUS_HOST_LENS = 500
QUERY_PROC_STATUS_HOST_LENS = 500
QUERY_CMDB_LIMIT = 500
QUERY_CMDB_MODULE_LIMIT = 500
QUERY_CLOUD_LIMIT = 200
VERSION_PATTERN = re.compile(r"[vV]?(\d+\.){1,5}\d+(-rc\d)?$")
WINDOWS_PORT = 445
WINDOWS_ACCOUNT = "Administrator"
LINUX_ACCOUNT = "root"
APPLY_RESOURCE_WATCH_EVENT_LENS = 2000

BIZ_CACHE_SUFFIX = "_biz_cache"
BIZ_CUSTOM_PROPERTY_CACHE_SUFFIX = "_property_cache"
JOB_MAX_VALUE = 100000

# 监听资源类型
RESOURCE_TUPLE = ("host", "host_relation")
RESOURCE_CHOICES = tuple_choices(RESOURCE_TUPLE)
ResourceType = choices_to_namedtuple(RESOURCE_CHOICES)

QUERY_BIZ_LENS = 200


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
    "bt_port": 10020,
    "tracker_port": 10030,
    "data_prometheus_port": 59402,
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

LIST_BIZ_HOSTS_KWARGS = [
    "bk_host_id",
    "bk_os_type",
    "bk_host_outerip",
    "bk_host_innerip",
    "bk_cpu_module",
    "bk_cloud_id",
    "operator",
    "bk_bak_operator",
    "bk_os_bit",
    "bk_os_name",
    "bk_host_name",
    "bk_supplier_account",
]

FIND_HOST_BY_TEMPLATE_FIELD = (
    "bk_host_innerip",
    "bk_cloud_id",
    "bk_host_id",
    "bk_biz_id",
    "bk_host_outerip",
    "bk_host_name",
    "bk_os_name",
    "bk_os_type",
    "operator",
    "bk_bak_operator",
    "bk_state_name",
    "bk_isp_name",
    "bk_province_name",
    "bk_supplier_account",
    "bk_state",
    "bk_os_version",
    "bk_state",
)

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
    SETUP_AGENT_BAT = "setup_agent.bat"
    SETUP_PAGENT_PY = "setup_pagent.py"
    GSECTL_BAT = "gsectl.bat"


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


class BkAgentStatus(object):
    """
    Gse agent状态码：
    0为不在线，1为在线
    """

    ALIVE = 1


class BkJobErrorCode(object):
    NOT_RUNNING = -1

    BK_JOB_ERROR_CODE_MAP = {
        NOT_RUNNING: _("该IP未执行作业，请联系管理员排查问题"),
        1: _("Agent异常"),
        3: _("上次已成功"),
        5: _("等待执行"),
        7: _("正在执行"),
        9: _("执行成功"),
        11: _("任务失败"),
        12: _("任务下发失败"),
        13: _("任务超时"),
        15: _("任务日志错误"),
        101: _("脚本执行失败"),
        102: _("脚本执行超时"),
        103: _("脚本执行被终止"),
        104: _("脚本返回码非零"),
        117: _("Agent异常"),
        202: _("文件传输失败"),
        203: _("源文件不存在"),
        310: _("Agent异常"),
        311: _("用户名不存在"),
        320: _("文件获取失败"),
        321: _("文件超出限制"),
        329: _("文件传输错误"),
        399: _("任务执行出错"),
    }


class BkJobIpStatus(object):
    NOT_RUNNING = -1
    SUCCEEDED = 9

    BK_JOB_IP_STATUS_MAP = {
        NOT_RUNNING: _("该IP未执行作业，请联系管理员排查问题"),
        1: _("Agent异常"),
        5: _("等待执行"),
        7: _("正在执行"),
        SUCCEEDED: _("执行成功"),
        11: _("执行失败"),
        12: _("任务下发失败"),
        403: _("任务强制终止成功"),
        404: _("任务强制终止失败"),
    }


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


class CmdbObjectId:
    BIZ = "biz"
    SET = "set"
    MODULE = "module"
    HOST = "host"
    CUSTOM = "custom"

    OBJ_ID_ALIAS_MAP = {BIZ: _("业务"), SET: _("集群"), MODULE: _("模块"), HOST: _("主机"), CUSTOM: _("自定义")}


class PolicyRollBackType:
    SUPPRESSED = "SUPPRESSED"
    LOSE_CONTROL = "LOSE_CONTROL"
    TRANSFER_TO_ANOTHER = "TRANSFER_TO_ANOTHER"

    ROLLBACK_TYPE__ALIAS_MAP = {SUPPRESSED: "已被其他策略管控", LOSE_CONTROL: "脱离策略管控", TRANSFER_TO_ANOTHER: "转移到优先级最高的策略"}


FILES_TO_PUSH_TO_PROXY = [
    {"files": ["py36.tgz"], "name": _("检测 BT 分发策略（下发Py36包）")},
    {
        "files": [
            "gse_client-windows-x86.tgz",
            "gse_client-windows-x86_64.tgz",
            "gse_client-aix-powerpc.tgz",
            "gse_client-linux-x86.tgz",
            "gse_client-linux-x86_64.tgz",
        ],
        "name": _("下发安装包"),
        "from_type": ProxyFileFromType.AP_CONFIG.value,
    },
    {
        "files": [
            "curl-ca-bundle.crt",
            "curl.exe",
            "libcurl-x64.dll",
            "7z.dll",
            "7z.exe",
            "handle.exe",
            "unixdate.exe",
            "tcping.exe",
            "nginx-portable.tgz",
        ],
        "name": _("下发安装工具"),
    },
]
