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
from django.utils.module_loading import import_string

from apps.backend.sync_task import constants


class AsyncTaskManager:
    """异步函数通用管理"""
    def __init__(self, task_id=None, task_func=None):
        self.task_id = task_id
        self.task_func = task_func

    def as_task(self, task_name):
        task_import_path_map = constants.SyncTaskType.get_member__import_path_map()
        task_import_path = task_import_path_map[task_name]
        self.task_func = import_string(task_import_path)

    def delay(self, *args, **kwargs):
        self.task_id = self.task_func.delay(*args, **kwargs).id
        return self.task_id
