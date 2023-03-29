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
from django.core.cache import cache

from apps.backend.sync_task import constants
from apps.backend.sync_task.manager import AsyncTaskManager


class AsyncTaskHandler:
    """写入同步任务的公共逻辑，提供给多方调用"""
    @staticmethod
    def sync_cmdb_host(bk_biz_id=None):
        # 获取缓存中该业务主机是否正在同步
        task_key_tpl = constants.SYNC_CMDB_HOST_KEY_TPL
        task_id = None
        if bk_biz_id:
            task_id = cache.get(task_key_tpl.format(bk_biz_id=bk_biz_id))
        if not task_id:
            task_id = cache.get(task_key_tpl.format(bk_biz_id="all"))
        if task_id:
            return task_id

        async_task = AsyncTaskManager()
        async_task.as_task(constants.SyncTaskType.sync_cmdb_host)
        task_id = async_task.delay(bk_biz_id=bk_biz_id)

        cache.set(task_key_tpl.format(bk_biz_id=bk_biz_id if bk_biz_id else "all"), task_id, 10)

        return task_id
