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
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.generic import APIViewSet
from apps.node_man.handlers.permission import SyncTaskPermission
from apps.node_man.serializers.sync_task import CreateSyncTaskSerializer, SyncTaskStatusSerializer
from common.api import NodeApi


class SyncTaskViewSet(APIViewSet):
    permission_classes = (SyncTaskPermission,)

    @action(detail=False, methods=["POST"], url_path="create", serializer_class=CreateSyncTaskSerializer)
    def create_sync_task(self, request):
        """
        @api {POST} /sync_task/create/ 创建同步任务
        @apiName create_sync_task
        @apiGroup sync_task
        """
        validated_data = self.validated_data
        sync_task = NodeApi.create_sync_task(validated_data)

        return Response({"task_id": sync_task["task_id"]})

    @action(detail=False, methods=["GET"], serializer_class=SyncTaskStatusSerializer)
    def status(self, request):
        """
        @api {GET} /sync_task/status/ 同步任务状态
        @apiName sync_task_status
        @apiGroup sync_task
        """
        validated_data = self.validated_data
        task_status = NodeApi.sync_task_status(validated_data)
        result = {"task_id": task_status["task_id"], "status": task_status["status"]}

        return Response(result)
