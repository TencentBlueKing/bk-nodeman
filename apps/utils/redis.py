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
import uuid
from collections.abc import Iterator
from typing import Any, Generator, Iterable, Optional, Tuple

from _collections_abc import dict_keys
from django.conf import settings
from django_redis import get_redis_connection

from apps.node_man.constants import DataBackend, DCReturnType

# 过期时间为1小时
REDIS_CACHE_DATA_TIMEOUT = 60 * 60
# 每次取值的长度
REDIS_CACHE_DATA_LENGTH = 1000


class RedisHashScanner:
    def __init__(self, key: str, match: Optional[str] = None, count: int = REDIS_CACHE_DATA_LENGTH):
        self.redis_client = get_redis_connection()
        self.key = key
        self.match = match
        self.count = count

    def __iter__(self) -> Generator[Tuple[str, str], None, None]:
        cursor = "0"
        while cursor != 0:
            cursor, data = self.redis_client.hscan(self.key, cursor=cursor, match=self.match, count=self.count)
            for field, value in data.items():
                yield field, json.loads(value)


class RedisHashValuesScanner(RedisHashScanner):
    def __iter__(self) -> Generator[Tuple[str, str], None, None]:
        cursor = "0"
        while cursor != 0:
            cursor, data = self.redis_client.hscan(self.key, cursor=cursor, match=self.match, count=self.count)
            for _, value in data.items():
                yield json.loads(value)


class RedisListIterator:
    def __init__(self, key: str, batch_size: int = REDIS_CACHE_DATA_LENGTH):
        self.redis_client = get_redis_connection()
        self.key = key
        self.batch_size = batch_size

    def __iter__(self) -> Generator[Tuple[str, str], None, None]:
        start = 0
        while True:
            end = start + self.batch_size - 1
            elements = self.redis_client.lrange(self.key, start, end)
            if not elements:
                break
            yield from (json.loads(element) for element in elements)
            start += self.batch_size


class RedisDataBase:
    def __init__(self, uuid_key: str = None, cache_uuid_key: str = None):
        self.cache_uuid_key = cache_uuid_key
        self.uuid_key = uuid_key or f"{uuid.uuid4().hex}"
        self.client = get_redis_connection()

    def _update_redis_expiry(self, cache_time=None):
        self.client.expire(self.cache_uuid_key or self.uuid_key, cache_time or REDIS_CACHE_DATA_TIMEOUT)

    def __del__(self):
        self.client.delete(self.uuid_key)

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.__del__()


class RedisDict(RedisDataBase, dict):
    def __setitem__(self, key, value):
        self.client.hset(self.cache_uuid_key or self.uuid_key, key, json.dumps(value))
        self._update_redis_expiry()

    def update(self, *args, **kwargs):
        temp_dict = {}
        for k, v in dict(*args, **kwargs).items():
            temp_dict[k] = json.dumps(v)
        if temp_dict:
            self.client.hset(self.cache_uuid_key or self.uuid_key, mapping=temp_dict)
        self._update_redis_expiry()

    def __getitem__(self, key: Any) -> Any:
        return json.loads(self.client.hget(self.cache_uuid_key or self.uuid_key, key) or "null")

    def __len__(self) -> int:
        return self.client.hlen(self.cache_uuid_key or self.uuid_key)

    def keys(self) -> dict_keys:
        return self.client.hkeys(self.cache_uuid_key or self.uuid_key)

    def get(self, key: Any, default=None):
        return self.__getitem__(key) or default

    def values(self):
        return RedisHashValuesScanner(self.cache_uuid_key or self.uuid_key)

    def items(self):
        return RedisHashScanner(self.cache_uuid_key or self.uuid_key)

    def __str__(self):
        return self.uuid_key


class RedisList(RedisDataBase, list):
    def __iter__(self) -> Iterator:
        self.index = 0
        return self

    def __next__(self):
        if self.index < self.client.llen(self.cache_uuid_key or self.uuid_key):
            item = self.client.lindex(self.cache_uuid_key or self.uuid_key, self.index)
            self.index += 1
            return json.loads(item)
        else:
            raise StopIteration

    def extend(self, iterable: Iterable[Any]) -> None:
        serialized_items = [json.dumps(item) for item in iterable]
        if serialized_items:
            self.client.rpush(self.cache_uuid_key or self.uuid_key, *serialized_items)
            self._update_redis_expiry()

    def append(self, obj: Any) -> None:
        self.client.rpush(self.cache_uuid_key or self.uuid_key, json.dumps(obj))
        self._update_redis_expiry()

    def __len__(self) -> int:
        return self.client.llen(self.cache_uuid_key or self.uuid_key)


class DynamicContainer:
    def __init__(self, return_type: str = DCReturnType.DICT.value, data_backend: str = DataBackend.REDIS.value):

        if settings.DATA_BACKEND == DataBackend.REDIS.value or data_backend == DataBackend.REDIS.value:
            self._container = RedisDict() if return_type == DCReturnType.DICT.value else RedisList()
        else:
            self._container = {} if return_type == DCReturnType.DICT.value else []

    @property
    def container(self):
        return self._container
