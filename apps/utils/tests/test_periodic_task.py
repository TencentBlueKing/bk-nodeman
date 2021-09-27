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

import random
from typing import Set

from .. import periodic_task
from ..unittest import testcase


class TestPeriodicTask(testcase.CustomBaseTestCase):
    def test_calculate_countdown(self):
        def _get_countdown_set(_count: int) -> Set[int]:
            _countdown_set = set()
            for idx in range(_count):
                _countdown_set.add(periodic_task.calculate_countdown(count=_count, index=idx))
            return _countdown_set

        def _test_one_count():
            self.assertEqual(periodic_task.calculate_countdown(count=1, index=0), 0)

        def _test_count_less_than_duration():
            count = random.randint(1, periodic_task.DURATION)
            countdown_set = _get_countdown_set(_count=count)

            # 任务数量小于平摊周期，此时任务被分布到不同的时刻执行
            self.assertTrue(len(countdown_set) == count)

        _test_one_count()
        _test_count_less_than_duration()
