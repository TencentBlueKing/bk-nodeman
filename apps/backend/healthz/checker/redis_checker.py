# coding: utf-8
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""


import time
from contextlib import contextmanager

from apps.backend.utils.healthz import CallCache
from apps.backend.utils.redis import REDIS_INST
from common.log import logger

from .checker import CheckerRegister

register = CheckerRegister.redis


@contextmanager
def with_client_of_fail(result):
    try:
        yield CallCache(REDIS_INST)
    except Exception as err:
        logger.exception(err)
        raise result.fail(str(err))


@register.status()
def cache_status(manager, result, key="uptime_in_seconds"):
    """Redis 状态"""
    with with_client_of_fail(result) as client:
        result.ok(str(client.info()[key]))


CACHE_CHECK_KEY = "-- healthz checking key --"


@register.write.status()
def cache_write_status(manager, result, key=None):
    """Redis 可写状态"""
    key = key or CACHE_CHECK_KEY
    with with_client_of_fail(result) as client:
        result.ok(str(client.set(key, time.time())))


@register.read.status()
def cache_read_status(manager, result, key=None):
    """Redis 可读状态"""
    key = key or CACHE_CHECK_KEY
    with with_client_of_fail(result) as client:
        result.ok(str(client.get(key)))


def cache_methods(manager, result, method_name, method_args=(), **kwargs):
    with with_client_of_fail(result) as client:
        method = getattr(client, method_name)
        result.ok(str(method(*method_args, **kwargs)))


REDIS_METHODS = ["llen", "ttl", "dbsize", "exists", "hexists", "hlen", "hgetall", "scard"]
