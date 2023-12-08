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

import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

import wrapt


class RetryHandler:
    """重试处理器"""

    # 重试间隔
    interval: float = None
    # 重试次数
    retry_times: int = None
    # 需要重试的异常类型
    exception_types: List[Type[Exception]] = None

    def __init__(
        self, interval: float = 0, retry_times: int = 1, exception_types: Optional[List[Type[Exception]]] = None
    ):
        self.interval = max(interval, 0)
        self.retry_times = max(retry_times, 0)
        self.exception_types = exception_types or [Exception]

    @wrapt.decorator
    def __call__(self, wrapped: Callable, instance: Optional[object], args: Tuple[Any], kwargs: Dict[str, Any]):
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
        call_times = self.retry_times + 1
        while call_times > 0:
            call_times = call_times - 1
            try:
                return wrapped(*args, **kwargs)
            except Exception as exc_val:
                # 重试次数已用完或者异常捕获未命中时，抛出原异常
                if call_times == 0 or not self.hit_exceptions(exc_val):
                    raise
                # 休眠一段时间
                time.sleep(self.interval)

    def hit_exceptions(self, exc_val: Exception) -> bool:
        for exception in self.exception_types:
            if isinstance(exc_val, exception):
                return True
        return False
