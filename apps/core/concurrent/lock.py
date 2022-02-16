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

import logging
import math
import typing
import uuid

from redis import StrictRedis

from apps.backend.utils import redis

from . import constants

logger = logging.getLogger("app")


class RedisLock:
    redis_inst: StrictRedis = None

    def __init__(self, lock_name: str, lock_expire: int = None, redis_inst: typing.Optional[StrictRedis] = None):
        self.lock_name = lock_name
        self.lock_expire = lock_expire or constants.DEFAULT_LOCK_EXPIRE
        self.redis_inst = redis_inst or redis.RedisInstSingleTon.get_inst()

    def __enter__(self):
        if self.lock_name is None:
            logger.error("can not use None key")
            return None
        self.identifier = self.acquire_lock_with_expire(self.lock_name)
        return self.identifier

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.identifier is None:
            return False
        self.release_lock(self.lock_name, self.identifier)

    def acquire_lock_with_expire(self, lock_name):
        """
        获得锁
        :param lock_name: 锁名
        :return: success: identifier failed: None
        """
        identifier = str(uuid.uuid4())
        lock_name = f"lock:{lock_name}"
        lock_timeout = int(math.ceil(self.lock_expire))
        # 如果不存在这个锁则加锁并设置过期时间，避免死锁
        if self.redis_inst.set(lock_name, identifier, ex=lock_timeout, nx=True):
            return identifier
        # 锁已存在并被持有，此时放弃排队竞争，直接返回None
        return None

    def release_lock(self, lock_name, identifier):
        """
        释放锁
        :param lock_name: 锁的名称
        :param identifier: 锁的标识
        :return:
        """
        unlock_script = """
        if redis.call("get",KEYS[1]) == ARGV[1] then
            return redis.call("del",KEYS[1])
        else
            return 0
        end
        """
        lock_name = f"lock:{lock_name}"
        unlock = self.redis_inst.register_script(unlock_script)
        result = unlock(keys=[lock_name], args=[identifier])
        return result
