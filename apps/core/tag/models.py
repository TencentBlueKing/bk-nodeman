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

from django.db import models
from django.utils.translation import ugettext_lazy as _

from apps.utils import orm

from . import constants


class Tag(orm.OperateRecordModel):
    name = models.CharField(_("标签名称"), max_length=128)
    to_top = models.BooleanField(_("标签是否置顶"), default=False)
    description = models.TextField(_("标签描述"), default="", null=True)
    target_type = models.CharField(_("目标类型"), max_length=20, choices=constants.TargetType.list_choices())
    target_id = models.IntegerField(_("目标 ID"))
    target_version = models.CharField(_("指向版本号"), max_length=128)

    class Meta:
        verbose_name = _("标签")
        verbose_name_plural = _("标签")
        # 唯一性校验
        unique_together = (("target_type", "target_id", "name"),)


class TagChangeRecord(orm.OperateRecordModel):
    tag_id = models.IntegerField(_("标签 ID"))
    action = models.CharField(_("变更动作"), max_length=20, choices=constants.TagChangeAction.list_choices())
    target_version = models.CharField(_("指向版本号"), max_length=128)

    class Meta:
        verbose_name = _("标签变更记录")
        verbose_name_plural = _("标签变更记录")
