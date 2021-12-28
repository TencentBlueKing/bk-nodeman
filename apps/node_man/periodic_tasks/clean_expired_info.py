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
from celery.task import periodic_task
from django.utils import timezone

from apps.node_man import constants
from apps.node_man.models import IdentityData
from common.log import logger


def clean_identity_data(task_id, start, end):
    identity_bk_host_ids = (
        IdentityData.objects.filter(retention=1, updated_at__lte=timezone.now() - timezone.timedelta(days=1))
        .exclude(key=None, password=None, extra_data=None)
        .values_list(flat=True)[start:end]
    )
    if not identity_bk_host_ids:
        # 结束递归
        return

    logger.info(
        f"{task_id} | "
        f"Clean up the host authentication information with a retention period of one day.[{start}-{end}]"
    )
    IdentityData.objects.filter(bk_host_id__in=list(identity_bk_host_ids)).update(
        key=None, password=None, extra_data=None
    )
    clean_identity_data(task_id, end, end + constants.QUERY_EXPIRED_INFO_LENS)


@periodic_task(
    queue="default",
    options={"queue": "default"},
    run_every=constants.CLEAN_EXPIRED_INFO_INTERVAL,
)
def clean_expired_info_periodic_task():
    """
    清理保留期限为一天的主机认证信息
    """
    # 清除过期的账户信息
    task_id = clean_expired_info_periodic_task.request.id
    logger.info(f"{task_id} | Start cleaning host authentication information.")
    clean_identity_data(task_id, 0, constants.QUERY_EXPIRED_INFO_LENS)
    logger.info(f"{task_id} | Clean up the host authentication information complete.")
