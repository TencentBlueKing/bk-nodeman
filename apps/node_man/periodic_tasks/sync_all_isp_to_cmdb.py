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

import time
from typing import Any, Dict, List

from celery.task import periodic_task

from apps.component.esbclient import client_v2
from apps.exceptions import ComponentCallError
from apps.node_man import constants
from apps.node_man.models import Cloud, GlobalSettings
from apps.utils.basic import chunk_lists
from common.log import logger


def sync_all_isp_to_cmdb(task_id):
    logger.info(f"{task_id} | Start syncing cloud isp info.")
    # CMDB内置云区域不更新
    cmdb_internal_cloud_ids = GlobalSettings.get_config(
        key=GlobalSettings.KeyEnum.CMDB_INTERNAL_CLOUD_IDS.value, default=[]
    )
    cloud_info: List[Dict[str, Any]] = list(Cloud.objects.values("bk_cloud_id", "isp"))
    # 分片请求：一次五十条
    for chunk_clouds in chunk_lists(cloud_info, constants.UPDATE_CMDB_CLOUD_AREA_LIMIT):
        for cloud in chunk_clouds:
            bk_cloud_id: int = cloud["bk_cloud_id"]
            if bk_cloud_id in cmdb_internal_cloud_ids:
                continue
            bk_cloud_vendor: str = constants.CMDB_CLOUD_VENDOR_MAP.get(cloud["isp"])
            try:
                client_v2.cc.update_cloud_area({"bk_cloud_id": bk_cloud_id, "bk_cloud_vendor": bk_cloud_vendor})
            except ComponentCallError as e:
                logger.error("esb->call update_cloud_area error %s" % e.message)
                client_v2.cc.update_inst(bk_obj_id="plat", bk_inst_id=bk_cloud_id, bk_cloud_vendor=bk_cloud_vendor)
        # 休眠1秒避免一次性全量请求导致接口超频
        time.sleep(1)

    logger.info(f"{task_id} | Sync cloud isp info task complete.")


@periodic_task(
    queue="default",
    options={"queue": "default"},
    run_every=constants.SYNC_ISP_TO_CMDB_INTERVAL,
)
def sync_all_isp_to_cmdb_periodic_task():
    """
    同步云服务商至CMDB
    """
    task_id = sync_all_isp_to_cmdb_periodic_task.request.id
    sync_all_isp_to_cmdb(task_id)
