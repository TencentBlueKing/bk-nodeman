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
import datetime

from celery.task import periodic_task
from django.core.cache import cache

from apps.node_man import constants
from common.log import logger
from requests_tracker.models import Config, Record


@periodic_task(
    queue="default",
    options={"queue": "default"},
    run_every=constants.CLEAN_REQUESTS_TRACKER_RECORDS_INTERVAL,
)
def clean_requests_tracker_records_periodic_task():
    # 检查组件请求记录，清空2天前的记录
    logger.info("Start cleaning up requests tracker records.")
    two_days_before = datetime.datetime.now() - datetime.timedelta(days=2)
    Record.objects.filter(
        date_created__lte=two_days_before,
    ).order_by("id").delete()
    logger.info("Clean up requests tracker records complete.")

    # 定时关闭request tracker，避免排查问题时忘记关闭产生大量record
    Config.objects.filter(key="is_track").update(value=False)
    cache.set("is_track", False)
