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

import re
import typing
from concurrent.futures import ThreadPoolExecutor, as_completed

import ujson as json
import wrapt
from django.conf import settings
from django.core.cache import caches

from apps.prometheus import metrics
from apps.prometheus.helper import observe
from apps.utils.cache import format_cache_key
from env.constants import CacheBackend

DEFAULT_CACHE_TIME = 60 * 15


class FuncCacheDecorator:

    cache_time: int = DEFAULT_CACHE_TIME
    piece_length: int = settings.CACHE_PIECE_LENGTH or 1 * 1024 * 1024

    def __init__(self, cache_time: typing.Optional[int] = None):
        """
        :param cache_time: 缓存事件（秒）
        """
        self.cache_time = cache_time or DEFAULT_CACHE_TIME

    def get_from_cache(self, using: str, key: str) -> typing.Any:
        cache = caches[using]
        func_result = cache.get(key, None)
        if func_result is None:
            return func_result

        if self.check_is_split(key, func_result):
            func_result = self.join_splitted_cache(using, func_result)
        try:
            return json.loads(func_result)
        except Exception:
            return func_result

    def set_to_cache(self, using: str, key: str, value: typing.Any):
        cache = caches[using]
        value = json.dumps(value)

        if len(value) < self.piece_length:
            return cache.set(key, value, self.cache_time)

        split_cache = self.split_cache(key, value)
        cache.set(key, list(split_cache.keys()), self.cache_time)
        for split_key, split_value in split_cache.items():
            cache.set(split_key, split_value, self.cache_time)

    def ttl_from_cache(self, using: str, key: str) -> int:
        ttl: int = 0
        try:
            ttl = caches[using].ttl(key)
        except Exception:
            pass
        return ttl

    def split_cache(self, key: str, value: str) -> typing.Dict[str, str]:
        parts = [value[i : i + self.piece_length] for i in range(0, len(value), self.piece_length)]
        return {f"{key}|{num}": part for num, part in enumerate(parts)}

    def check_is_split(self, key: str, cache_result: typing.Any) -> bool:
        if not isinstance(cache_result, list):
            return False

        list_result = list(cache_result)
        pattern = re.compile(rf"{key}|\d+")
        return bool(re.search(pattern, list_result[0]))

    def join_splitted_cache(self, using: str, keys: typing.List[str]) -> typing.Any:
        cache = caches[using]
        with ThreadPoolExecutor(max_workers=settings.CONCURRENT_NUMBER) as ex:
            futures = {ex.submit(cache.get, key): key for key in keys}

        results = {}
        for future in as_completed(futures):
            key = futures[future]
            results[key] = future.result()

        sorted_keys = sorted(results.keys(), key=lambda x: int(x.split("|")[-1]))
        return "".join(str(results[key]) for key in sorted_keys)

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
            metrics.app_core_cache_decorator_hits_total.labels(**master_labels).inc()

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
                metrics.app_core_cache_decorator_hits_total.labels(**slave_labels).inc()

        return func_result
