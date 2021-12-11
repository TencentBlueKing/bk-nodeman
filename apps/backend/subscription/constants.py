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

from apps.node_man import constants

# run_every 周期都用秒作为单位的 int 类型，不使用crontab格式，以便与削峰函数 calculate_countdown 所用的 duration 复用
# 自动下发触发周期
SUBSCRIPTION_UPDATE_INTERVAL = 2 * constants.TimeUnit.HOUR

# 检查僵尸订阅实例记录周期
CHECK_ZOMBIE_SUB_INST_RECORD_INTERVAL = 15 * constants.TimeUnit.MINUTE

# 任务超时时间。距离 create_time 多久后会被判定为超时，防止 pipeline 后台僵死的情况
TASK_TIMEOUT = 15 * constants.TimeUnit.MINUTE

# 最大重试次数
MAX_RETRY_TIME = 3

# 单个任务主机数量
TASK_HOST_LIMIT = 500

# 订阅范围实例缓存时间，比自动下发周期多1小时
SUBSCRIPTION_SCOPE_CACHE_TIME = SUBSCRIPTION_UPDATE_INTERVAL + constants.TimeUnit.HOUR
