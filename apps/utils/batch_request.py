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
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from multiprocessing.pool import ThreadPool

from django.conf import settings

from apps.exceptions import AppBaseException
from apps.node_man import constants
from apps.utils.local import get_request


def format_params(params, get_count, func):
    # 拆分params适配bk_module_id大于500情况
    request_params = []

    bk_module_ids = params.pop("bk_module_ids", [])

    # 请求第一次获取总数
    if not bk_module_ids:
        request_params.append({"count": get_count(func(page={"start": 0, "limit": 1}, **params)), "params": params})

    for s_index in range(0, len(bk_module_ids), constants.QUERY_CMDB_MODULE_LIMIT):
        single_params = deepcopy(params)

        single_params.update({"bk_module_ids": bk_module_ids[s_index : s_index + constants.QUERY_CMDB_MODULE_LIMIT]})
        request_params.append(
            {"count": get_count(func(page={"start": 0, "limit": 1}, **single_params)), "params": single_params}
        )

    return request_params


def batch_request(
    func,
    params,
    get_data=lambda x: x["info"],
    get_count=lambda x: x["count"],
    limit=constants.QUERY_CMDB_LIMIT,
    sort=None,
    split_params=False,
):
    """
    异步并发请求接口
    :param func: 请求方法
    :param params: 请求参数
    :param get_data: 获取数据函数
    :param get_count: 获取总数函数
    :param limit: 一次请求数量
    :param sort: 排序
    :param split_params: 是否拆分参数
    :return: 请求结果
    """

    # 如果该接口没有返回count参数，只能同步请求
    if not get_count:
        return sync_batch_request(func, params, get_data, limit)

    if not split_params:
        final_request_params = [{"count": get_count(func(page={"start": 0, "limit": 1}, **params)), "params": params}]
    else:
        final_request_params = format_params(params, get_count, func)

    data = []

    # 根据请求总数并发请求
    pool = ThreadPool(20)
    futures = []

    for req in final_request_params:
        start = 0
        while start < req["count"]:
            request_params = {"page": {"limit": limit, "start": start}}
            if sort:
                request_params["page"]["sort"] = sort
            request_params.update(req["params"])
            futures.append(pool.apply_async(func, kwds=request_params))

            start += limit

    pool.close()
    pool.join()

    # 取值
    for future in futures:
        data.extend(get_data(future.get()))

    return data


def sync_batch_request(func, params, get_data=lambda x: x["info"], limit=500):
    """
    同步请求接口
    :param func: 请求方法
    :param params: 请求参数
    :param get_data: 获取数据函数
    :param limit: 一次请求数量
    :return: 请求结果
    """
    # 如果该接口没有返回count参数，只能同步请求
    data = []
    start = 0

    # 根据请求总数并发请求
    while True:
        request_params = {"page": {"limit": limit, "start": start}}
        request_params.update(params)
        result = get_data(func(request_params))
        data.extend(result)
        if len(result) < limit:
            break
        else:
            start += limit

    return data


def request_multi_thread(func, params_list, get_data=lambda x: []):
    """
    并发请求接口，每次按不同参数请求最后叠加请求结果
    :param func: 请求方法
    :param params_list: 参数列表
    :param get_data: 获取数据函数，通常CMDB的批量接口应该设置为 get_data=lambda x: x["info"]，其它场景视情况而定
    :return: 请求结果累计
    """
    # 参数预处理，添加request_id
    try:
        _request = get_request()
    except AppBaseException:
        # celery下 无request对象
        pass
    else:
        for params in params_list:
            if "params" in params:
                params["params"]["_request"] = _request

    result = []
    with ThreadPoolExecutor(max_workers=settings.CONCURRENT_NUMBER) as ex:
        tasks = [ex.submit(func, **params) for params in params_list]
    for future in as_completed(tasks):
        result.extend(get_data(future.result()))
    return result
