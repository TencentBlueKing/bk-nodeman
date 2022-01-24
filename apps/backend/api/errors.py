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


class EmptyResponseError(AppBaseException):
    """无响应"""

    code = 3801000
    name = _("无响应")
    message_tpl = _("API({api_name})没有返回响应")


class FalseResultError(AppBaseException):
    """接口调用错误"""

    code = 3801001
    name = _("接口调用错误")
    message_tpl = _("API({api_name})调用出错：{error_message}")


class JobPollTimeout(AppBaseException):
    """Job轮询超时"""

    code = 3801002
    name = _("Job轮询超时")
    message_tpl = _("Job任务({job_instance_id})轮询超时")


class GsePollTimeout(AppBaseException):
    """GSE轮询超时"""

    code = 3801004
    name = _("GSE轮询超时")
    message_tpl = _("GSE任务({task_id})轮询超时")
