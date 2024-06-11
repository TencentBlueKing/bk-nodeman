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

import logging
import typing
from dataclasses import asdict, dataclass
from datetime import timedelta

from celery.schedules import crontab
from celery.task import periodic_task
from dacite import from_dict
from django.db import connection
from django.db.models import Value
from django.utils import timezone

from apps.node_man import models
from apps.prometheus import metrics
from apps.prometheus.helper import SetupObserve

logger = logging.getLogger("celery")


TASK: str = "clean_sub_data"


def generate_options(ids: typing.List[typing.Union[str, int]]) -> str:
    if len(ids) == 0:
        return "()"
    dot: str = ",".join(f"'{str(_id)}'" for _id in ids)
    return f"({dot})"


def generate_delete_sql(
    table_name: str, field: str, ids: typing.List[typing.Union[str, int]], other_cond: str = ""
) -> str:
    sql: str = f"DELETE FROM {table_name} WHERE {field} IN {generate_options(ids)}"
    if other_cond:
        sql = sql + " AND " + other_cond
    sql = f"{sql};"
    logger.info("[clean_sub_data][generate_delete_sql] sql -> %s", sql)
    return sql


@SetupObserve(
    histogram=metrics.app_clean_data_duration_seconds,
    get_labels_func=lambda wrapped, instance, args, kwargs: {
        "task": TASK,
        "source": kwargs["source"],
        "method": f"delete-{kwargs['table_name']}",
    },
)
def do_delete(table_name: str, field: str, ids: typing.List[typing.Union[str, int]], source: str, other_cond: str = ""):
    if not ids:
        metrics.app_clean_data_records_total.labels(task=TASK, table=table_name, source=source).inc(0)
        return

    ids = list(set(ids))

    with connection.cursor() as cursor:
        cursor.execute(generate_delete_sql(table_name, field, ids, other_cond=other_cond))
        try:
            rowcount: int = int(cursor.rowcount)
        except TypeError:
            rowcount: int = 0
        logger.info("[clean_sub_data][do_delete] table -> %s, delete -> %s", table_name, rowcount)
        metrics.app_clean_data_records_total.labels(task=TASK, table=table_name, source=source).inc(amount=rowcount)


@SetupObserve(
    histogram=metrics.app_clean_data_duration_seconds,
    get_labels_func=lambda wrapped, instance, args, kwargs: {
        "task": TASK,
        "method": "handle_job_delete",
        "source": "default",
    },
)
def handle_job_delete(config: "CleanConfig", sub_ids: typing.Set[int]) -> typing.Set[int]:
    clean_deadline = timezone.now() - timedelta(days=config.job_alive_days)
    job_task_ids: typing.Set[int] = set()
    to_be_clean_job_ids: typing.List[int] = []
    to_be_clean_sub_ids: typing.List[int] = []
    job_objs: typing.List[models.Job] = models.Job.objects.filter(subscription_id__in=sub_ids).only(
        "id", "subscription_id", "task_id_list", "start_time"
    )
    for job in job_objs:
        for task_id in job.task_id_list:
            job_task_ids.add(task_id)
        if job.start_time <= clean_deadline:
            to_be_clean_job_ids.append(job.id)
            to_be_clean_sub_ids.append(job.subscription_id)

    # 找到 task 关联的所有 pipeline id
    to_be_clean_pipeline_ids: typing.List[int] = [
        pipeline_id
        for pipeline_id in models.SubscriptionTask.objects.filter(subscription_id__in=to_be_clean_sub_ids).values_list(
            "pipeline_id", flat=True
        )
        if pipeline_id
    ]

    logger.info(
        "[clean_sub_data][handle_job_delete] job -> %s, sub -> %s, pipeline -> %s",
        len(to_be_clean_job_ids),
        len(to_be_clean_sub_ids),
        len(to_be_clean_pipeline_ids),
    )

    do_delete(
        table_name=models.PipelineTree._meta.db_table,
        field="id",
        ids=to_be_clean_pipeline_ids,
        source="handle_job_delete",
    )
    do_delete(
        table_name=models.SubscriptionInstanceRecord._meta.db_table,
        field="subscription_id",
        ids=to_be_clean_sub_ids,
        source="handle_job_delete",
    )
    do_delete(
        table_name=models.SubscriptionStep._meta.db_table,
        field="subscription_id",
        ids=to_be_clean_sub_ids,
        source="handle_job_delete",
    )
    do_delete(
        table_name=models.Subscription._meta.db_table, field="id", ids=to_be_clean_sub_ids, source="handle_job_delete"
    )
    do_delete(table_name=models.Job._meta.db_table, field="id", ids=to_be_clean_job_ids, source="handle_job_delete")
    do_delete(
        table_name=models.SubscriptionTask._meta.db_table,
        field="subscription_id",
        ids=to_be_clean_sub_ids,
        source="handle_job_delete",
    )

    return job_task_ids


@SetupObserve(
    histogram=metrics.app_clean_data_duration_seconds,
    get_labels_func=lambda wrapped, instance, args, kwargs: {
        "task": TASK,
        "method": "handle_sub_delete",
        "source": "default",
    },
)
def handle_sub_delete(sub_task_ids: typing.Set[int], task_id__info_map: typing.Dict[int, typing.Dict[str, typing.Any]]):
    # 只有当这个 task 全部的 record 为 False，这个 task 才能删除
    contains_latest_sub_task_ids: typing.Set[int] = set(
        models.SubscriptionInstanceRecord.objects.filter(task_id__in=sub_task_ids, is_latest=Value(1)).values_list(
            "task_id", flat=True
        )
    )
    to_be_clean_sub_task_ids: typing.Set[int] = sub_task_ids - contains_latest_sub_task_ids
    pipeline_ids: typing.Set[str] = set()
    for task_id in to_be_clean_sub_task_ids:
        task: typing.Dict[str, typing.Any] = task_id__info_map[task_id]
        if task["pipeline_id"]:
            pipeline_ids.add(task["pipeline_id"])

    logger.info(
        "[clean_sub_data][handle_sub_delete] task -> %s, to_be_clean_tasks -> %s, pipeline -> %s",
        len(sub_task_ids),
        len(to_be_clean_sub_task_ids),
        len(pipeline_ids),
    )
    do_delete(
        table_name=models.SubscriptionInstanceRecord._meta.db_table,
        field="task_id",
        ids=list(sub_task_ids),
        other_cond="is_latest=0",
        source="handle_sub_delete",
    )
    do_delete(
        table_name=models.PipelineTree._meta.db_table, field="id", ids=list(pipeline_ids), source="handle_sub_delete"
    )
    do_delete(
        table_name=models.SubscriptionTask._meta.db_table,
        field="id",
        ids=list(to_be_clean_sub_task_ids),
        source="handle_sub_delete",
    )


@dataclass
class CleanConfig:
    enable: bool = False
    begin: int = 0
    limit: int = 200
    # 默认保留一年的 Job 日志
    job_alive_days: int = 365
    # 为避免对当下执行任务的影响，保留 n 天的 task
    sub_task_alive_days: int = 7


def get_config() -> CleanConfig:
    """获取 settings 配置数据"""
    config_dict: typing.Dict[str, typing.Any] = models.GlobalSettings.get_config(
        models.GlobalSettings.KeyEnum.CLEAN_SUB_DATA_MAP.value, default={}
    )
    config: CleanConfig = from_dict(CleanConfig, config_dict)
    logger.info("[clean_sub_data][get_config] config -> %s", asdict(config))
    return config


def set_config(config: CleanConfig):
    models.GlobalSettings.update_config(models.GlobalSettings.KeyEnum.CLEAN_SUB_DATA_MAP.value, asdict(config))


@SetupObserve(
    histogram=metrics.app_clean_data_duration_seconds,
    get_labels_func=lambda wrapped, instance, args, kwargs: {
        "task": TASK,
        "method": "clean_sub_data",
        "source": "default",
    },
)
def clean_sub_data(config: CleanConfig):
    sub_tasks: typing.List[typing.Dict[str, typing.Any]] = list(
        models.SubscriptionTask.objects.filter(
            id__gt=config.begin, create_time__lt=timezone.now() - timedelta(days=config.sub_task_alive_days)
        )
        .order_by("id")
        .values("id", "pipeline_id", "subscription_id")[: config.limit]
    )
    # 数据删完了，重置为 0
    if not sub_tasks:
        config.begin = 0
        logger.info("[clean_sub_data] empty tasks, reset begin to 0 and skipped")
        return

    # 找出最大的 id
    max_id: int = models.SubscriptionTask.objects.filter(
        create_time__lt=timezone.now() - timedelta(days=config.sub_task_alive_days)
    ).values_list("id", flat=True)[0]
    # 下一次从本轮的最后一个 task 开始
    next_begin: int = sub_tasks[-1]["id"]
    # 在到达最右端时重置
    config.begin = (next_begin, 0)[next_begin >= max_id]
    logger.info("[clean_sub_data] sub_tasks -> %s, max_id -> %s, next_begin -> %s", len(sub_tasks), max_id, next_begin)

    policy_sub_ids: typing.Set[int] = set(
        models.Subscription.objects.filter(category=models.Subscription.CategoryType.POLICY).values_list(
            "id", flat=True
        )
    )
    sub_ids: typing.Set[int] = set()
    sub_task_ids: typing.Set[int] = set()
    task_id__info_map: typing.Dict[int, typing.Dict[str, typing.Any]] = {}
    for sub_task in sub_tasks:
        task_id: int = sub_task["id"]
        sub_id: int = sub_task["subscription_id"]
        if sub_id in policy_sub_ids:
            continue
        sub_ids.add(sub_id)
        sub_task_ids.add(task_id)
        task_id__info_map[task_id] = sub_task

    # 属于 Job 的订阅 ID  -> 清理全部
    job_task_ids = handle_job_delete(config, sub_ids)
    # 其它订阅 ID -> 清理 is_latest = 0
    normal_task_ids: typing.Set[int] = sub_task_ids - job_task_ids
    handle_sub_delete(normal_task_ids, task_id__info_map)


@periodic_task(queue="default", options={"queue": "default"}, run_every=crontab(minute="*/1"))
def clean_sub_data_task():
    config: CleanConfig = get_config()
    if not config.enable:
        logger.info("[clean_sub_data] disable and skipped.")
        return
    clean_sub_data(config)
    # 设置下一次指针
    set_config(config)
