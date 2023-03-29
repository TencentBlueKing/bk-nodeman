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
from rest_framework import serializers

from apps.backend.sync_task.constants import SYNC_TASK_CHOICES


class CreateSyncTaskSerializer(serializers.Serializer):
    task_name = serializers.ChoiceField(label="任务名称", choices=SYNC_TASK_CHOICES)
    task_params = serializers.DictField(label="任务调用参数", required=False)


class TaskStatusSerializer(serializers.Serializer):
    task_id = serializers.IntegerField(label="任务ID")
