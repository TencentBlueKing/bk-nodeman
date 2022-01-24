# coding: utf-8
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
import random

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from common.log import logger

from .. import tasks
from ..constants import CheckerStatus
from .checker import CheckerRegister
from .utils import get_process_info

register = CheckerRegister.celery


@register.execution.status()
def execution_status(manager, result, queues, timeout=10):
    """Celery worker 任务执行测试"""
    value = random.random()
    proxy_items = []
    queue_result = []
    # 批量发送celery任务
    for queue in queues:
        proxy = tasks.healthz.apply_async(queue=queue, args=(value,), priority=9, expires=timeout)
        proxy_items.append({"queue": queue, "proxy": proxy})
    # 批量检查celery任务结果，检查失败则增加失败任务统计
    for proxy_item in proxy_items:
        proxy = proxy_item["proxy"]
        status_check_info = functools.partial(generate_check_info, name=str({"queue": proxy_item["queue"]}))
        try:
            res = proxy.get(timeout=timeout, no_ack=True)
            if res:
                queue_result.append(status_check_info(status=CheckerStatus.CHECKER_OK, value="ok"))
            else:
                queue_result.append(
                    status_check_info(status=CheckerStatus.CHECKER_FAILED, message="get celery task result failed")
                )
        except Exception as e:
            logger.exception(e)
            queue_result.append(status_check_info(status=CheckerStatus.CHECKER_FAILED, message=str(e)))
    result.update(value=queue_result)


@register.worker_process.status()
def process_info(manager, result, process_name):
    """celery worker 进程状态"""
    processes_result = []
    # 遍历所选组内所有任务
    for name in process_name:
        status_check_info = functools.partial(generate_check_info, name=str({"process_name": name}))
        found = False
        ok = False
        for info in get_process_info():
            # 如果任务名含有process_name，证明是该类型任务
            if info.get("name").startswith(name):
                found = True
                if info and (info.get("statename") == "RUNNING" or info.get("description") == "Not started"):
                    ok = True
                    break
        if found:
            if ok:
                processes_result.append(status_check_info(status=CheckerStatus.CHECKER_OK, value="ok"))
            else:
                processes_result.append(
                    status_check_info(status=CheckerStatus.CHECKER_FAILED, message="celery process not running")
                )
        else:
            processes_result.append(
                status_check_info(status=CheckerStatus.CHECKER_FAILED, message="celery process not found")
            )

    return result.update(value=processes_result)


@register.beat_process.status()
def beat_process_status(manager, result, process_name):
    """Supervisor 进程详情"""
    ok = False
    processes = []
    # 遍历所选组内所有任务
    for info in get_process_info():
        # 如果任务名含有process_name，证明是该类型任务
        if info.get("name").startswith(process_name):
            processes.append(
                {
                    "name": info.get("name"),
                    "pid": info.get("pid"),
                    "start": info.get("start"),
                    "exitstatus": info.get("exitstatus"),
                    "spawnerr": info.get("spawnerr"),
                    "statename": info.get("statename"),
                    "description": info.get("description"),
                }
            )

            uptime = info.get("now", 0) - info.get("start", 0)
            is_running = info.get("statename") == "RUNNING" and uptime >= settings.SUPERVISOR_PROCESS_UPTIME
            not_started = info.get("description") == "Not started"

            if not is_running and info.get("statename") == "RUNNING":
                processes[-1]["description"] += _(", 进程启动时间小于10秒，请关注")

            if info and (is_running or not_started):
                ok = True
    if ok:
        return result.ok(processes)
    return result.fail(processes)


def generate_check_info(name, status=CheckerStatus.CHECKER_OK, message="", value=""):
    return {
        "name": name,
        "status": status,
        "message": message,
        "value": value,
    }
