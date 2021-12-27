# -*- coding: utf-8 -*-
import logging
import threading
import traceback

from django.conf import settings
from redis import StrictRedis

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


REDIS_INST: StrictRedis = RedisInstSingleTon.get_inst()
