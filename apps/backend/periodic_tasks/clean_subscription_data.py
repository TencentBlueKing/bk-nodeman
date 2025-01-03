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
from typing import Dict, List, Optional, Union

from celery import current_app
from celery.schedules import crontab
from django.db import connection
from django.utils import timezone

from apps.backend.constants import DEFAULT_ALIVE_TIME, DEFAULT_CLEAN_RECORD_LIMIT
from apps.node_man import constants, models
from apps.utils.time_handler import strftime_local
from common.log import logger

SUBSCRIPTION_INSTANCE_DETAIL_TABLE = "node_man_subscriptioninstancestatusdetail"
JOB_SUB_INSTANCE_MAP_TABLE = "node_man_jobsubscriptioninstancemap"


@current_app.task(
    queue="default",
    options={"queue": "default"},
    run_every=crontab(minute="*/5"),
)
def clean_subscription_data():
    """
    周期清理订阅实例状态详情表和作业订阅实例映射表
    """
    clean_subscription_data_map: Dict[str, Union[int, str, bool]] = (
        models.GlobalSettings.get_config(models.GlobalSettings.KeyEnum.CLEAN_SUBSCRIPTION_DATA_MAP.value) or {}
    )

    # 默认开启清理，清理规则：1. 保留最近30天的日志 2. 每次删除最多5000条记录 3.订阅实例状态详情表中，默认保留失败日志 4. job 映射表中，默认清理 FAILED / SUCCESS 的状态记录
    enable_clean_subscription_data: bool = clean_subscription_data_map.get("enable_clean_subscription_data", True)
    if not enable_clean_subscription_data:
        logger.info("clean_subscription_data is not enable, delete subscription data will be skipped")
        return
    limit: int = clean_subscription_data_map.get("limit", DEFAULT_CLEAN_RECORD_LIMIT)
    alive_days: int = clean_subscription_data_map.get("alive_days", DEFAULT_ALIVE_TIME)
    sub_ins_detail_save_log_status: List[str] = clean_subscription_data_map.get(
        "sub_ins_detail_save_log_status", [constants.JobStatusType.FAILED]
    )

    # 默认不删除 job 映射表中的记录，任务执行过程中，如果进行删除，会导致部分任务查不到
    job_map_clean_status: List[int] = clean_subscription_data_map.get("job_map_clean_status", [])

    logger.info(
        f"periodic_task -> clean_subscription_data, start to clean subscription data, clean "
        f"rule: {models.GlobalSettings.KeyEnum.CLEAN_SUBSCRIPTION_DATA_MAP.value} -> [{clean_subscription_data_map}]"
    )

    with connection.cursor() as cursor:
        sub_detail_delete_sqls: List[str] = build_delete_query_sqls(
            table_name=SUBSCRIPTION_INSTANCE_DETAIL_TABLE,
            days=alive_days,
            limit=limit,
            log_save_levels=sub_ins_detail_save_log_status,
        )
        for sub_detail_delete_sql in sub_detail_delete_sqls:
            logger.info(
                f"periodic_task -> clean_subscription_data, time -> {strftime_local(timezone.now())}"
                f"start to execute sql -> [{sub_detail_delete_sql}] "
            )
            cursor.execute(sub_detail_delete_sql)
            logger.info(
                f"periodic_task -> clean_subscription_data, time -> {strftime_local(timezone.now())}, "
                f"deleted subscription instance status detail records -> [{cursor.rowcount}] "
            )

        job_instance_map_delete_sqls: List[str] = build_delete_query_sqls(
            table_name=JOB_SUB_INSTANCE_MAP_TABLE,
            appoint_clean_statuses=job_map_clean_status,
            limit=limit,
        )
        if job_instance_map_delete_sqls:
            for job_instance_map_delete_sql in job_instance_map_delete_sqls:
                logger.info(
                    f"periodic_task -> clean_subscription_data, time -> {strftime_local(timezone.now())}, "
                    f"start to execute sql -> [{job_instance_map_delete_sql}]"
                )
                cursor.execute(job_instance_map_delete_sql)
                logger.info(
                    f"periodic_task -> clean_subscription_data, time -> {strftime_local(timezone.now())}, "
                    f"deleted job instance map records -> [{cursor.rowcount}] "
                )
        else:
            logger.info(
                f"periodic_task -> clean_subscription_data, time -> {strftime_local(timezone.now())}, "
                f"skip delete node_man_jobsubscriptioninstancemap records because appoint_clean_status is empty"
            )


def build_delete_query_sqls(
    table_name: str,
    limit: int,
    days: Optional[int] = None,
    appoint_clean_statuses: Optional[List[int]] = None,
    log_save_levels: Optional[List[str]] = None,
) -> List[str]:
    head_sql: str = f"DELETE FROM {table_name} "

    # 判断是否需要增加时间条件, JOB_SUB_INSTANCE_MAP_TABLE 没有时间条件 并且 limit 条件不根据 create_time 排序
    where_conditions: List[str] = []
    if table_name == JOB_SUB_INSTANCE_MAP_TABLE:
        # appoint_clean_status 为空时，不需要进行后续清理动作
        if not appoint_clean_statuses:
            return
        limit_condition: str = f"limit {limit}"
        where_conditions: str = [f"WHERE status IN ({', '.join([f'{status}' for status in appoint_clean_statuses])})"]
    else:
        time_condition: str = f"create_time < DATE_SUB(NOW(), INTERVAL {days} DAY)"
        limit_condition: str = f"ORDER BY create_time DESC limit {limit}"
        if not log_save_levels:
            where_conditions: List[str] = [f"WHERE {time_condition}"]
        else:
            # 日志表来说，只有 PENDING RUNNING SUCCESS FAILED 几种状态
            delete_log_level: List[str] = [
                job_type
                for job_type in [
                    constants.JobStatusType.PENDING,
                    constants.JobStatusType.RUNNING,
                    constants.JobStatusType.SUCCESS,
                    constants.JobStatusType.FAILED,
                ]
                if job_type not in log_save_levels
            ]
            where_conditions: List[str] = [
                f"WHERE status = '{level}' AND {time_condition}" for level in delete_log_level
            ]

    return [f"{head_sql} {where_condition} {limit_condition}" for where_condition in where_conditions]
