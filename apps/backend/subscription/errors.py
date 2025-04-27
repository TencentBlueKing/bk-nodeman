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


from django.utils.translation import gettext_lazy as _

from apps.exceptions import AppBaseException


class SubscriptionError(AppBaseException):
    MODULE_CODE = 10000


class SubscriptionNotExist(AppBaseException):
    """订阅不存在"""

    ERROR_CODE = 1
    MESSAGE = _("订阅不存在")
    MESSAGE_TPL = _("订阅({subscription_id})不存在")


class ActionCanNotBeNone(AppBaseException):
    """主动触发订阅，当scope存在时，action不能为空"""

    ERROR_CODE = 2
    MESSAGE = _("Actions不能为None")
    MESSAGE_TPL = _("当scope存在时，actions不能空")


class SubscriptionTaskNotExist(AppBaseException):
    """订阅任务不存在"""

    ERROR_CODE = 3
    MESSAGE = _("订阅任务不存在")
    MESSAGE_TPL = _("订阅任务({task_id})不存在")


class InstanceTaskIsRunning(AppBaseException):
    """实例有执行中任务"""

    ERROR_CODE = 3
    MESSAGE = _("实例存在运行中任务")
    MESSAGE_TPL = _("实例存在运行中任务，避免重复下发")


class ConfigRenderFailed(AppBaseException):
    """实例有执行中任务"""

    ERROR_CODE = 4
    MESSAGE = _("配置文件渲染失败")
    MESSAGE_TPL = _("配置文件[{name}]渲染失败，原因：{msg}")


class PipelineExecuteFailed(AppBaseException):
    """pipeline 执行失败"""

    ERROR_CODE = 5
    MESSAGE = _("Pipeline任务执行失败")
    MESSAGE_TPL = _("Pipeline任务执行失败，原因：{msg}")


class PipelineTreeParseError(AppBaseException):
    """pipeline 任务树解析失败"""

    ERROR_CODE = 6
    MESSAGE = _("Pipeline任务树解析失败")
    MESSAGE_TPL = _("Pipeline任务树解析失败")


class SubscriptionInstanceRecordNotExist(AppBaseException):
    """订阅实例记录不存在"""

    ERROR_CODE = 7
    MESSAGE = _("订阅任务实例不存在")
    MESSAGE_TPL = _("订阅任务实例不存在")


class PipelineDuplicateExecution(AppBaseException):
    """pipeline 执行失败"""

    ERROR_CODE = 8
    MESSAGE = _("Pipeline任务重复执行")
    MESSAGE_TPL = _("Pipeline任务已经开始执行，不能重复执行")


class SubscriptionInstanceEmpty(AppBaseException):
    """订阅实例记录为空"""

    ERROR_CODE = 9
    MESSAGE = _("订阅任务实例为空")
    MESSAGE_TPL = _("订阅任务实例为空，不再创建订阅任务")


class PluginValidationError(AppBaseException):
    """插件校验错误"""

    ERROR_CODE = 10
    MESSAGE = _("插件校验错误")
    MESSAGE_TPL = _("{msg}")


class MultipleObjectError(AppBaseException):
    """目标选择器传了不同的bk_obj_id"""

    ERROR_CODE = 11
    MESSAGE = _("不允许同一个请求传不同目标")
    MESSAGE_TPL = _("{msg}")


class PackageNotExists(AppBaseException):
    ERROR_CODE = 12
    MESSAGE = _("插件包不存在")
    MESSAGE_TPL = _("{msg}")


class SubscriptionStepNotExist(AppBaseException):
    """订阅任务不存在"""

    ERROR_CODE = 13
    MESSAGE = _("订阅步骤不存在")
    MESSAGE_TPL = _("订阅步骤({step_id})不存在")


class CreateSubscriptionTaskError(AppBaseException):
    ERROR_CODE = 14
    MESSAGE = _("创建任务失败")
    MESSAGE_TPL = _("创建任务失败: {err_msg}")


class SubscriptionTaskNotReadyError(AppBaseException):
    ERROR_CODE = 15
    MESSAGE = _("订阅任务未准备就绪，请稍后再尝试查询")
    MESSAGE_TPL = _("订阅任务未准备就绪，请稍后再尝试查询。task_id_list: {task_id_list}")


class NoRunningInstanceRecordError(AppBaseException):
    ERROR_CODE = 16
    MESSAGE = _("不存在运行中的任务，请确认")
    MESSAGE_TPL = _("订阅[id:{subscription_id}]不存在运行中的任务，请确认")


class SubscriptionUpdateError(AppBaseException):
    """订阅任务不存在"""

    ERROR_CODE = 17
    MESSAGE = _("订阅更新错误")
    MESSAGE_TPL = _("订阅[id:{subscription_id}]更新错误: {msg}")


class PluginScriptValidationError(AppBaseException):
    """插件操作脚本校验错误"""

    ERROR_CODE = 18
    MESSAGE = _("插件操作脚本校验错误")
    MESSAGE_TPL = _("{msg}")


class SubscriptionIncludeGrayBizError(AppBaseException):
    """订阅任务包含Gse2.0灰度业务"""

    ERROR_CODE = 19
    MESSAGE = _("订阅任务包含Gse2.0灰度业务，任务将暂缓执行无需重复点击")
    MESSAGE_TPL = _("订阅任务包含Gse2.0灰度业务，任务将暂缓执行无需重复点击")


class SubscriptionNotDeletedCantOperateError(AppBaseException):
    ERROR_CODE = 20
    MESSAGE = _("订阅未被删除，无法操作")
    MESSAGE_TPL = _("订阅ID:{subscription_id}未被删除，无法进行清理操作，可增加参数is_force=true强制操作")
