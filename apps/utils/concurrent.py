# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import sys
import time
from concurrent.futures import as_completed
from concurrent.futures.thread import ThreadPoolExecutor
from multiprocessing import cpu_count, get_context
from typing import Callable, Dict, List

from django.conf import settings

from apps.exceptions import AppBaseException
from apps.utils import local


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

    result = []

    # 不存在参数列表，直接返回
    if not params_list:
        return result

    with ThreadPoolExecutor(max_workers=settings.CONCURRENT_NUMBER) as ex:
        tasks = []
        for idx, params in enumerate(params_list):
            if idx != 0:
                time.sleep(interval)
            tasks.append(ex.submit(inject_request(func), **params))

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
    result = []
    for idx, params in enumerate(params_list):
        if idx != 0:
            time.sleep(interval)
        if extend_result:
            result.extend(get_data(func(**params)))
        else:
            result.append(get_data(func(**params)))
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
