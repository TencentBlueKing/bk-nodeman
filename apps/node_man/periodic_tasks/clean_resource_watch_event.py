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

from celery.schedules import crontab
from celery.task import periodic_task

from apps.node_man.models import ResourceWatchEvent
from common.log import logger


@periodic_task(
    queue="default",
    options={"queue": "default"},
    run_every=crontab(hour="2", minute="0", day_of_week="*", day_of_month="*", month_of_year="*"),
)
def clean_resource_watch_event_periodic_task():
    """
    每天清理缓存的 CMDB 资源订阅事件，防止异常时 ResourceWatchEvent 不停增长导致 MySQL 慢查询的问题
    """
    logger.info("Start cleaning up resource watch event.")
    ResourceWatchEvent.objects.all().delete()
    logger.info("Clean up resource watch event complete.")
