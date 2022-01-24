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

import time

from django.utils.translation import ugettext_lazy as _

from pipeline.core.flow import Service, StaticIntervalGenerator

from .base import AgentBaseService, AgentCommonData


class WaitService(AgentBaseService):
    name = _("等待")

    __need_schedule__ = True
    interval = StaticIntervalGenerator(5)

    def inputs_format(self):
        return [
            Service.InputItem(name="sleep_time", key="sleep_time", type="int", required=True),
        ]

    def _execute(self, data, parent_data, common_data: AgentCommonData):
        return True

    def _schedule(self, data, parent_data, callback_data=None):
        sleep_time = data.get_one_of_inputs("sleep_time", 5)
        time.sleep(sleep_time)
        self.finish_schedule()
        return True
