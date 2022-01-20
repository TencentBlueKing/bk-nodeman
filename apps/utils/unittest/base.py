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
from collections import ChainMap, defaultdict
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Tuple

from rest_framework import status
from rest_framework.test import APIClient

# DEFAULT_CONTENT_TYPE & DEFAULT_FORMAT 不能同时设置
DEFAULT_CONTENT_TYPE = None  # or "application/json"

DEFAULT_FORMAT = "json"


class CustomAPIClient(APIClient):
    # 通用请求参数，同键覆盖策略 data > common_request_data
    common_request_data: Optional[Dict[str, Any]] = None

    def __init__(self, enforce_csrf_checks=False, **defaults):
        self.common_request_data = {}
        super().__init__(enforce_csrf_checks=enforce_csrf_checks, **defaults)

    @staticmethod
    def assert_response(response) -> Dict[str, Any]:
        if response.status_code != status.HTTP_200_OK:
            print(json.dumps(json.loads(response.content)))
            assert False
        else:
            return json.loads(response.content)

    def process_request_data(self, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        请求参数预处理
        :param data: 请求参数
        :return: 返回处理后的data
        """
        if data is None:
            return self.common_request_data

        return dict(ChainMap(data, self.common_request_data))

    def get(self, path, data=None, follow=False, **extra):
        data = self.process_request_data(data)
        response = super().get(path=path, data=data, follow=follow, **extra)
        return self.assert_response(response)

    def post(self, path, data=None, format=DEFAULT_FORMAT, content_type=DEFAULT_CONTENT_TYPE, follow=False, **extra):
        data = self.process_request_data(data)
        response = super().post(path=path, data=data, format=format, content_type=content_type, follow=follow, **extra)
        return self.assert_response(response)

    def put(self, path, data=None, format=DEFAULT_FORMAT, content_type=DEFAULT_CONTENT_TYPE, follow=False, **extra):
        data = self.process_request_data(data)
        response = super().put(path=path, data=data, format=format, content_type=content_type, follow=follow, **extra)
        return self.assert_response(response)

    def delete(self, path, data=None, format=DEFAULT_FORMAT, content_type=DEFAULT_CONTENT_TYPE, follow=False, **extra):
        data = self.process_request_data(data)
        response = super().delete(
            path=path, data=data, format=format, content_type=content_type, follow=follow, **extra
        )
        return self.assert_response(response)


class CallRecord:
    args: Tuple[Any] = None
    kwargs: Dict[str, Any] = None
    result: Any = None
    ex: Exception = None
    is_success: bool = None

    def __init__(self, args: Tuple[Any], kwargs: Dict[str, Any]):
        self.args = args
        self.kwargs = kwargs
        self.is_success = True


class CallRecorder:
    """函数调用记录器，仅用于测试"""

    # 调用记录
    record: Optional[Dict[Callable, List[CallRecord]]] = None
    # 记录锁
    _lock: Optional[Lock] = None

    def __init__(self):
        self.record = defaultdict(list)
        self._lock = Lock()

    def start(self, func: Callable, key: Any = None):
        """
        开始记录某个函数的调用情况，参考装饰器实现
        :param key:
        :param func:
        :return:
        """

        def recorder(*args, **kwargs):
            with self._lock:
                record = CallRecord(args=args, kwargs=kwargs)
                self.record[key or func].append(record)

                try:
                    record.result = func(*args, **kwargs)
                except Exception as ex:
                    record.exec = ex
                    record.is_success = False
                else:
                    return record.result

        return recorder
