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


import inspect
import time
import typing
from contextlib import contextmanager

import wrapt
from prometheus_client import Counter, Gauge, Histogram

from apps.utils import local, sync

HOST_NAME = local.get_hostname()

GetLabelsFuncT = typing.Callable[
    [typing.Callable, typing.Any, typing.Tuple[typing.Any], typing.Dict[str, typing.Any]], typing.Dict[str, typing.Any]
]


def get_call_resource_labels_func(
    wrapped: typing.Callable,
    instance: typing.Any,
    args: typing.Tuple[typing.Any],
    kwargs: typing.Dict[str, typing.Any],
) -> typing.Dict[str, str]:
    source = kwargs.pop("source", "default")
    return {"method": wrapped.__name__, "source": source}


@contextmanager
def observe(histogram: Histogram, **labels):
    start = time.perf_counter()
    yield
    histogram.labels(**labels).observe(time.perf_counter() - start)


class SetupObserve:
    gauge: typing.Optional[Gauge] = None
    counter: typing.Optional[Counter] = None
    histogram: typing.Optional[Histogram] = None
    labels: typing.Optional[typing.Dict[str, typing.Any]] = None
    get_labels_func: typing.Optional[GetLabelsFuncT] = None
    include_exception_histogram: bool = True

    @staticmethod
    def default_get_labels_func(
        wrapped: typing.Callable,
        instance: typing.Any,
        args: typing.Tuple[typing.Any],
        kwargs: typing.Dict[str, typing.Any],
    ) -> typing.Dict[str, str]:
        return {}

    def __init__(
        self,
        gauge: typing.Optional[Gauge] = None,
        counter: typing.Optional[Counter] = None,
        histogram: typing.Optional[Histogram] = None,
        get_labels_func: typing.Optional[GetLabelsFuncT] = None,
        labels: typing.Optional[typing.Dict[str, typing.Any]] = None,
        include_exception_histogram: bool = True,
    ):
        """
        :param 测量指标数组
        :param get_labels_func: 获取标签的方法
        :param labels: 标签
        """
        self.gauge = gauge
        self.counter = counter
        self.histogram = histogram
        self.labels = labels
        self.get_labels_func = get_labels_func or self.default_get_labels_func
        self.include_exception_histogram = include_exception_histogram

    async def wrapped_async_executor(
        self,
        wrapped: typing.Callable,
        instance: typing.Any,
        args: typing.Tuple[typing.Any],
        kwargs: typing.Dict[str, typing.Any],
    ) -> typing.Any:
        """
        实例任务执行器，协程模式
        :param wrapped: 被装饰的函数或类方法
        :param instance: 参考 __init__
        :param args: 位置参数
        :param kwargs: 关键字参数
        :return:
        """

        labels = await sync.sync_to_async(self.get_labels)(wrapped, instance, args, kwargs)
        self.gauge_inc(labels)
        start = time.perf_counter()
        try:
            result = await wrapped(*args, **kwargs)
        except Exception:
            raise
        else:
            if not self.include_exception_histogram:
                self.histogram_observe(labels, start)
            return result
        finally:
            self.gauge_dec(labels)
            if self.include_exception_histogram:
                self.histogram_observe(labels, start)

    def wrapped_executor(
        self,
        wrapped: typing.Callable,
        instance: typing.Any,
        args: typing.Tuple[typing.Any],
        kwargs: typing.Dict[str, typing.Any],
    ):
        """
        实例任务执行器
        :param wrapped: 被装饰的函数或类方法
        :param instance: 基础Pipeline服务
        :param args: 位置参数
        :param kwargs: 关键字参数
        :return:
        """
        labels = self.get_labels(wrapped, instance, args, kwargs)
        self.gauge_inc(labels)
        self.counter_inc(labels)
        start = time.perf_counter()
        try:
            result = wrapped(*args, **kwargs)
        except Exception:
            raise
        else:
            if not self.include_exception_histogram:
                self.histogram_observe(labels, start)
            return result
        finally:
            self.gauge_dec(labels)
            if self.include_exception_histogram:
                self.histogram_observe(labels, start)

    def get_labels(
        self,
        wrapped: typing.Callable,
        instance: typing.Any,
        args: typing.Tuple[typing.Any],
        kwargs: typing.Dict[str, typing.Any],
    ) -> typing.Dict[str, str]:
        return self.labels or self.get_labels_func(wrapped, instance, args, kwargs) or {}

    def gauge_inc(self, labels: typing.Dict[str, str]):
        if not self.gauge:
            return
        if labels:
            self.gauge.labels(**labels).inc(1)
        else:
            self.gauge.inc(1)

    def counter_inc(self, labels: typing.Dict[str, str]):
        if not self.counter:
            return
        if labels:
            self.counter.labels(**labels).inc(1)
        else:
            self.counter.inc(1)

    def gauge_dec(self, labels: typing.Dict[str, str]):
        if not self.gauge:
            return

        if labels:
            self.gauge.labels(**labels).dec(1)
        else:
            self.gauge.dec(1)

    def histogram_observe(self, labels: typing.Dict[str, str], start: float):
        if not self.histogram:
            return
        if labels:
            self.histogram.labels(**labels).observe(time.perf_counter() - start)
        else:
            self.histogram.observe(time.perf_counter() - start)

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
        if inspect.iscoroutinefunction(wrapped):
            # 交给上层通过 await 方式执行
            return self.wrapped_async_executor(wrapped, instance, args, kwargs)
        else:
            return self.wrapped_executor(wrapped, instance, args, kwargs)
