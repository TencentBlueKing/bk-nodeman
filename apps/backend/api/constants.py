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


from django.conf import settings


class OS(object):
    """
    操作系统
    """

    WINDOWS = "windows"
    LINUX = "linux"
    AIX = "aix"
    SOLARIS = "solaris"


# 操作系统->系统账户映射表
ACCOUNT_MAP = {
    OS.WINDOWS: settings.BACKEND_WINDOWS_ACCOUNT,
    OS.LINUX: "root",
    OS.AIX: "root",
    OS.SOLARIS: "root",
}

# 操作系统->后缀映射表
SUFFIX_MAP = {
    OS.WINDOWS: "bat",
    OS.LINUX: "sh",
    OS.AIX: "ksh",
    OS.SOLARIS: "sh",
}


class JobDataStatus(object):
    """
    JobAPI->status响应状态码
    """

    NON_EXECUTION = 1
    PENDING = 2
    SUCCESS = 3
    FAILED = 4


class JobIPStatus(object):
    """
    JobAPI->ip_status响应状态码
    """

    AGENT_EXCEPTION = 1
    ALREADY_SUCCESS = 3
    WAITING_FOR_EXEC = 5
    RUNNING = 7
    SUCCESS = 9
    FAILED = 11
    TASK_DEPLOY_FAILED = 12
    TIMEOUT = 13
    SCRIPT_EXECUTE_FAILED = 101


class ScriptType(object):
    """
    脚本类型代号
    """

    SHELL = 1
    BAT = 2
    PERL = 3
    PYTHON = 4
    POWERSHELL = 5


# 操作系统->脚本类型映射表
SCRIPT_TYPE_MAP = {OS.LINUX: ScriptType.SHELL, OS.WINDOWS: ScriptType.BAT}


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


GSE_RUNNING_TASK_CODE = 1000115


class GseDataErrCode(object):
    SUCCESS = 0
    RUNNING = 115
    PROC_RUNNING = 828
    NON_EXIST = 829
    ALREADY_REGISTERED = 850


# task_result键值->GSE错误码映射
GSE_TASK_RESULT_MAP = {
    GseDataErrCode.SUCCESS: "success",
    GseDataErrCode.PROC_RUNNING: "success",
    GseDataErrCode.RUNNING: "pending",
}

# 轮询间隔
POLLING_INTERVAL = 5
# 轮询超时时间
POLLING_TIMEOUT = 60 * 6
