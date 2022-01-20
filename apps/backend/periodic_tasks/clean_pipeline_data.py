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

from celery.schedules import crontab
from celery.task import periodic_task
from django.utils import timezone

from apps.backend.management.commands import clean_old_instance_record
from apps.node_man import models
from apps.utils.time_handler import strftime_local

logger = logging.getLogger("celery")


@periodic_task(
    queue="default",
    options={"queue": "default"},
    run_every=crontab(hour="1-8", minute="*/5"),
)
def clean_pipeline_data():

    logger.info(f"periodic_task -> clean_pipeline_data, time -> {strftime_local(timezone.now())} start")
    clean_pipeline_data_record_key = "clean_pipeline_data_record_key"
    clean_pipeline_data_record = models.GlobalSettings.get_config(clean_pipeline_data_record_key)

    if not clean_pipeline_data_record:
        clean_pipeline_data_record = {"pipeline_begin": 0, "clean_record": {}, "limit": 500}
        models.GlobalSettings.set_config(clean_pipeline_data_record_key, clean_pipeline_data_record)

    pipeline_begin = clean_pipeline_data_record["pipeline_begin"]
    total_record_num = models.SubscriptionInstanceRecord.objects.filter(is_latest=False, start_pipeline_id="").count()
    if total_record_num < pipeline_begin:
        logger.info(
            f"periodic_task -> clean_pipeline_data, time -> {strftime_local(timezone.now())}, "
            f"total_record_num -> {total_record_num}, pipeline_begin -> {pipeline_begin}, reset to 0"
        )
        # 指针复位，循环扫描冗余数据
        pipeline_begin = 0

    pipeline_end = min(pipeline_begin + clean_pipeline_data_record["limit"], total_record_num + 1)

    log_content = clean_old_instance_record.clean_old_instance_record_handler(
        pipeline_begin, pipeline_end, clean_type=clean_old_instance_record.CleanType.OLD_INSTANCE_RECORD
    )

    clean_pipeline_data_record["pipeline_begin"] = pipeline_end

    # 对升级暂存的Pipeline数据进行清理
    if models.GlobalSettings.objects.filter(key__endswith="to_be_deleted_pipeline_id").exists():
        clean_transfer_data_log_content = clean_old_instance_record.clean_old_instance_record_handler(
            clean_type=clean_old_instance_record.CleanType.TRANSFER, limit=clean_pipeline_data_record["limit"]
        )
        logger.info(
            f"periodic_task -> clean_transfer_pipeline_data, time -> {strftime_local(timezone.now())}, "
            f"log -> {clean_transfer_data_log_content}"
        )
    else:
        logger.info("没有升级暂存的待删除Pipeline")

    models.GlobalSettings.update_config(clean_pipeline_data_record_key, clean_pipeline_data_record)

    logger.info(f"periodic_task -> clean_pipeline_data, time -> {strftime_local(timezone.now())} log -> {log_content}")
