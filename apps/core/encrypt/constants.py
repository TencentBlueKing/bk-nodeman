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
from enum import Enum
from typing import Dict

from django.utils.translation import ugettext_lazy as _

from apps.utils.enum import EnhanceEnum


class RSAKeyType(EnhanceEnum):
    PUBLIC_KEY = "PUBLIC_KEY"
    PRIVATE_KEY = "PRIVATE_KEY"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.PUBLIC_KEY: _("公钥"), cls.PRIVATE_KEY: _("私钥")}


class InternalRSAKeyNameEnum(EnhanceEnum):
    DEFAULT = "DEFAULT"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.DEFAULT: _("默认RSA密钥")}
