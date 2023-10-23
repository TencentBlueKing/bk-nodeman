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

from apps.utils.enum import EnhanceEnum


class BkPaaSVersion(EnhanceEnum):
    V2 = 2
    V3 = 3

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.V2: "V2", cls.V3: "V3具备容器及二进制配置差异"}


class LogType(EnhanceEnum):
    STDOUT = "STDOUT"
    DEFAULT = "DEFAULT"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.DEFAULT: "与开发框架保持一致", cls.STDOUT: "标准输出"}


class GseVersion(EnhanceEnum):
    V1 = "V1"
    V2 = "V2"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.V1: "V1", cls.V2: "V2"}


class BkCryptoType(EnhanceEnum):

    SHANGMI = "SHANGMI"
    CLASSIC = "CLASSIC"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.SHANGMI: "国密算法", cls.CLASSIC: "国密算法"}


class CacheBackend(EnhanceEnum):
    DB = "db"
    REDIS = "redis"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.DB: "MySQL", cls.REDIS: "Redis（如果 Redis 未配置，使用 MySQL）"}
