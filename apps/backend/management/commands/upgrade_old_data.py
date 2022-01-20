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
from __future__ import absolute_import, unicode_literals

import time

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.node_man import constants, models
from apps.utils.time_handler import strftime_local
from common.log import logger


def log_and_print(log):
    # 实时打屏显示进度
    log = f"[{strftime_local(timezone.now())} upgrade_old_data] {log}"
    logger.info(log)
    print(log)


class Command(BaseCommand):
    def handle(self, *args, **options):

        begin_time = time.time()
        with transaction.atomic():
            # subscription_task 全量更新为True
            task_update_count = models.SubscriptionTask.objects.update(is_ready=True)

            # AIX类型主机 cpu_arch 变更为 powerpc
            host_update_count = models.Host.objects.filter(os_type=constants.OsType.AIX).update(
                cpu_arch=constants.CpuType.powerpc
            )

        log_and_print(
            f"数据更新完成：task_update_count -> {task_update_count}, host_update_count -> {host_update_count}, "
            f"cost_time -> {time.time() - begin_time}"
        )
