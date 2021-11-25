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


class ErrorCode(object):
    # 平台错误码
    PLAT_CODE = 3800000
    WEB_CODE = 0


class AppBaseException(Exception):
    MODULE_CODE = 0
    ERROR_CODE = 50000
    MESSAGE = _("系统异常")
    MESSAGE_TPL = None

    def __init__(self, context=None, data=None, **kwargs):
        """
        @param {String} code 自动设置异常状态码
        """
        if context is None:
            context = {}

        self.code = ErrorCode.PLAT_CODE + self.MODULE_CODE + self.ERROR_CODE
        self.errors = kwargs.get("errors")

        # 优先使用第三方系统的错误编码
        if kwargs.get("code"):
            self.code = kwargs["code"]

        if self.MESSAGE_TPL:
            try:
                context.update(kwargs)
                self.message = self.MESSAGE_TPL.format(**context)
            except Exception:
                self.message = context
        else:
            self.message = context or self.MESSAGE

        # 当异常有进一步处理时，需返回data
        self.data = data

    def __str__(self):
        return "[{}] {}".format(self.code, self.message)


class ApiError(AppBaseException):
    pass


class ValidationError(AppBaseException):
    MESSAGE = _("参数验证失败")
    ERROR_CODE = 1


class ApiResultError(ApiError):
    MESSAGE = _("远程服务请求结果异常")
    ERROR_CODE = 2


class ComponentCallError(AppBaseException):
    MESSAGE = _("组件调用异常")
    ERROR_CODE = 3


class BizNotExistError(AppBaseException):
    MESSAGE = _("业务不存在")
    ERROR_CODE = 4


class LanguageDoseNotSupported(AppBaseException):
    MESSAGE = _("语言不支持")
    ERROR_CODE = 5


class PermissionError(AppBaseException):
    MESSAGE = _("权限不足")
    ERROR_CODE = 403


class ApiRequestError(ApiError):
    # 属于严重的场景，一般为第三方服务挂了，ESB调用超时
    MESSAGE = _("服务不稳定，请检查组件健康状况")
    ERROR_CODE = 15


class BkJwtClientException(AppBaseException):
    ERROR_CODE = 16
    MESSAGE = _("请升级blueapps至最新版本")


class BkJwtVerifyException(AppBaseException):
    ERROR_CODE = 17
    MESSAGE = _("获取JWT信息异常")


class BkJwtVerifyFailException(AppBaseException):
    ERROR_CODE = 18
    MESSAGE = _("JWT校验失败")


class AuthOverdueException(AppBaseException):
    ERROR_CODE = 19
    MESSAGE = _("认证信息已过期, 请重装并填入认证信息")


# 背景：后台序列化逻辑改造导致接口校验错误码默认指向 ValidationError(ERROR_CODE=1)
# 作用：部分接口需要兼容老的校验错误码，兼容调用方使用错误码分类异常的情况
class BackendValidationError(AppBaseException):
    ERROR_CODE = 100
    MESSAGE = _("参数验证失败")
