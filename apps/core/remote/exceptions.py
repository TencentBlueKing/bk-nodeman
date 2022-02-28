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

from apps.core.exceptions import CoreBaseException


class RemoteBaseException(CoreBaseException):
    MODULE_CODE = 3002


class RunCmdError(RemoteBaseException):
    MESSAGE_TPL = _("命令执行失败: {err_msg}")
    MESSAGE = _("命令执行失败")
    ERROR_CODE = 1


class KeyExchangeError(RemoteBaseException):
    MESSAGE_TPL = _("密钥交换失败: {err_msg}")
    ERROR_CODE = 2


class PermissionDeniedError(RemoteBaseException):
    MESSAGE_TPL = _("认证失败，请检查认证信息是否有误：{err_msg}")
    ERROR_CODE = 3


class ConnectionLostError(RemoteBaseException):
    MESSAGE_TPL = _("连接丢失，远程系统未响应或登录超时：{err_msg}")
    ERROR_CODE = 4


class DisconnectError(RemoteBaseException):
    MESSAGE_TPL = _("远程连接失败：{err_msg}")
    ERROR_CODE = 5


class RemoteTimeoutError(RemoteBaseException):
    MESSAGE = _("超时")
    ERROR_CODE = 6


class ProcessError(RemoteBaseException):
    MESSAGE_TPL = _("命令返回非零值：{err_msg}")
    ERROR_CODE = 7


class SessionError(RemoteBaseException):
    MESSAGE_TPL = _("会话异常：{err_msg}")
    ERROR_CODE = 8


class RemoteIOError(RemoteBaseException):
    MESSAGE_TPL = _("IO 异常：{err_msg}")
    ERROR_CODE = 9


class FileClientError(RemoteBaseException):
    MESSAGE_TPL = _("文件远程客户端异常：{err_msg}")
    ERROR_CODE = 10
