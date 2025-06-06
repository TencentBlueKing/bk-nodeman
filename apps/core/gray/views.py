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
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.generic import APIViewSet

from . import handlers, permission, serializers

GRAY_VIEW_TAGS = ["gray"]


class GrayViewSet(APIViewSet):
    URL_BASE_NAME = "gray"
    permission_classes = (permission.GrayPermission,)

    @swagger_auto_schema(
        operation_id="gray_build",
        operation_summary="GSE 2.0灰度",
        tags=GRAY_VIEW_TAGS,
        extra_overrides={"is_register_apigw": True},
    )
    @action(detail=False, methods=["POST"], serializer_class=serializers.GraySerializer)
    def build(self, request):
        return Response(handlers.GrayHandler.build(self.validated_data))

    @swagger_auto_schema(
        operation_id="gray_rollback",
        operation_summary="GSE 2.0灰度回滚",
        tags=GRAY_VIEW_TAGS,
        extra_overrides={"is_register_apigw": True},
    )
    @action(detail=False, methods=["POST"], serializer_class=serializers.GraySerializer)
    def rollback(self, request):
        return Response(handlers.GrayHandler.rollback(self.validated_data))

    @swagger_auto_schema(
        operation_id="gray_info",
        operation_summary="获取GSE 2.0灰度信息",
        tags=GRAY_VIEW_TAGS,
        responses={status.HTTP_200_OK: serializers.GrayBizSerializer},
        extra_overrides={"is_register_apigw": True},
    )
    @action(detail=False, methods=["GET"])
    def info(self, request):
        return Response({"bk_biz_ids": handlers.GrayHandler.list_biz_ids()})

    @swagger_auto_schema(
        operation_id="upgrade_to_agent_id",
        operation_summary="升级到Agent ID配置",
        tags=GRAY_VIEW_TAGS,
        responses={status.HTTP_200_OK: serializers.UpgradeOrRollbackAgentIDSerializer},
        extra_overrides={"is_register_apigw": True},
    )
    @action(detail=False, methods=["POST"], serializer_class=serializers.GraySerializer)
    def upgrade_to_agent_id(self, request):
        return Response(handlers.GrayHandler.upgrade_to_agent_id(self.validated_data))

    @swagger_auto_schema(
        operation_id="rollback_agent_id",
        operation_summary="回滚Agent ID配置",
        tags=GRAY_VIEW_TAGS,
        responses={status.HTTP_200_OK: serializers.UpgradeOrRollbackAgentIDSerializer},
        extra_overrides={"is_register_apigw": True},
    )
    @action(detail=False, methods=["POST"], serializer_class=serializers.GraySerializer)
    def rollback_agent_id(self, request):
        return Response(handlers.GrayHandler.rollback_agent_id(self.validated_data))
