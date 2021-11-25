# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from django.db import models
from django.utils.translation import ugettext_lazy as _

from . import constants


class RSAKey(models.Model):
    name = models.CharField(_("密钥名称"), max_length=128)
    type = models.CharField(_("密钥类型"), max_length=64, choices=constants.RSAKeyType.list_choices())
    description = models.TextField(_("密钥描述"), default="", null=True)
    content = models.TextField(_("密钥内容"))

    update_time = models.DateTimeField(_("更新时间"), auto_now=True)
    create_time = models.DateTimeField(_("创建时间"), auto_now_add=True)

    class Meta:
        verbose_name = _("RSA密钥")
        verbose_name_plural = _("RSA密钥")
        # 唯一性校验，name-type
        unique_together = (("name", "type"),)
