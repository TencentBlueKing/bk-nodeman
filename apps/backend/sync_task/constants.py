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
from django.conf import settings

from apps.utils.basic import tuple_choices, choices_to_namedtuple

SYNC_TASK_TUPLE = ("sync_cmdb_host",)
SYNC_TASK_CHOICES = tuple_choices(SYNC_TASK_TUPLE)
SyncTaskType = choices_to_namedtuple(SYNC_TASK_CHOICES)

SYNC_TASK_IMPORT_PATH_MAP = {
    SyncTaskType.sync_cmdb_host: "apps.backend.sync_task.tasks.sync_cmdb_host.sync_cmdb_host_task"
}

# 同步 CMDB 主机缓存键名模板
SYNC_CMDB_HOST_KEY_TPL = f"{settings.APP_CODE}:backend:sync_task:sync_cmdb_host:" + "biz:{bk_biz_id}"
