# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making 蓝鲸智云PaaS平台社区版 (BlueKing PaaS Community
Edition) available.
Copyright (C) 2017-2019 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at
http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from django.db import models
from django.utils.translation import ugettext_lazy as _

from pipeline.component_framework.constants import LEGACY_PLUGINS_VERSION
from pipeline.component_framework.library import ComponentLibrary


class ComponentManager(models.Manager):
    def get_component_dict(self):
        """
        获得标准插件对应的dict类型
        :return:
        """
        components = self.filter(status=True)
        component_dict = {}
        for bundle in components:
            name = bundle.name.split("-")
            group_name = _(name[0])
            name = _(name[1])
            component_dict[bundle.code] = "{}-{}".format(group_name, name)
        return component_dict


class ComponentModel(models.Model):
    """
    注册的组件
    """

    code = models.CharField(_("组件编码"), max_length=255, db_index=True)
    version = models.CharField(_("组件版本"), max_length=64, default=LEGACY_PLUGINS_VERSION, db_index=True)
    name = models.CharField(_("组件名称"), max_length=255, db_index=True)
    status = models.BooleanField(_("组件是否可用"), default=True)

    objects = ComponentManager()

    class Meta:
        verbose_name = _("组件 Component")
        verbose_name_plural = _("组件 Component")
        ordering = ["-id"]

        indexes = [
            models.Index(fields=["code", "version"], name="idx_code_version"),
        ]

    def __unicode__(self):
        return self.name

    @property
    def group_name(self):
        return ComponentLibrary.get_component_class(self.code, self.version).group_name

    @property
    def group_icon(self):
        return ComponentLibrary.get_component_class(self.code, self.version).group_icon
