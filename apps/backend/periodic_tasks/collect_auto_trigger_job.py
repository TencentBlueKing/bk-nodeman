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

from celery.task import periodic_task
from django.db import transaction
from django.db.models import Q

from apps.node_man import constants, models

logger = logging.getLogger("celery")


@periodic_task(
    run_every=constants.COLLECT_AUTO_TRIGGER_JOB_INTERVAL,
    queue="backend",  # 这个是用来在代码调用中指定队列的，例如： update_subscription_instances.delay()
    options={"queue": "backend"},  # 这个是用来celery beat调度指定队列的
)
def collect_auto_trigger_job():
    last_sub_task_id = models.GlobalSettings.get_config(models.GlobalSettings.KeyEnum.LAST_SUB_TASK_ID.value, None)
    not_ready_task_info_map = models.GlobalSettings.get_config(
        models.GlobalSettings.KeyEnum.NOT_READY_TASK_INFO_MAP.value, None
    )
    if last_sub_task_id is None:
        last_sub_task_id = 0
        models.GlobalSettings.set_config(models.GlobalSettings.KeyEnum.LAST_SUB_TASK_ID.value, last_sub_task_id)
    if not_ready_task_info_map is None:
        not_ready_task_info_map = {}
        models.GlobalSettings.set_config(models.GlobalSettings.KeyEnum.NOT_READY_TASK_INFO_MAP.value, {})

    not_ready_task_ids = list(int(not_ready_task_id_str) for not_ready_task_id_str in not_ready_task_info_map.keys())
    all_auto_task_infos = models.SubscriptionTask.objects.filter(
        Q(id__gt=last_sub_task_id) | Q(id__in=not_ready_task_ids), is_auto_trigger=True
    ).values("subscription_id", "id", "is_ready", "err_msg")

    # 找出归属SaaS侧的订阅ID列表
    subscription_ids = set(
        models.Job.objects.filter(
            is_auto_trigger=False,
            subscription_id__in={auto_task_info["subscription_id"] for auto_task_info in all_auto_task_infos},
        ).values_list("subscription_id", flat=True)
    )

    subscriptions = models.Subscription.objects.filter(id__in=subscription_ids).values("id", "bk_biz_scope")

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

    auto_jobs_to_be_created = []
    for subscription in subscriptions:

        # 任务未就绪或创建失败，跳过
        if subscription["id"] not in task_ids_gby_sub_id:
            continue

        auto_jobs_to_be_created.append(
            models.Job(
                # 巡检的任务类型为安装
                job_type=constants.JobType.MAIN_INSTALL_PLUGIN,
                bk_biz_scope=subscription["bk_biz_scope"],
                subscription_id=subscription["id"],
                # 依赖calculate_statistics定时更新状态及实例状态统计
                status=constants.JobStatusType.RUNNING,
                statistics={f"{k}_count": 0 for k in ["success", "failed", "pending", "running", "total"]},
                error_hosts=[],
                created_by="admin",
                # TODO 将历史多个自动触发task先行整合到一个job，后续根据实际情况考虑是否拆分
                task_id_list=task_ids_gby_sub_id[subscription["id"]],
                is_auto_trigger=True,
            )
        )

    # 上一次未就绪在本次同步中已有结果，从未就绪记录中移除
    for task_id in task_ids_gby_reason["READY"] + task_ids_gby_reason["ERROR"]:
        # global setting 会将key转为str类型，在统计时也将整数转为str，保证统计准确
        task_id = str(task_id)
        not_ready_task_info_map.pop(task_id, None)

    # 异步创建失败（ERROR）的任务无需同步，NOT_READY 的任务先行记录，若上一次的未就绪任务仍未就绪，重试次数+1
    for task_id in task_ids_gby_reason["NOT_READY"]:
        task_id = str(task_id)
        not_ready_task_info_map[task_id] = not_ready_task_info_map.get(task_id, 0) + 1

    # 指针后移至已完成同步id的最大值，若本轮无同步数据，指针位置不变
    all_task_ids = {auto_task_info["id"] for auto_task_info in auto_task_infos}
    # 仅统计新增task_id，防止指针回退
    new_add_task_ids = all_task_ids - set(not_ready_task_ids)
    last_sub_task_id = max(new_add_task_ids or [last_sub_task_id])

    with transaction.atomic():
        models.Job.objects.bulk_create(auto_jobs_to_be_created)
        models.GlobalSettings.update_config(models.GlobalSettings.KeyEnum.LAST_SUB_TASK_ID.value, last_sub_task_id)
        models.GlobalSettings.update_config(
            models.GlobalSettings.KeyEnum.NOT_READY_TASK_INFO_MAP.value, not_ready_task_info_map
        )
    logger.info(
        f"collect_auto_trigger_job: {models.GlobalSettings.KeyEnum.LAST_SUB_TASK_ID.value} -> {last_sub_task_id}, "
        f"{models.GlobalSettings.KeyEnum.NOT_READY_TASK_INFO_MAP.value} -> {not_ready_task_info_map}"
    )

    return {
        models.GlobalSettings.KeyEnum.LAST_SUB_TASK_ID.value: last_sub_task_id,
        models.GlobalSettings.KeyEnum.NOT_READY_TASK_INFO_MAP.value: not_ready_task_info_map,
        "TASK_IDS_GBY_REASON": task_ids_gby_reason,
    }
