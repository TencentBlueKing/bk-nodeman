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
from typing import Any, Dict

from django.utils.translation import ugettext_lazy as _

from apps.core.concurrent import core_concurrent_constants
from apps.node_man import models
from apps.utils import enum


class ServiceCCConfigName(enum.EnhanceEnum):

    SSH = "SERVICE_SSH"
    WMIEXE = "SERVICE_WMIEXE"
    JOB_CMD = "SERVICE_JOB_CMD"
    QUERY_PASSWORD = "QUERY_PASSWORD"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {
            cls.SSH: _("使用 ssh 会话执行命令"),
            cls.WMIEXE: _("使用 wmiexe 会话执行命令"),
            cls.JOB_CMD: _("使用 job 执行命令"),
            cls.QUERY_PASSWORD: _("查询密码"),
        }


def get_config_dict(config_name: str) -> Dict[str, Any]:
    current_controller_settings = models.GlobalSettings.get_config(
        key=models.GlobalSettings.KeyEnum.CONCURRENT_CONTROLLER_SETTINGS.value, default={}
    )
    return current_controller_settings.get(config_name, core_concurrent_constants.DEFAULT_CONCURRENT_CONTROL_CONFIG)
