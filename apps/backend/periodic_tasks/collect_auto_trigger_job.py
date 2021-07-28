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

import logging
from collections import defaultdict

from celery.schedules import crontab
from celery.task import periodic_task
from django.db import transaction

from apps.node_man import constants, models

logger = logging.getLogger("celery")


@periodic_task(
    run_every=crontab(hour="*", minute="*/5", day_of_week="*", day_of_month="*", month_of_year="*"),
    queue="backend",  # 这个是用来在代码调用中指定队列的，例如： update_subscription_instances.delay()
    options={"queue": "backend"},  # 这个是用来celery beat调度指定队列的
)
def collect_auto_trigger_job():
    last_sub_task_id = models.GlobalSettings.get_config("LAST_SUB_TASK_ID", None)
    if last_sub_task_id is None:
        last_sub_task_id = 0
        models.GlobalSettings.set_config("LAST_SUB_TASK_ID", last_sub_task_id)

    all_auto_task_infos = models.SubscriptionTask.objects.filter(id__gt=last_sub_task_id, is_auto_trigger=True).values(
        "subscription_id", "id", "is_ready", "err_msg"
    )

    # 找出SaaS侧存在自动触发task的主动触发job
    jobs = models.Job.objects.filter(
        is_auto_trigger=False,
        subscription_id__in={auto_task_info["subscription_id"] for auto_task_info in all_auto_task_infos},
    ).order_by("-id")

    subscription_ids = {job.subscription_id for job in jobs}
    # 过滤非SaaS侧策略自动触发的订阅任务
    auto_task_infos = [
        auto_task_info
        for auto_task_info in all_auto_task_infos
        if auto_task_info["subscription_id"] in subscription_ids
    ]

    logger.info(
        f"collect_auto_trigger_job: auto_task_ids -> {[auto_task_info['id'] for auto_task_info in auto_task_infos]}"
    )

    # 考虑一个订阅中有多个自动触发task的情况
    task_ids_gby_sub_id = defaultdict(list)
    task_ids_gby_reason = {"NOT_READY": [], "READY": [], "ERROR": []}
    for task_info in auto_task_infos:
        # is_ready=False并且无错误信息时，该订阅任务仍处于创建状态
        if not task_info["is_ready"]:
            task_ids_gby_reason["ERROR" if task_info["err_msg"] else "NOT_READY"].append(task_info["id"])
            continue
        # 仅同步成功创建的的订阅任务
        task_ids_gby_reason["READY"].append(task_info["id"])
        task_ids_gby_sub_id[task_info["subscription_id"]].append(task_info["id"])

    logger.info(
        f"collect_auto_trigger_job: last_sub_task_id -> {last_sub_task_id}, "
        f"task_ids_gby_reason -> {task_ids_gby_reason}, begin"
    )

    sub_id_record = set()
    auto_job_to_be_created = []
    for job in jobs:

        # 任务未就绪或创建失败，跳过
        if job.subscription_id not in task_ids_gby_sub_id:
            continue

        # 可能存在job_id - subscription_id 多对一的关系，取相同sub_id的最新job记录
        if job.subscription_id in sub_id_record:
            continue

        sub_id_record.add(job.subscription_id)
        auto_job_to_be_created.append(
            models.Job(
                # 巡检的任务类型为安装
                job_type=constants.JobType.MAIN_INSTALL_PLUGIN,
                bk_biz_scope=job.bk_biz_scope,
                subscription_id=job.subscription_id,
                # 依赖calculate_statistics定时更新状态及实例状态统计
                status=constants.JobStatusType.RUNNING,
                statistics={f"{k}_count": 0 for k in ["success", "failed", "pending", "running", "total"]},
                error_hosts=[],
                created_by="admin",
                # TODO 将历史多个自动触发task先行整合到一个job，后续根据实际情况考虑是否拆分
                task_id_list=task_ids_gby_sub_id[job.subscription_id],
                is_auto_trigger=True,
            )
        )

    # 下次同步的起点确定
    # 该同步周期内无新的task产生，此时起点不变
    if not auto_task_infos:
        last_sub_task_id = last_sub_task_id
    else:
        # 异步创建失败（ERROR）的任务无需同步，NOT_READY 的任务需要在下一周期同步
        if task_ids_gby_reason["NOT_READY"]:
            last_sub_task_id = min(task_ids_gby_reason["NOT_READY"]) - 1
        else:
            # 指针后移至已完成同步id的最大值
            last_sub_task_id = max(task_ids_gby_reason["READY"] or task_ids_gby_reason["ERROR"])

    with transaction.atomic():
        models.Job.objects.bulk_create(auto_job_to_be_created)
        models.GlobalSettings.update_config("LAST_SUB_TASK_ID", last_sub_task_id)
    logger.info(f"collect_auto_trigger_job: last_sub_task_id -> {last_sub_task_id}")
