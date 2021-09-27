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

DURATION = 60 * 15


def calculate_countdown(count: int, index: int) -> int:
    """
    把周期任务平均分布到 ${DURATION}秒 内执行，用于削峰
    :param count: 任务总数
    :param index: 当前任务索引
    :return: 执行倒计时（s）
    """
    # 任务总数小于等于1时立即执行
    if count <= 1:
        return 0
    countdown = (index % DURATION) * (DURATION / (count - 1))
    return int(countdown)
