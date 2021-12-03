# -*- coding: utf-8 -*-
import logging
import math
import threading
import traceback
import uuid

from django.conf import settings
from rediscluster import StrictRedisCluster

from apps.backend.api.constants import POLLING_INTERVAL
from pipeline.apps import CLIENT_GETTER

logger = logging.getLogger("app")


class RedisInstSingleTon:
    _inst_lock = threading.Lock()
    _inst_name = "redis_inst"

    @classmethod
    def get_inst(cls):
        if hasattr(cls, cls._inst_name):
            return getattr(cls, cls._inst_name)
        with cls._inst_lock:
            if hasattr(cls, cls._inst_name):
                return getattr(cls, cls._inst_name)
            if hasattr(settings, "REDIS"):
                mode = settings.REDIS.get("mode") or "single"
                try:
                    setattr(cls, cls._inst_name, CLIENT_GETTER[mode]())
                except Exception:
                    # fall back to single node mode
                    logger.error("redis client init error: %s" % traceback.format_exc())
                    setattr(cls, cls._inst_name, None)
            else:
                logger.error("can not find REDIS in settings!")
                setattr(cls, cls._inst_name, None)
        return getattr(cls, cls._inst_name)


class RedisLock:
    redis_inst = RedisInstSingleTon.get_inst()

    def __init__(self, lock_name: str = None, lock_expire: int = POLLING_INTERVAL * 4):
        self.lock_name = lock_name
        self.lock_expire = lock_expire

    def __enter__(self):
        if self.lock_name is None:
            logger.error("can not use None key")
            return None
        self.identifier = self.acquire_lock_with_timeout(self.lock_name, self.lock_expire)
        return self.identifier

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.identifier is None:
            return False
        self.release_lock(self.lock_name, self.identifier)

    def acquire_lock_with_timeout(self, lock_name, lock_expire: int = POLLING_INTERVAL * 4):
        """
        获得锁
        :param lock_name: 锁名
        :param lock_expire: 锁过期时间
        :return: success: identifier failed: None
        """
        identifier = str(uuid.uuid4())
        lock_name = f"lock:{lock_name}"
        lock_timeout = int(math.ceil(lock_expire))
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


REDIS_INST: StrictRedisCluster = RedisInstSingleTon.get_inst()
