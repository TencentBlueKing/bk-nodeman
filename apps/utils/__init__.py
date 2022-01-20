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
import abc

from django.conf import settings


class APIModel(abc.ABC):
    KEYS = []

    @classmethod
    def init_by_data(cls, data):
        kvs = {_key: data[_key] for _key in cls.KEYS}
        o = cls(**kvs)
        o._data = data
        return o

    def __init__(self, *args, **kwargs):
        self._data = None

    def _get_data(self):
        """
        获取基本数据方法，用于给子类重载
        """
        raise NotImplementedError

    @property
    def data(self):
        if self._data is None:
            self._data = self._get_data()

        return self._data


def get_oath_cookies_params() -> dict:
    # 企业版给默认值bk_token，其他版本从settings中获取
    return getattr(settings, "OAUTH_COOKIES_PARAMS", {"bk_token": "bk_token"})


def build_auth_args(request):
    """
    组装认证信息
    """
    # auth_args 用于ESB身份校验
    auth_args = {}
    if request is None:
        return auth_args

    ignore_fields = ["rtx"]
    for key, value in get_oath_cookies_params().items():
        if value in request.COOKIES and key not in ignore_fields:
            auth_args.update({key: request.COOKIES[value]})

    return auth_args


def remove_auth_args(params):
    """
    移除认证信息，用于使用admin请求时排除bk_token等信息
    :param params:
    :return:
    """
    for key in settings.OAUTH_COOKIES_PARAMS.keys():
        params.pop(key, None)
    return params
