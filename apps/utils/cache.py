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
import json
from functools import wraps
from typing import Callable, Optional

from django.core.serializers.json import DjangoJSONEncoder
from django_redis.pool import ConnectionFactory as Factory
from django_redis.pool import SentinelConnectionFactory as SentinelFactory
from django_redis.serializers.base import BaseSerializer

from apps.utils.md5 import count_md5

DEFAULT_CACHE_TIME = 60 * 15


class JSONSerializer(BaseSerializer):
    """
    自定义JSON序列化器用于redis序列化
    django-redis的默认JSON序列化器假定`decode_responses`被禁用。
    """

    def dumps(self, value):
        return json.dumps(value, cls=DjangoJSONEncoder)

    def loads(self, value):
        return json.loads(value)


class ConnectionFactoryMixin:
    """自定义ConnectionFactory以注入decode_responses参数"""

    def make_connection_params(self, url):
        kwargs = super().make_connection_params(url)
        kwargs["decode_responses"] = True
        return kwargs


class ConnectionFactory(ConnectionFactoryMixin, Factory):
    pass


class SentinelConnectionFactory(ConnectionFactoryMixin, SentinelFactory):
    pass


def django_cache_key_maker(key: str, key_prefix: str, version: str) -> str:
    """
    自定义缓存键生成函数
    :param key:
    :param key_prefix:
    :param version:
    :return:
    """
    return f"{key_prefix}:v2:{key}"


def class_member_cache(name: Optional[str] = None):
    """
    类成员缓存
    :param name: 缓存名称，为空则使用 _{class_func.__name__}
    :return:
    """

    def class_member_cache_inner(class_func: Callable) -> Callable:
        @wraps(class_func)
        def wrapper(self, *args, **kwargs):

            cache_field = f"_{name or class_func.__name__}"

            cache_member = getattr(self, cache_field, None)
            if cache_member:
                return cache_member
            cache_member = class_func(self, *args, **kwargs)
            setattr(self, cache_field, cache_member)
            return cache_member

        return wrapper

    return class_member_cache_inner


def format_cache_key(func: Callable, *args, **kwargs):
    """计算缓存的key，通过函数名加上参数md5值得到"""
    kwargs.update({"args": args})
    return f"{func.__name__}_{count_md5(kwargs)}"
