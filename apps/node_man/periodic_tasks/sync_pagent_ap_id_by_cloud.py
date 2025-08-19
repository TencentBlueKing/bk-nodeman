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

from blueapps.contrib.celery_tools.periodic import periodic_task
from django.db import transaction
from django.db.models import Q

from apps.node_man import constants
from apps.node_man.models import Cloud, Host
from common.log import logger


@periodic_task(
    run_every=constants.SYNC_PAGENT_AP_ID_INTERVAL,
    queue="default",
    options={"queue": "default"},
)
def sync_pagent_ap_id_by_cloud_periodic_task():
    """
    定时任务，同步云区域下的接入点ID
    """
    task_id = sync_pagent_ap_id_by_cloud_periodic_task.request.id
    logger.info(f"sync_pagent_ap_id_by_cloud_periodic_task: {task_id} Start sync pagent ap id by cloud.")

    # 获取所有云区域
    clouds = list(Cloud.objects.values("bk_cloud_id", "ap_id"))

    for cloud in clouds:
        # 获取当前云区域下所有主机
        hosts = Host.objects.filter(Q(bk_cloud_id=cloud["bk_cloud_id"]) & ~Q(ap_id=cloud["ap_id"]))

        with transaction.atomic():
            updated_count = hosts.update(ap_id=cloud["ap_id"])
            logger.info(f"Updated {updated_count} hosts in cloud {cloud['bk_cloud_id']} to ap_id {cloud['ap_id']}.")
