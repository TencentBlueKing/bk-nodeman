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
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.backend.sync_task import serializers
from apps.backend.sync_task.handler import AsyncTaskHandler
from apps.generic import APIViewSet

SYNC_TASK_VIEW_TAGS = ["sync_task"]


class SyncTaskViewSet(APIViewSet):
    @swagger_auto_schema(
        operation_id="sync_task_create",
        operation_summary="创建同步任务",
        tags=SYNC_TASK_VIEW_TAGS,
        extra_overrides={"is_register_apigw": True},
    )
    @action(detail=False, methods=["POST"], url_path="create", serializer_class=serializers.CreateSyncTaskSerializer)
    def create_sync_task(self, request):
        """
        @api {POST} /sync_task/create/ 创建同步任务
        @apiName sync_task_create
        @apiGroup backend_sync_task
        """
        params = self.validated_data

        task_name = params["task_name"]
        task_params = params.get("task_params")

        task_handler_func = getattr(AsyncTaskHandler(), task_name)
        task_id = task_handler_func(**task_params) if task_params else task_handler_func()

        return Response({"task_id": task_id})

    @swagger_auto_schema(
        operation_id="sync_task_status",
        operation_summary="查询同步任务状态",
        tags=SYNC_TASK_VIEW_TAGS,
        extra_overrides={"is_register_apigw": True},
    )
    @action(detail=False, methods=["GET"], url_path="status", serializer_class=serializers.SyncTaskStatusSerializer)
    def status(self, request):
        """
        @api {GET} /sync_task/status/ 查询同步任务状态
        @apiName sync_task_status
        @apiGroup backend_sync_task
        """
        task_id = self.validated_data["task_id"]
        result = {"task_id": task_id, "status": AsyncResult(task_id).state}
        return Response(result)
