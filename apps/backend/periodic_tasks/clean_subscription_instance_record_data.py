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

from typing import Dict, Union

from celery.schedules import crontab
from celery.task import periodic_task
from django.db import connection
from django.utils import timezone

from apps.backend.constants import DEFAULT_ALIVE_TIME, DEFAULT_CLEAN_RECORD_LIMIT
from apps.node_man import models
from apps.prometheus import metrics
from apps.prometheus.helper import observe
from apps.utils.time_handler import strftime_local
from common.log import logger

SUBSCRIPTION_INSTANCE_RECORD_TABLE = "node_man_subscriptioninstancerecord"
SUBSCRIPTION_TASK_TABLE = "node_man_subscriptiontask"
PIPELINE_TREE_TABLE = "node_man_pipelinetree"


@periodic_task(
    queue="default",
    options={"queue": "default"},
    run_every=crontab(minute="*/5"),
)
def clean_subscription_instance_record_data():
    # 清理数据开关以及相关配置
    enable_clean_subscription_data, limit, alive_days = get_configuration()

    if not enable_clean_subscription_data:
        logger.info("clean_subscription_data is not enable, delete subscription data will be skipped")
        return

    logger.info(
        f"periodic_task -> clean_subscription_instance_record_data, "
        f"start to clean subscription instance record and pipeline tree data,"
        f" alive_days: {alive_days}, limit: {limit}"
    )

    with connection.cursor() as cursor:
        policy_subscription_ids = get_policy_subscription_ids(cursor)

        need_clean_task_ids = get_need_clean_task_ids(cursor, policy_subscription_ids, alive_days, limit)

        if not need_clean_task_ids:
            logger.info(
                "need clean instance records_ids is empty, " "delete subscription instance record data will be skipped"
            )
            return

        need_clean_pipeline_tree_ids = get_need_clean_pipeline_tree_ids(cursor, need_clean_task_ids)

        # 删除 subscription instance record 表数据
        delete_subscription_instance_record_sql = generate_delete_sql(
            SUBSCRIPTION_INSTANCE_RECORD_TABLE,
            {"field": "subscription_id", "value": policy_subscription_ids, "reverse": True},
            alive_days,
            {"field": "is_latest", "value": 0},
            limit,
        )
        delete_data(
            cursor,
            SUBSCRIPTION_INSTANCE_RECORD_TABLE,
            delete_subscription_instance_record_sql,
            need_clean_task_ids,
        )

        # 删除 subscription task 表数据
        delete_subscription_task_sql = generate_delete_sql(
            SUBSCRIPTION_TASK_TABLE,
            {"field": "id", "value": need_clean_task_ids},
        )
        delete_data(
            cursor,
            SUBSCRIPTION_TASK_TABLE,
            delete_subscription_task_sql,
            need_clean_task_ids,
        )

        if need_clean_pipeline_tree_ids:
            # 删除 pipeline tree 表数据
            delete_pipeline_tree_sql = generate_delete_sql(
                PIPELINE_TREE_TABLE,
                {"field": "id", "value": need_clean_pipeline_tree_ids},
            )
            delete_data(cursor, PIPELINE_TREE_TABLE, delete_pipeline_tree_sql, need_clean_pipeline_tree_ids)


def log_sql(sql_str: str):
    logger.info(
        f"periodic_task -> clean_subscription_instance_record_data, time -> {strftime_local(timezone.now())}, "
        f"start to execute sql -> [{sql_str}]"
    )


def generate_scope_query(fields_name: str, scopes: list) -> str:
    if not scopes:
        return ""

    if len(scopes) == 1:
        return f"{fields_name}='{scopes[0]}'"

    return f"{fields_name} in {tuple(scopes)}"


def get_configuration():
    """获取 settings 配置数据"""
    clean_subscription_data_map: Dict[str, Union[int, str, bool]] = (
        models.GlobalSettings.get_config(models.GlobalSettings.KeyEnum.CLEAN_SUBSCRIPTION_DATA_MAP.value) or {}
    )
    enable_clean_subscription_data: bool = clean_subscription_data_map.get("enable_clean_subscription_data", True)
    limit: int = clean_subscription_data_map.get("limit", DEFAULT_CLEAN_RECORD_LIMIT)
    alive_days: int = clean_subscription_data_map.get("alive_days", DEFAULT_ALIVE_TIME)
    return enable_clean_subscription_data, limit, alive_days


def get_policy_subscription_ids(cursor):
    """获取策略类型任务"""
    select_policy_subscription_sql: str = (
        f"SELECT id FROM node_man_subscription " f"WHERE category = '{models.Subscription.CategoryType.POLICY}';"
    )
    cursor.execute(select_policy_subscription_sql)
    return [row[0] for row in cursor.fetchall()]


def get_need_clean_task_ids(cursor, policy_subscription_ids: list, alive_days, limit):
    """获取需要清理的 instance_record_ids"""
    if policy_subscription_ids:
        select_clean_records_sql: str = (
            f"SELECT DISTINCT task_id FROM {SUBSCRIPTION_INSTANCE_RECORD_TABLE} "
            f"WHERE NOT({generate_scope_query('subscription_id', policy_subscription_ids)}) "
            f"AND create_time < DATE_SUB(NOW(), INTERVAL {alive_days} DAY) AND is_latest = 0  LIMIT {limit};"
        )
    else:
        select_clean_records_sql: str = (
            f"SELECT DISTINCT task_id FROM {SUBSCRIPTION_INSTANCE_RECORD_TABLE} "
            f"WHERE create_time < DATE_SUB(NOW(), INTERVAL {alive_days} DAY) AND is_latest = 0  LIMIT {limit};"
        )
    cursor.execute(select_clean_records_sql)
    return [row[0] for row in cursor.fetchall()]


def get_need_clean_pipeline_tree_ids(cursor, need_clean_task_ids: list):
    """获取需要清理的 pipeline_tree_ids"""
    select_pipeline_ids_sql: str = (
        f"SELECT pipeline_id from {SUBSCRIPTION_TASK_TABLE} "
        f"WHERE {generate_scope_query('id', need_clean_task_ids)} "
        f"AND pipeline_id <> '';"
    )
    cursor.execute(select_pipeline_ids_sql)
    return [row[0] for row in cursor.fetchall()]


def generate_delete_sql(
    table_name: str,
    scope: Dict[str, Union[str, bool, list]],
    time_cond: int = None,
    additional_cond: dict = None,
    limit: int = None,
):
    """生成删除语句"""
    scope_query: str = generate_scope_query(scope["field"], scope["value"]) if scope else ""
    if scope_query and scope.get("reverse"):
        scope_query: str = f"NOT({scope_query})"

    time_query: str = f" AND create_time < DATE_SUB(NOW(), INTERVAL {time_cond} DAY)" if time_cond else ""
    additional_query: str = f" AND {additional_cond['field']} = {additional_cond['value']}" if additional_cond else ""
    limit_query: str = f" LIMIT {limit}" if limit else ""

    delete_sql: str = f"DELETE FROM {table_name} WHERE {scope_query}{time_query}{additional_query}{limit_query};"
    return delete_sql


def delete_data(cursor, table_name: str, sql: str, ids: list):
    """删除数据并记录metrics"""
    log_sql(sql)
    with observe(metrics.app_clean_subscription_instance_records_seconds, sql=sql):
        cursor.execute(sql)
    metrics.app_clean_subscription_instance_records_total.labels(table_name=table_name).inc(len(ids))
