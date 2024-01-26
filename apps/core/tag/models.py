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
    name = models.CharField(_("标签名称"), max_length=128, db_index=True)
    to_top = models.BooleanField(_("标签是否置顶"), default=False)
    description = models.TextField(_("标签描述"), default="", null=True)
    target_type = models.CharField(_("目标类型"), max_length=20, choices=constants.TargetType.list_choices())
    target_id = models.IntegerField(_("目标 ID"), db_index=True)
    target_version = models.CharField(_("指向版本号"), max_length=128, db_index=True)

    class Meta:
        verbose_name = _("标签")
        verbose_name_plural = _("标签")
        # 唯一性校验
        unique_together = (("target_type", "target_id", "name", "target_version"),)
        index_together = [
            ["target_id", "target_type"],
        ]


class TagChangeRecord(orm.OperateRecordModel):
    tag_id = models.IntegerField(_("标签 ID"))
    action = models.CharField(_("变更动作"), max_length=20, choices=constants.TagChangeAction.list_choices())
    target_version = models.CharField(_("指向版本号"), max_length=128)

    class Meta:
        verbose_name = _("标签变更记录")
        verbose_name_plural = _("标签变更记录")


class VisibleRange(orm.OperateRecordModel):
    """
    A. 包对业务可见需满足任一条件：
        1. bk_biz_id == bk_biz_id
        2. bk_obj_id=biz, bk_biz_id in bk_inst_scope
        3. is_public
    B. 包对主机可用满足任一可见范围约束
    """

    name = models.CharField(_("构件名称"), max_length=128)
    version = models.CharField(_("构件版本"), max_length=128)
    target_type = models.CharField(_("目标类型"), max_length=20, choices=constants.TargetType.list_choices())
    is_public = models.BooleanField(_("是否全部可见"), default=False)
    # bk_obj_id 不为业务时必填
    bk_biz_id = models.IntegerField(_("业务ID"), default=None, null=True)
    bk_obj_id = models.CharField(_("CMDB对象ID"), max_length=32, null=True)
    bk_inst_scope = models.JSONField(_("CMDB实例ID范围"), default=list)

    class Meta:
        verbose_name = _("版本可见范围")
        verbose_name_plural = _("版本可见范围")
