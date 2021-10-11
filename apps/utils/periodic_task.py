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
from typing import Optional

DURATION = 60 * 15


def calculate_countdown__mod(count: int, index: int, duration: int) -> int:
    """
    把周期任务通过取模的方式平均分布到 duration 秒 内执行，用于削峰
    :param count: 任务总数
    :param index: 当前任务索引
    :param duration: 执行周期
    :return: 执行倒计时（s）
    """
    return max(index, 1) % max(duration, 1)


def calculate_countdown__random(count: int, index: int, duration: int) -> int:
    """
    把周期任务通过随机数的方式平均分布到 duration 秒 内执行，用于削峰
    :param count: 任务总数
    :param index: 当前任务索引
    :param duration: 执行周期
    :return: 执行倒计时（s）
    """
    return random.randint(0, max(duration - 1, 1))


def calculate_countdown__mix(count: int, index: int, duration: int) -> int:
    """
    结合多种分布策略将周期任务分布到 duration 秒 内执行，用于削峰
    :param count: 任务总数
    :param index: 当前任务索引
    :param duration: 执行周期
    :return: 执行倒计时（s）
    """
    calculate_countdown_funcs = [calculate_countdown__mod, calculate_countdown__random]
    return calculate_countdown_funcs[random.randint(0, 1)](count=count, index=index, duration=duration)


def calculate_countdown(count: int, index: int, duration: Optional[int] = None) -> int:
    """
    把周期任务随机平均分布到 ${DURATION}秒 内执行，用于削峰
    :param count: 任务总数
    :param index: 当前任务索引
    :param duration: 平摊周期(s)，一般设定为周期任务的执行周期
    :return: 执行倒计时（s）
    """
    # 任务总数小于等于1时立即执行
    if count <= 1:
        return 0
    duration = (duration, DURATION)[duration is None]
    return calculate_countdown__mix(count=count, index=index, duration=duration)
