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
from typing import Any, Callable, Coroutine, Dict, Optional, Tuple, Union

import wrapt
from asgiref.sync import sync_to_async


class ExceptionHandler:
    """
    异常处理器，兼容协程
    自定义 exc_handler，实现`生成解决方案`，`异常捕获兜底` 等功能
    """

    exc_handler: Callable[[Callable, Any, Tuple[Any], Dict[str, Any], Exception], Any] = None

    @staticmethod
    def default_exc_handler(
        wrapped: Callable, instance: Any, args: Tuple[Any], kwargs: Dict[str, Any], exc: Exception
    ) -> Any:
        """
        默认异常处理器
        :param wrapped: 被装饰的函数或类方法
        :param instance: 参考 __init__
        :param args: 位置参数
        :param kwargs: 关键字参数
        :param exc: 捕获到异常
        :return:
        """
        # 抛出原异常
        raise

    async def wrapped_async_executor(
        self, wrapped: Callable, instance: Any, args: Tuple[Any], kwargs: Dict[str, Any]
    ) -> Any:
        """
        实例任务执行器，协程模式
        :param wrapped: 被装饰的函数或类方法
        :param instance: 参考 __init__
        :param args: 位置参数
        :param kwargs: 关键字参数
        :return:
        """
        try:
            return await wrapped(*args, **kwargs)
        except Exception as exc:
            if inspect.iscoroutinefunction(self.exc_handler):
                return await self.exc_handler(wrapped, instance, args, kwargs, exc)
            else:
                return await sync_to_async(self.exc_handler)(wrapped, instance, args, kwargs, exc)

    def wrapped_executor(self, wrapped: Callable, instance: Any, args: Tuple[Any], kwargs: Dict[str, Any]):
        """
        实例任务执行器
        :param wrapped: 被装饰的函数或类方法
        :param instance: 基础Pipeline服务
        :param args: 位置参数
        :param kwargs: 关键字参数
        :return:
        """
        try:
            return wrapped(*args, **kwargs)
        except Exception as exc:
            return self.exc_handler(wrapped, instance, args, kwargs, exc)

    def __init__(
        self, exc_handler: Optional[Callable[[Callable, Any, Tuple[Any], Dict[str, Any], Exception], Any]] = None
    ):
        """
        :param exc_handler: 异常处理器
        """
        self.exc_handler = exc_handler or self.default_exc_handler

    @wrapt.decorator
    def __call__(
        self, wrapped: Callable, instance: Any, args: Tuple[Any], kwargs: Dict[str, Any]
    ) -> Union[Coroutine, Any]:
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
