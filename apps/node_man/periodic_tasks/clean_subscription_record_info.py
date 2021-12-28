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
from celery.schedules import crontab
from celery.task import periodic_task
from django.utils import timezone

from apps.node_man import models
from apps.node_man.models import SubscriptionInstanceRecord
from common.log import logger

KEY = "UPDATE_SUBSCRIPTION_INSTANCE_RECORD__LAST_ID"


def update_subscription_instance_record(task_id):
    logger.info(f"{task_id} | clean_subscription_record_info: Start of cleaning up subscription records.]")

    last_sub_task_id = models.GlobalSettings.get_config(KEY, None)
    if last_sub_task_id is None:
        last_sub_task_id = 0
        models.GlobalSettings.set_config(KEY, last_sub_task_id)

    last_sub_inst_record = (
        SubscriptionInstanceRecord.objects.filter(update_time__lte=timezone.now() - timezone.timedelta(days=1))
        .order_by("-id")
        .first()
    )

    record_query_set = SubscriptionInstanceRecord.objects.filter(
        id__gte=last_sub_task_id,
        update_time__lte=timezone.now() - timezone.timedelta(days=1),
        need_clean=True,
    )

    last_sub_task_id = last_sub_inst_record.id or 0

    # 结束递归
    if not record_query_set:
        models.GlobalSettings.update_config(KEY, last_sub_task_id)
        return

    for record in record_query_set:
        if isinstance(record.instance_info, dict):
            try:
                if record.instance_info["host"].get("password"):
                    record.instance_info["host"]["password"] = ""
                if record.instance_info["host"].get("key"):
                    record.instance_info["host"]["key"] = ""
            except (KeyError, TypeError):
                pass
            record.need_clean = False
            record.save()

    models.GlobalSettings.update_config(KEY, last_sub_task_id)


@periodic_task(
    queue="default",
    options={"queue": "default"},
    run_every=crontab(hour="0", minute="0", day_of_week="*", day_of_month="*", month_of_year="*"),
)
def clean_subscription_record_info_periodic_task():
    # 清除订阅记录中过期的密码信息
    task_id = clean_subscription_record_info_periodic_task.request.id
    logger.info(f"{task_id} | Start cleaning up subscription records.")
    update_subscription_instance_record(task_id)
    logger.info(f"{task_id} | Clean up subscription records complete.")
