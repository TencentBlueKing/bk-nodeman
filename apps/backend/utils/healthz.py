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
import hashlib
import pickle
import socket
import time

from django.conf import settings


def get_local_ip():
    """
    Returns the actual ip of the local machine.
    This code figures out what source address would be used if some traffic
    were to be sent out to some well known address on the Internet. In this
    case, a Google DNS server is used, but the specific address does not
    matter much.  No traffic is actually sent.

    stackoverflow上有人说用socket.gethostbyname(socket.getfqdn())
    但实测后发现有些机器会返回127.0.0.1
    """
    try:
        csock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        csock.connect(("8.8.8.8", 80))
        (addr, port) = csock.getsockname()
        csock.close()
        return addr
    except socket.error:
        return "127.0.0.1"


class CallCache(object):
    def __init__(self, obj, timeout=None):
        self._object = obj
        self._timeout = timeout or getattr(settings, "DEFAULT_CALL_CACHE_TIMEOUT", 60)
        self._results = {}

    def __getattr__(self, item):
        attr = self.__class__(getattr(self._object, item), self._timeout)
        setattr(self, item, attr)
        return attr

    def __call__(self, *args, **kwargs):
        key = hashlib.new(
            "md5",
            pickle.dumps(
                {
                    "args": args,
                    "kwargs": kwargs,
                }
            ),
        ).hexdigest()
        now = time.time()
        cached = self._results.get(key)
        if cached and cached["time"] + self._timeout >= now:
            return cached["result"]

        result = self._object(*args, **kwargs)
        self._results[key] = {
            "result": result,
            "time": now,
        }
        return result
