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

from django.contrib import admin

from . import models


@admin.register(models.Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "name",
        "to_top",
        "description",
        "target_type",
        "target_id",
        "target_version",
        "created_time",
        "created_by",
        "updated_time",
        "updated_by",
    ]
    search_fields = ["id", "name", "type", "target_version"]
    list_filter = ["target_type", "to_top"]


@admin.register(models.TagChangeRecord)
class TagChangeRecordAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "tag_id",
        "action",
        "target_version",
        "created_time",
        "created_by",
        "updated_time",
        "updated_by",
    ]
    list_filter = ["action"]
    search_fields = ["target_version"]


@admin.register(models.VisibleRange)
class VisibleRangeAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "name",
        "version",
        "target_type",
        "is_public",
        "bk_biz_id",
        "bk_obj_id",
        "bk_inst_scope",
    ]
    list_filter = ["target_type", "is_public", "bk_obj_id"]
    search_fields = ["id", "name", "version", "target_type", "bk_biz_id"]
