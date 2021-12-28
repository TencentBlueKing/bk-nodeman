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

from apps.component.esbclient import client_v2
from apps.exceptions import ComponentCallError
from apps.node_man import constants
from apps.node_man.models import AccessPoint, Cloud
from common.log import logger


def update_or_create_cloud_area(task_id, start):
    logger.info(f"{task_id} | Sync cloud area task start.[{start}-{start + constants.QUERY_CLOUD_LIMIT}]")

    # 查询云区域兼容低版本paas无search_cloud_area情况
    try:
        plats = client_v2.cc.search_cloud_area({"page": {"start": start, "limit": constants.QUERY_CLOUD_LIMIT}})
    except ComponentCallError as e:
        logger.error(f"{task_id} | call search_cloud_area error {e.message}")
        plats = client_v2.cc.search_inst({"bk_obj_id": "plat"})

    cloud_list = plats.get("info") or []
    cloud_count = plats.get("count", 0)

    if not cloud_list:
        logger.info(f"{task_id} | sync_cmdb_cloud_area query cloud area is empty.")

    cc_cloud_id_list = [cloud["bk_cloud_id"] for cloud in cloud_list]

    exist_cloud_ids = Cloud.objects.filter(bk_cloud_id__in=cc_cloud_id_list).values_list("bk_cloud_id", flat=True)

    need_update_cloud = []
    need_create_cloud = []

    access_points = AccessPoint.objects.all()
    if access_points.count() == 1:
        default_ap_id = access_points[0].id
    else:
        default_ap_id = constants.DEFAULT_AP_ID

    # 存在的批量更新，不存在的批量创建
    for _cloud in cloud_list:
        # 默认云区域不同步
        if _cloud["bk_cloud_id"] == constants.DEFAULT_CLOUD:
            continue
        elif _cloud["bk_cloud_id"] in exist_cloud_ids:
            need_update_cloud.append(Cloud(bk_cloud_id=_cloud["bk_cloud_id"], bk_cloud_name=_cloud["bk_cloud_name"]))
        else:
            need_create_cloud.append(
                Cloud(
                    bk_cloud_id=_cloud["bk_cloud_id"],
                    bk_cloud_name=_cloud["bk_cloud_name"],
                    ap_id=default_ap_id,
                    creator=["system"],
                    isp="PrivateCloud",
                )
            )

    Cloud.objects.bulk_create(need_create_cloud)
    Cloud.objects.bulk_update(need_update_cloud, fields=["bk_cloud_name"])

    if cloud_count > start + constants.QUERY_CLOUD_LIMIT:
        update_or_create_cloud_area(task_id, start + constants.QUERY_CLOUD_LIMIT)


@periodic_task(
    queue="default",
    options={"queue": "default"},
    run_every=constants.SYNC_CMDB_CLOUD_AREA_INTERVAL,
)
def sync_cmdb_cloud_area_periodic_task():
    """
    同步CMDB云区域
    """
    task_id = sync_cmdb_cloud_area_periodic_task.request.id
    logger.info(f"{task_id} | Start syncing cloud area.")
    update_or_create_cloud_area(task_id, 0)
    logger.info(f"{task_id} | Sync cloud area task complete.")
