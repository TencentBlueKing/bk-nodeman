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

from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from apps.generic import ModelViewSet
from apps.node_man.constants import BUILT_IN_TAG_NAMES
from apps.utils import orm

from . import constants, handlers, models, permission, serializers
from .exceptions import ValidationError

TAG_VIEW_TAGS = ["tag"]


class TagViewSet(ModelViewSet):
    URL_BASE_NAME = "tag"

    model = models.Tag
    permission_classes = (permission.TagPermission,)
    http_method_names = ["get", "head", "post", "patch", "delete"]

    def get_serializer_class(self, *args, **kwargs):
        action_serializer_map = {
            "create": serializers.TagCreateSerializer,
            "partial_update": serializers.TagUpdateSerializer,
        }
        serializer_class = action_serializer_map.get(self.action)
        if not serializer_class:
            serializer_class = super().get_serializer_class(*args, **kwargs)
        return serializer_class

    @swagger_auto_schema(
        operation_summary="将标签视为版本，发布到对应目标",
        tags=TAG_VIEW_TAGS,
    )
    def create(self, request, *args, **kwargs):
        tag: models.Tag = handlers.TagHandler.publish_tag_version(
            name=self.validated_data["name"],
            target_type=self.validated_data["target_type"],
            target_id=self.validated_data["target_id"],
            target_version=self.validated_data["target_version"],
        )
        return Response(orm.model_to_dict(tag))

    def perform_update(self, serializer):
        instance = serializer.instance
        if instance.name in BUILT_IN_TAG_NAMES:
            raise ValidationError(_("内置标签不允许修改"))

        # 仅需更新描述信息的情况
        if "target_version" not in serializer.validated_data:
            serializer.save()
            return

        # 用于 publish_tag_version 的关键信息属于只读数据，所以可以用更新前快照传参
        tag_before_update: models.Tag = self.get_object()
        handlers.TagHandler.publish_tag_version(
            name=tag_before_update.name,
            target_type=tag_before_update.target_type,
            target_id=tag_before_update.target_id,
            target_version=serializer.validated_data["target_version"],
        )
        serializer.save()

    @swagger_auto_schema(
        operation_summary="去除对应标签",
        tags=TAG_VIEW_TAGS,
    )
    def perform_destroy(self, instance: models.Tag):
        if instance.name in BUILT_IN_TAG_NAMES:
            raise ValidationError(_("内置标签不允许删除"))

        handlers.TagHandler.delete_tag_version(
            name=instance.name,
            target_type=instance.target_type,
            target_id=instance.target_id,
            target_version=instance.target_version,
        )


class TagChangeRecordViewSet(ModelViewSet):
    URL_BASE_NAME = "tag_change_record"

    model = models.TagChangeRecord
    http_method_names = ["get", "head"]

    filter_backends = (DjangoFilterBackend, OrderingFilter)

    ordering_fields = ["created_time", "updated_time", "tag_id"]
    filterset_fields = {
        "id": ["exact", "in"],
        "tag_id": ["exact", "in"],
        "target_version": ["exact", "in"],
        "created_by": ["exact", "in"],
        "updated_by": ["exact", "in"],
    }

    def get_queryset(self):
        # 仅需展示版本变更情况，无需展示同版本覆盖的数据
        return models.TagChangeRecord.objects.filter(~Q(action=constants.TagChangeAction.OVERWRITE.value))
