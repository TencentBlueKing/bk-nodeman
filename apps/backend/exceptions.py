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

from apps.exceptions import AppBaseException


class BackendBaseException(AppBaseException):
    MODULE_CODE = 2000


class FileNotExistError(BackendBaseException):
    MESSAGE = _("文件不存在")
    ERROR_CODE = 1


class JobNotExistError(BackendBaseException):
    MESSAGE = _("任务不存在")
    ERROR_CODE = 2


class StopDebugError(BackendBaseException):
    MESSAGE = _("停止调试失败")
    ERROR_CODE = 3


class PluginNotExistError(BackendBaseException):
    MESSAGE = _("插件包不存在")
    MESSAGE_TPL = _("插件包[{plugin_name}-{os_type}-{cpu_arch}]不存在")
    ERROR_CODE = 4


class PackageStatusOpError(BackendBaseException):
    MESSAGE = _("插件包状态变更错误")
    ERROR_CODE = 5


class PackageVersionValidationError(BackendBaseException):
    MESSAGE = _("插件包版本校验错误")
    ERROR_CODE = 6


class GenCommandsError(BackendBaseException):
    MESSAGE = _("安装命令生成失败")
    ERROR_CODE = 7


class GseEncryptedError(BackendBaseException):
    MESSAGE = _("GSE敏感信息加密失败")
    ERROR_CODE = 8


class PluginParseError(BackendBaseException):
    MESSAGE = _("插件解析错误")
    ERROR_CODE = 9


class CreatePackageRecordError(BackendBaseException):
    MESSAGE = _("归档插件包信息错误")
    ERROR_CODE = 10


class OsVersionPackageValidationError(BackendBaseException):
    MESSAGE = _("操作系统版本安装包校验错误")
    MESSAGE_TPL = _("操作系统[{os_type}]不支持 对应版本[{os_version}]的安装包")
    ERROR_CODE = 11


class AgentConfigTemplateNotExistError(BackendBaseException):
    MESSAGE = _("配置模板不存在")
    MESSAGE_TPL = _("配置模板[{name}-{filename}-{os_type}-{cpu_arch}]不存在")
    ERROR_CODE = 12


class NotSemanticVersionError(BackendBaseException):
    MESSAGE_TPL = _("版本号 -> {version} 不符合语义化版本规则")
    ERROR_CODE = 13


class PkgMetaInfoValidationError(BackendBaseException):
    MESSAGE = _("安装包元数据校验失败")
    ERROR_CODE = 14


class AgentConfigTemplateEnvNotExistError(BackendBaseException):
    MESSAGE = _("配置模板Env不存在")
    MESSAGE_TPL = _("配置模板Env不存在[{name}-{version}-{os_type}-{cpu_arch}]不存在")
    ERROR_CODE = 15


class ModelInstanceNotFoundError(BackendBaseException):
    MESSAGE = _("模型对象不存在")
    MESSAGE_TPL = _("模型对象 -> [{model_name}] 不存在")
    ERROR_CODE = 16
