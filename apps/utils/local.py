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
import uuid
from threading import local

from apps.exceptions import AppBaseException

"""
管理线程变量
"""
_local = local()


def activate_request(request, request_id=None):
    """
    激活request线程变量
    """
    if not request_id:
        request_id = str(uuid.uuid4())
    request.request_id = request_id
    _local.request = request
    return request


def get_request():
    """
    获取线程请求request
    """
    try:
        return _local.request
    except AttributeError:
        raise AppBaseException("request thread error!")


def get_request_id():
    """
    获取request_id
    """
    try:
        return get_request().request_id
    except AppBaseException:
        return str(uuid.uuid4())


def get_request_username():
    """
    获取请求的用户名
    """
    try:
        return get_request().user.username
    except Exception:
        return ""


def get_request_app_code():
    """
    获取线程请求中的 APP_CODE，非线程请求返回空字符串
    """
    try:
        return _local.bk_app_code
    except AttributeError:
        return ""


def set_local_param(key, value):
    """
    设置自定义线程变量
    """
    setattr(_local, key, value)


def del_local_param(key):
    """
    删除自定义线程变量
    """
    if hasattr(_local, key):
        delattr(_local, key)


def get_local_param(key, default=None):
    """
    获取线程变量
    """
    return getattr(_local, key, default)
