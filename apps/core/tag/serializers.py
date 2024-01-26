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

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from apps.node_man.constants import BUILT_IN_TAG_DESCRIPTIONS

from . import constants, exceptions, models


class TagCreateSerializer(serializers.Serializer):

    name = serializers.CharField(label=_("标签名称"), max_length=120, min_length=1)
    target_type = serializers.ChoiceField(label=_("目标类型"), choices=constants.TargetType.list_choices())
    target_id = serializers.IntegerField(label=_("目标 ID"))
    target_version = serializers.CharField(label=_("指向版本号"), max_length=120, min_length=1)

    def validate(self, attrs):
        # 不允许 name & target_type & target_id 重复，这种情况下应该走更新
        if models.Tag.objects.filter(
            name=attrs["name"], target_type=attrs["target_type"], target_id=attrs["target_id"]
        ).exists():
            raise exceptions.TagAlreadyExistsError

        # 目标版本和标签名称不能一样
        if attrs["name"] == attrs["target_version"]:
            raise exceptions.TagInvalidNameError(
                {
                    "err_msg": _("标签名（{name}）不能与目标版本（{target_version}）一致").format(
                        name=attrs["name"], target_version=attrs["target_version"]
                    )
                }
            )
        return attrs


class TagUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Tag
        fields = ["target_version", "description", "to_top"]

    def validate(self, attrs):
        if "description" in attrs and attrs["description"] in BUILT_IN_TAG_DESCRIPTIONS:
            raise exceptions.ValidationError(_(f"不可将标签描述设置为内置标签描述{BUILT_IN_TAG_DESCRIPTIONS}"))

        return attrs
