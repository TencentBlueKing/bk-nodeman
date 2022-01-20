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
import functools
import time
from typing import Any, Dict

from django.utils import timezone

from apps.utils.time_handler import strftime_local
from common.log import logger


def get_log_and_print(command_name: str):
    def log_and_print(log: str, execute_id: int = None):
        # 实时打屏显示进度
        if execute_id:
            log_prefix = f"[{strftime_local(timezone.now())} {command_name}, execute_id -> {execute_id}]"
        else:
            log_prefix = f"[{strftime_local(timezone.now())} {command_name}]"

        log = f"{log_prefix} {log}"
        print(log, flush=True)
        logger.info(log)

    return log_and_print


def called_hook_example(result: Any, cost_time: float, call_params: Dict[str, Any]):
    pass


def program_timer(called_hook=called_hook_example):
    def program_timer_inner(func):
        @functools.wraps(func)
        def inner(**kwargs):
            start_time = time.time()
            result = func(**kwargs)
            cost_time = time.time() - start_time
            called_hook(result=result, cost_time=cost_time, call_params=kwargs)
            return {"result": result, "cost_time": cost_time}

        return inner

    return program_timer_inner
