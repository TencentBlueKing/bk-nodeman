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

# 动作轮询间隔
from __future__ import absolute_import, unicode_literals

from celery.schedules import crontab

ACTION_POLLING_INTERVAL = 1
# 动作轮询超时时间
ACTION_POLLING_TIMEOUT = 60 * 3 * ACTION_POLLING_INTERVAL

# 自动下发触发周期
SUBSCRIPTION_UPDATE_INTERVAL = crontab(hour="*", minute="*/15", day_of_week="*", day_of_month="*", month_of_year="*")

# 订阅任务清理周期
INSTANCE_CLEAR_INTERVAL = crontab(minute="*/5", hour="*", day_of_week="*", day_of_month="*", month_of_year="*")

# 任务超时时间。距离 create_time 多久后会被判定为超时，防止 pipeline 后台僵死的情况
TASK_TIMEOUT = 60 * 15

# 最大重试次数
MAX_RETRY_TIME = 3

# 自动下发 - 订阅配置单个切片所包含的最大订阅个数 (根据经验，一个订阅需要消耗1~2s）
SUBSCRIPTION_UPDATE_SLICE_SIZE = 20

# 单个任务主机数量
TASK_HOST_LIMIT = 500

# 订阅范围实例缓存时间
SUBSCRIPTION_SCOPE_CACHE_TIME = 60 * 60
