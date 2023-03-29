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
from celery.result import AsyncResult
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.generic import APIViewSet
from apps.node_man.handlers.sync_task import SyncTaskHandler
from apps.node_man.serializers.sync_task import CreateSyncTaskSerializer, TaskStatusSerializer


class SyncTaskViewSet(APIViewSet):
    @action(detail=False, methods=["POST"], url_path="create", serializer_class=CreateSyncTaskSerializer)
    def create_sync_task(self, request):
        validated_data = self.validated_data
        task_name = validated_data["task_name"]

        if not task_name or not hasattr(SyncTaskHandler, task_name):
            raise AttributeError(f"SyncTaskHandler does not have this property: {task_name}")

        task_handler_func = getattr(SyncTaskHandler(), task_name)
        task_id = task_handler_func(**validated_data)

        return Response({"task_id": task_id})

    @action(detail=False, methods=["GET"], serializer_class=TaskStatusSerializer)
    def status(self, request):
        validated_data = self.validated_data
        task_id = validated_data["task_id"]

        result = {"task_id": task_id, "status": AsyncResult(task_id).get()}

        return Response(result)
