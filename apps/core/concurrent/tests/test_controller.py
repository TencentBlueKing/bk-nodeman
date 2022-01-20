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
import math
import random
import time
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.utils import timezone

from apps.utils import concurrent
from apps.utils.unittest import testcase

from .. import controller, lock


def list_double_numbers(numbers: List[int], call_info: Optional[Dict[str, Any]] = None) -> List[int]:
    """
    获取给定整数列表
    :param numbers: 整数列表
    :param call_info: 记录调用信息
    :return:
    """
    sleep_time = 0
    # 维护 call_info 的记录原子性
    with lock.RedisLock(lock_name="nodeman:test:list_double_numbers"):
        if call_info is not None:
            call_info["count"] += 1
            if "timedelta_list" not in call_info:
                call_info["timedelta_list"] = []
            call_info["timedelta_list"].append((timezone.now() - call_info["begin_at"]).total_seconds())
            sleep_time = call_info.get("sleep_time", 0)
    # 模拟真实场景下的执行耗时
    time.sleep(sleep_time)
    return [2 * number for number in numbers]


class ConcurrentControllerTestCase(testcase.CustomBaseTestCase):
    def base_assert(self, max_length: int, call_info: Dict[str, Any], controller_inst: controller.ConcurrentController):
        call_info.update(begin_at=timezone.now(), count=0)
        list_double_numbers_with_controller = controller_inst(list_double_numbers)

        length = random.randint(100, max_length)
        random_numbers = random.sample(range(max_length), length)

        # 获取装饰器执行结果
        double_numbers = list_double_numbers_with_controller(numbers=random_numbers, call_info=call_info)
        double_numbers_execute_all = list_double_numbers(random_numbers)
        # 验证经过排序后返回结果一致
        self.assertListEqual(double_numbers, double_numbers_execute_all, is_sort=True)

        config_obj = controller_inst.get_config_obj()
        if config_obj.execute_all:
            expect_batch_num = 1
        else:
            expect_batch_num = math.ceil(len(random_numbers) / config_obj.limit)
        # 验证分片执行
        self.assertEqual(expect_batch_num, call_info["count"])

        return {"double_numbers": double_numbers, "double_numbers_execute_all": double_numbers_execute_all}

    def test_default_config(self):
        """测试默认配置"""
        controller_inst = controller.ConcurrentController(
            data_list_name="numbers", batch_call_func=concurrent.batch_call
        )
        self.base_assert(max_length=90000, call_info={}, controller_inst=controller_inst)

    def test_multi_threads_with_interval(self):
        """测试多线程间隔调用"""
        interval = 0.1
        controller_inst = controller.ConcurrentController(
            data_list_name="numbers", batch_call_func=concurrent.batch_call, batch_call_kwargs={"interval": interval}
        )
        call_info = {"sleep_time": interval + 0.1}
        self.base_assert(
            max_length=settings.CONCURRENT_NUMBER * 10, call_info=call_info, controller_inst=controller_inst
        )

        # 验证批次间调用间隔符合预期，仅需保证2个间隔具备调用时差
        # 相邻位置可能会有调用误差，导致 sorted_timedelta_list[idx] - sorted_timedelta_list[idx - 2] < interval
        sorted_timedelta_list = sorted(call_info["timedelta_list"])
        for idx in range(2, len(sorted_timedelta_list), 2):
            self.assertTrue(sorted_timedelta_list[idx] - sorted_timedelta_list[idx - 2] >= interval)

    def test_get_config(self):
        """验证通过传入配置获取方法获得配置"""

        def get_config(limit: int, is_concurrent_between_batches: bool):
            return {"limit": limit, "is_concurrent_between_batches": is_concurrent_between_batches}

        controller_inst = controller.ConcurrentController(
            data_list_name="numbers",
            batch_call_func=concurrent.batch_call,
            get_config_dict_func=get_config,
            get_config_dict_args=(10,),
            get_config_dict_kwargs={"is_concurrent_between_batches": False},
        )
        call_result = self.base_assert(
            max_length=settings.CONCURRENT_NUMBER * 10, call_info={}, controller_inst=controller_inst
        )
        # 串行有序
        self.assertEqual(call_result["double_numbers"], call_result["double_numbers_execute_all"])

    def test_execute_all(self):
        """验证全量执行"""
        controller_inst = controller.ConcurrentController(
            data_list_name="numbers",
            batch_call_func=concurrent.batch_call,
            get_config_dict_func=lambda: {"execute_all": True},
        )
        self.base_assert(max_length=settings.CONCURRENT_NUMBER * 5, call_info={}, controller_inst=controller_inst)

    def test_empty_list(self):
        """验证空列表"""
        double_numbers = controller.ConcurrentController(
            data_list_name="numbers", batch_call_func=concurrent.batch_call
        )(list_double_numbers)(numbers=[])
        self.assertEqual(double_numbers, [])
