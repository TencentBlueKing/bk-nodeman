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


class TagBaseException(CoreBaseException):
    MODULE_CODE = 3003


class TargetNotExistError(TagBaseException):
    MESSAGE_TPL = _("目标不存在：target_id -> {target_id}")
    MESSAGE = _("目标不存在")
    ERROR_CODE = 1


class TagNotExistError(TagBaseException):
    MESSAGE_TPL = _("标签不存在：target_id -> {target_id}, target_type -> {target_type}")
    MESSAGE = _("标签不存在")
    ERROR_CODE = 2


class PublishTagVersionError(TagBaseException):
    MESSAGE_TPL = _("发布标签版本错误：{err_msg}")
    MESSAGE = _("发布标签版本错误")
    ERROR_CODE = 3


class TargetHelperNotExistError(TagBaseException):
    MESSAGE_TPL = _("目标处理器不存在：target_type -> {target_type}")
    MESSAGE = _("目标处理器不存在")
    ERROR_CODE = 4


class TagAlreadyExistsError(TagBaseException):
    MESSAGE_TPL = _("标签已存在")
    MESSAGE = _("标签已存在")
    ERROR_CODE = 5


class TagInvalidNameError(TagBaseException):
    MESSAGE_TPL = _("标签名非法：{err_msg}")
    MESSAGE = _("标签名非法")
    ERROR_CODE = 6


class ValidationError(TagBaseException):
    MESSAGE = _("参数验证失败")
    ERROR_CODE = 7
