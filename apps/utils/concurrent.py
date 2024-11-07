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
import asyncio
import inspect
import sys
import time
from concurrent.futures import as_completed
from concurrent.futures.thread import ThreadPoolExecutor
from multiprocessing import cpu_count, get_context
from typing import Callable, Coroutine, Dict, List, Union

from asgiref.sync import async_to_sync
from django.conf import settings
from django.utils.translation import get_language

from apps.exceptions import AppBaseException
from apps.node_man.constants import DCReturnType
from apps.utils import local
from apps.utils.redis import DynamicContainer, RedisList

from . import translation


def inject_request(func: Callable):

    try:
        request = local.get_request()
    except AppBaseException:
        request = None

    def inner(*args, **kwargs):
        if request:
            local.activate_request(request)
        return func(*args, **kwargs)

    return inner


def batch_call(
    func: Callable,
    params_list: List[Dict],
    get_data=lambda x: x,
    extend_result: bool = False,
    interval: float = 0,
    data_backend: str = None,
    **kwargs
) -> List:
    """
    # TODO 后续 batch_call 支持 *args 类参数
    并发请求接口，每次按不同参数请求最后叠加请求结果
    :param func: 请求方法
    :param params_list: 参数列表
    :param get_data: 获取数据函数
    :param extend_result: 是否展开结果
    :param interval: 任务提交间隔
    :return: 请求结果累计
    """

    result: Union[RedisList, list] = DynamicContainer(
        return_type=DCReturnType.LIST.value, data_backend=data_backend
    ).container

    # 不存在参数列表，直接返回
    if not params_list:
        return result

    # 单个子任务，直接串行跑，减少上下文切换
    if len(params_list) == 1:
        return batch_call_serial(func, params_list, get_data, extend_result, interval, **kwargs)

    if inspect.iscoroutinefunction(func):
        func = async_to_sync(func)

    with ThreadPoolExecutor(max_workers=settings.CONCURRENT_NUMBER) as ex:
        tasks = []
        for idx, params in enumerate(params_list):
            if idx != 0 and interval:
                time.sleep(interval)
            tasks.append(
                ex.submit(translation.RespectsLanguage(language=get_language())(inject_request(func)), **params)
            )

    for future in as_completed(tasks):
        if extend_result:
            result.extend(get_data(future.result()))
        else:
            result.append(get_data(future.result()))
    return result


def batch_call_serial(
    func: Callable,
    params_list: List[Dict],
    get_data: Callable = lambda x: x,
    extend_result: bool = False,
    interval: float = 0,
    **kwargs
):

    if inspect.iscoroutinefunction(func):
        func = async_to_sync(func)

    result = []
    for idx, params in enumerate(params_list):
        if idx != 0 and interval:
            time.sleep(interval)
        if extend_result:
            result.extend(get_data(func(**params)))
        else:
            result.append(get_data(func(**params)))
    return result


def batch_call_coroutine(
    func: Callable[..., Coroutine],
    params_list: List[Dict],
    get_data: Callable = lambda x: x,
    extend_result: bool = False,
    interval: float = 0,
    **kwargs
):
    """
    协程并发
    :param func: 返回协程对象的方法
    :param params_list: 参数列表
    :param get_data: 获取数据函数
    :param extend_result: 是否展开结果
    :param interval: 暂不支持
    :param kwargs:
    :return:
    """

    async def _batch_call_coroutine(_coros: List[Coroutine]):
        return await asyncio.gather(*_coros, return_exceptions=True)

    coros: List[Coroutine] = [func(**params) for params in params_list]
    loop = asyncio.new_event_loop()
    coro_results = loop.run_until_complete(_batch_call_coroutine(coros))
    loop.close()

    result = []
    for coro_result in coro_results:
        if extend_result:
            result.extend(get_data(coro_result))
        else:
            result.append(get_data(coro_result))
    return result


def batch_call_multi_proc(
    func, params_list: List[Dict], get_data=lambda x: x, extend_result: bool = False, **kwargs
) -> List:
    """
    多进程执行函数
    不适用于DB请求类处理，容易引发Lose Connect，如有需求，使用 batch_call
    :param func: 请求方法
    :param params_list: 参数列表
    :param get_data: 获取数据函数
    :param extend_result: 是否展开结果
    :return: 请求结果累计
    """
    if sys.platform in ["win32", "cygwim", "msys"]:
        return batch_call(func, params_list, get_data, extend_result)
    else:
        ctx = get_context("fork")

    result = []

    pool = ctx.Pool(processes=cpu_count())
    futures = [pool.apply_async(func=inject_request(func), kwds=params) for params in params_list]

    pool.close()
    pool.join()

    # 取值
    for future in futures:
        if extend_result:
            result.extend(get_data(future.get()))
        else:
            result.append(get_data(future.get()))

    return result
