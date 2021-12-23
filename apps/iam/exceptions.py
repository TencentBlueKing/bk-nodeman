# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making 蓝鲸 (Blueking) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""
from django.conf import settings
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy as _lazy

from apps.exceptions import AppBaseException, ErrorCode


class BaseIAMError(AppBaseException):
    MODULE_CODE = ErrorCode.IAM_CODE
    MESSAGE = _lazy("权限中心异常")


class ActionNotExistError(BaseIAMError):
    ERROR_CODE = 1
    MESSAGE = _lazy("动作ID不存在")


class ResourceNotExistError(BaseIAMError):
    ERROR_CODE = 2
    MESSAGE = _lazy("资源ID不存在")


class GetSystemInfoError(BaseIAMError):
    ERROR_CODE = 3
    MESSAGE = _lazy("获取系统信息错误")


class PermissionDeniedError(BaseIAMError):
    ERROR_CODE = 3
    MESSAGE = _lazy("权限校验不通过")

    def __init__(self, action_name, permission, apply_url=settings.BK_IAM_SAAS_HOST):
        message = _("当前用户无 [{action_name}] 权限").format(action_name=action_name)
        data = {
            "permission": permission,
            "apply_url": apply_url,
        }
        super(PermissionDeniedError, self).__init__(message, data=data, code="9900403")
