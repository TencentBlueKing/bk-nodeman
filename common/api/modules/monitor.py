"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from django.utils.translation import gettext_lazy as _

from ..base import BaseApi, DataAPI
from ..domains import MONITOR_APIGATEWAY_ROOT


class _MonitorApi(BaseApi):
    MODULE = _("监控平台")
    SIMPLE_MODULE = "MONITOR"

    def __init__(self):
        self.get_or_create_agent_event_data_id = DataAPI(
            method="GET",
            url=MONITOR_APIGATEWAY_ROOT + "app/metadata/get_or_create_agent_event_data_id/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="获取或创建Agent事件data_id",
            api_name="get_or_create_agent_event_data_id",
        )
