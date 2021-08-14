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

from apps.exceptions import AppBaseException


class NodeManBaseException(AppBaseException):
    MODULE_CODE = 1000


class CloudNotExistError(NodeManBaseException):
    MESSAGE = _("云区域不存在")
    ERROR_CODE = 1


class CloudUpdateAgentError(NodeManBaseException):
    MESSAGE = _("云区域业务已装Agent, 不可删除")
    ERROR_CODE = 2


class CloudUpdateHostError(NodeManBaseException):
    MESSAGE = _("该云区域已经存在主机, 不可删除")
    ERROR_CODE = 3


class PagentDefaultCloudError(NodeManBaseException):
    MESSAGE = _("PAGENT只能安装在非直连区域")
    ERROR_CODE = 4


class AgentDefaultCloudError(NodeManBaseException):
    MESSAGE = _("AGENT只能安装在直连区域")
    ERROR_CODE = 5


class ProxyNotAvaliableError(NodeManBaseException):
    MESSAGE = _("直连区域不可安装Proxy")
    ERROR_CODE = 6


class ApIDNotExistsError(NodeManBaseException):
    MESSAGE = _("该接入点不存在.")
    MESSAGE_TPL = _("该接入点[{ap_id}]不存在")
    ERROR_CODE = 7


class BusinessNotPermissionError(NodeManBaseException):
    MESSAGE = _("不存在某业务权限.")
    ERROR_CODE = 8


class IpInUsedError(NodeManBaseException):
    MESSAGE = _("该Ip已被占用.")
    ERROR_CODE = 9


class HostIDNotExists(NodeManBaseException):
    MESSAGE = _("不存在某Host ID.")
    ERROR_CODE = 10


class PwdCheckError(NodeManBaseException):
    MESSAGE = _("认证信息校验不通过")
    ERROR_CODE = 11


class JobDostNotExistsError(NodeManBaseException):
    MESSAGE = _("任务不存在")
    ERROR_CODE = 12


class AliveProxyNotExistsError(NodeManBaseException):
    MESSAGE = _("没有可用的Proxy")
    ERROR_CODE = 13


class CloudNotPermissionError(NodeManBaseException):
    MESSAGE = _("不存在某云区域的权限.")
    ERROR_CODE = 14


class JobNotPermissionError(NodeManBaseException):
    MESSAGE = _("不存在某任务的权限.")
    ERROR_CODE = 14


class ApNotChooseError(NodeManBaseException):
    MESSAGE = _("该主机未选择接入点，请尝试重装主机自动选择接入点")
    ERROR_CODE = 15


class CmdbAddCloudPermissionError(NodeManBaseException):
    MESSAGE = _("没有Cmdb增加云区域的权限.")
    ERROR_CODE = 16


class NotSuperUserError(NodeManBaseException):
    MESSAGE = _("您不是超级用户无法访问此页面.")
    ERROR_CODE = 17


class AllIpFiltered(NodeManBaseException):
    MESSAGE = _("所有ip均被过滤")
    ERROR_CODE = 18


class ApIdIsUsing(NodeManBaseException):
    MESSAGE = _("该接入点正在被使用")
    ERROR_CODE = 19


class IpRunningJob(NodeManBaseException):
    MESSAGE = _("该IP正在运行其他任务")
    ERROR_CODE = 20


class NotExistsOs(NodeManBaseException):
    MESSAGE = _("该主机没有操作系统参数")
    ERROR_CODE = 21


class NotHostPermission(NodeManBaseException):
    MESSAGE = _("您没有该主机的权限")
    ERROR_CODE = 22


class HostNotExists(NodeManBaseException):
    MESSAGE = _("主机不存在")
    ERROR_CODE = 23


class MixedOperationError(NodeManBaseException):
    MESSAGE = _("不允许混合操作【手动安装】和【自动安装】的主机")
    ERROR_CODE = 24


class ConfigurationPolicyError(NodeManBaseException):
    MESSAGE = _("配置Proxy策略失败")
    ERROR_CODE = 25


class IamRequestException(NodeManBaseException):
    MESSAGE = _("权限中心请求失败")
    ERROR_CODE = 26


class QueryGlobalSettingsException(AppBaseException):
    ERROR_CODE = 27
    MESSAGE = _("获取全局配置失败")


class DuplicateAccessPointNameException(AppBaseException):
    ERROR_CODE = 28
    MESSAGE = _("接入点名称重复")


class PluginNotExistError(NodeManBaseException):
    MESSAGE = _("插件不存在")
    ERROR_CODE = 29


class CacheExpiredError(NodeManBaseException):
    MESSAGE = _("缓存过期，正在重新加载...")
    ERROR_CODE = 30


class PolicyNotExistError(NodeManBaseException):
    MESSAGE = _("策略不存在")
    ERROR_CODE = 31


class PolicyNotPermissionError(NodeManBaseException):
    MESSAGE = _("不存在某策略权限")
    ERROR_CODE = 32


class PluginConfigTplNotExistError(NodeManBaseException):
    MESSAGE = _("插件配置模板不存在")
    ERROR_CODE = 33


class CreateRecordError(NodeManBaseException):
    MESSAGE = _("创建插件记录失败")
    ERROR_CODE = 34


class ApNotSupportOsError(NodeManBaseException):
    MESSAGE = _("接入点不支持此机器的操作系统.")
    MESSAGE_TPL = _("接入点不[{ap_id}]支持此机器的操作系统[{os_type}]")
    ERROR_CODE = 35


class PolicyIsRunningError(NodeManBaseException):
    MESSAGE_TPL = _("策略 -> {policy_id}「{name}」正在执行")
    ERROR_CODE = 36


class InstallChannelNotExistsError(NodeManBaseException):
    ERROR_CODE = 37
    MESSAGE = _("主机的安装通道不存在，请重新选择")


class PluginUploadError(NodeManBaseException):
    MESSAGE = _("插件上传失败")
    MESSAGE_TPL = _("插件上传失败: plugin_name -> {plugin_name}, error -> {error}")
    ERROR_CODE = 38
