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
from typing import Dict, List

from celery.task import periodic_task
from django.db import transaction

from apps.backend.subscription.tools import search_business
from apps.core.gray.handlers import GrayHandler
from apps.node_man.constants import SYNC_BIZ_TO_GRAY_SCOPE_LIST_INTERVAL
from apps.node_man.models import GlobalSettings
from common.log import logger


@periodic_task(
    queue="default",
    options={"queue": "default"},
    run_every=SYNC_BIZ_TO_GRAY_SCOPE_LIST_INTERVAL,
)
def sync_new_biz_to_gray_scope_list():
    """
    添加新增业务到灰度列表
    """
    task_id = sync_new_biz_to_gray_scope_list.request.id
    logger.info(f"sync_new_biz_to_gray_scope_list: {task_id} Start adding new biz to GSE2_GRAY_SCOPE_LIST.")

    all_biz_ids = GlobalSettings.get_config(key=GlobalSettings.KeyEnum.ALL_BIZ_IDS.value, default=[])
    if not all_biz_ids:
        logger.info(f"sync_new_biz_to_gray_scope_list: {task_id} No need to add new biz to GSE2_GRAY_SCOPE_LIST.")
        return None

    cc_all_biz: List[Dict[str, int]] = search_business({})
    cc_all_biz_ids: List[int] = [biz["bk_biz_id"] for biz in cc_all_biz]
    new_biz_ids: List[int] = list(set(cc_all_biz_ids) - set(all_biz_ids))

    logger.info(f"sync_new_biz_to_gray_scope_list: {task_id} new biz ids: {new_biz_ids}.")
    if new_biz_ids:
        with transaction.atomic():
            # 更新全部业务列表
            all_biz_ids.extend(new_biz_ids)
            GlobalSettings.update_config(key=GlobalSettings.KeyEnum.ALL_BIZ_IDS.value, value=list(set(all_biz_ids)))

            # 对新业务执行灰度操作
            result = GrayHandler.build({"bk_biz_ids": new_biz_ids})
            logger.info(f"sync_new_biz_to_gray_scope_list: {task_id}  New biz: {new_biz_ids} Build result: {result}")

    logger.info(f"sync_new_biz_to_gray_scope_list: {task_id} Add new biz to GSE2_GRAY_SCOPE_LIST completed.")
