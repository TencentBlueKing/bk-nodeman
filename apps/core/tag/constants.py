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
from enum import Enum
from typing import Dict

from django.utils.translation import ugettext_lazy as _

from apps.utils.enum import EnhanceEnum


class TargetType(EnhanceEnum):
    """目标类型"""

    PLUGIN = "PLUGIN"
    AGENT = "AGENT"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.PLUGIN: _("插件"), cls.AGENT: _("Agent")}


class TagChangeAction(EnhanceEnum):
    DELETE = "DELETE"
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    OVERWRITE = "OVERWRITE"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.DELETE: _("删除标签"), cls.CREATE: _("新建标签"), cls.UPDATE: _("更新版本"), cls.OVERWRITE: _("同版本覆盖更新")}
