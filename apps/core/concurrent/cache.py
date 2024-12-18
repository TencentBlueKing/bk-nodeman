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

import typing
import uuid

import ujson as json
import wrapt
from django.conf import settings
from django.core.cache import caches

from apps.prometheus import metrics
from apps.prometheus.helper import observe
from apps.utils.cache import format_cache_key
from apps.utils.redis import RedisDict, RedisList
from env.constants import CacheBackend

DEFAULT_CACHE_TIME = 60 * 15


class FuncCacheDecorator:

    cache_time: int = DEFAULT_CACHE_TIME

    def __init__(self, cache_time: typing.Optional[int] = None, uuid_cache_enable: bool = False):
        """
        :param cache_time: 缓存事件（秒）
        """
        self.cache_time = cache_time or DEFAULT_CACHE_TIME
        self.uuid_cache_enable = uuid_cache_enable

    def get_from_cache(self, using: str, key: str) -> typing.Any:
        cache = caches[using]
        func_result = cache.get(key, None)
        if func_result is None:
            return func_result

        if using == CacheBackend.DB.value:
            return json.loads(func_result)

        if self.uuid_cache_enable:
            if isinstance(func_result, str) and func_result.startswith("data_backend_redis"):
                data_type = func_result.split("_")[-2]
                if data_type == "dict":
                    return RedisDict(cache_uuid_key=func_result)
                elif data_type == "list":
                    return RedisList(cache_uuid_key=func_result)

        return func_result

    def set_to_cache(self, using: str, key: str, value: typing.Any):
        cache = caches[using]
        if using == CacheBackend.DB.value:
            value = json.dumps(value)

        if self.uuid_cache_enable:
            # 变量上下文会将原本的uuid_key删除，这里重新命名，即可达到缓存目的
            new_uuid_key = None
            if isinstance(value, RedisDict):
                new_uuid_key = f"data_backend_redis_dict_{uuid.uuid4().hex}"
            elif isinstance(value, RedisList):
                new_uuid_key = f"data_backend_redis_list_{uuid.uuid4().hex}"

            if new_uuid_key:
                value._update_redis_expiry(self.cache_time)
                value.client.rename(value.uuid_key, new_uuid_key)
                value.cache_uuid_key = new_uuid_key
                value = new_uuid_key

        cache.set(key, value, self.cache_time)

    def ttl_from_cache(self, using: str, key: str) -> int:
        ttl: int = 0
        try:
            ttl = caches[using].ttl(key)
        except Exception:
            pass
        return ttl

    @wrapt.decorator
    def __call__(
        self,
        wrapped: typing.Callable,
        instance: typing.Any,
        args: typing.Tuple[typing.Any],
        kwargs: typing.Dict[str, typing.Any],
    ) -> typing.Any:
        """
        :param wrapped: 被装饰的函数或类方法
        :param instance:
            - 如果被装饰者为普通类方法，该值为类实例
            - 如果被装饰者为 classmethod / 类方法，该值为类
            - 如果被装饰者为类/函数/静态方法，该值为 None
        :param args: 位置参数
        :param kwargs: 关键字参数
        :return:
        """
        func_result: typing.Any = None
        func_name: str = wrapped.__name__
        use_fast_cache: bool = False
        get_cache: bool = kwargs.pop("get_cache", False)
        tolerance_time: int = kwargs.pop("tolerance_time", 0)
        cache_key: str = format_cache_key(wrapped, *args, **kwargs)
        master_labels: typing.Dict = {"type": "master", "backend": settings.CACHE_BACKEND, "method": func_name}
        if tolerance_time:
            master_labels["type"] = master_labels["type"] + "_fast"
            ttl: int = self.ttl_from_cache(using=settings.CACHE_BACKEND, key=cache_key)
            if ttl != 0 and ttl + tolerance_time >= self.cache_time:
                use_fast_cache = True

        metrics.app_core_cache_decorator_requests_total.labels(get_cache=get_cache, **master_labels).inc()

        if get_cache or use_fast_cache:
            with observe(metrics.app_core_cache_decorator_get_duration_seconds, **master_labels):
                func_result = self.get_from_cache(using=settings.CACHE_BACKEND, key=cache_key)

        if func_result is None:
            # 无需从缓存中获取数据或者缓存中没有数据，则执行函数得到结果，并设置缓存
            func_result = wrapped(*args, **kwargs)
            with observe(metrics.app_core_cache_decorator_set_duration_seconds, **master_labels):
                self.set_to_cache(using=settings.CACHE_BACKEND, key=cache_key, value=func_result)
        elif get_cache or use_fast_cache:
            # cache hit
            metrics.app_core_cache_decorator_hits_total.labels(get_cache=get_cache, **master_labels).inc()

        # 缓存预热
        if settings.CACHE_ENABLE_PREHEAT:
            cache_using: str = (CacheBackend.DB.value, CacheBackend.REDIS.value)[
                settings.CACHE_BACKEND == CacheBackend.DB.value
            ]
            preheat_value: typing.Any = None
            slave_labels: typing.Dict = {"type": "slave", "backend": cache_using, "method": func_name}

            metrics.app_core_cache_decorator_requests_total.labels(get_cache=get_cache, **slave_labels).inc()

            if get_cache:
                with observe(metrics.app_core_cache_decorator_get_duration_seconds, **slave_labels):
                    preheat_value = self.get_from_cache(using=cache_using, key=cache_key)

            if preheat_value is None:
                with observe(metrics.app_core_cache_decorator_set_duration_seconds, **slave_labels):
                    self.set_to_cache(using=cache_using, key=cache_key, value=func_result)
            elif get_cache:
                metrics.app_core_cache_decorator_hits_total.labels(get_cache=get_cache, **slave_labels).inc()

        return func_result
