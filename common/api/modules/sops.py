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

from ..base import BaseApi, DataAPI
from ..domains import SOPS_APIGATEWAY_ROOT


class _SopsApi(BaseApi):
    MODULE = _("标准运维")

    def __init__(self):
        self.create_task = DataAPI(
            method="POST",
            url=SOPS_APIGATEWAY_ROOT + "create_task/",
            module=self.MODULE,
            description="创建任务",
        )
        self.start_task = DataAPI(
            method="POST",
            url=SOPS_APIGATEWAY_ROOT + "start_task/",
            module=self.MODULE,
            description="启动任务",
        )
        self.get_task_status = DataAPI(
            method="POST",
            url=SOPS_APIGATEWAY_ROOT + "get_task_status/",
            module=self.MODULE,
            description="查询任务状态",
        )
