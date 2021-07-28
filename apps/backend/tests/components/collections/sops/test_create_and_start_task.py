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
import random

from django.test import TestCase

from apps.backend.components.collections.sops import CreateAndStartTaskComponent
from apps.backend.tests.components.collections.sops.utils import (
    SOPS_BIZ,
    SOPS_HOST_PARAMS,
    SOPS_USERNAME,
    TASK_ID,
    SopsMockClient,
    SopsParamFactory,
)
from pipeline.component_framework.test import (
    ComponentTestCase,
    ComponentTestMixin,
    ExecuteAssertion,
    Patcher,
    ScheduleAssertion,
)


class CheckAgentNormalStatusTest(TestCase, ComponentTestMixin):
    COMMON_INPUTS = {
        "sops_client": {
            "bk_biz_id": SOPS_BIZ,
            "username": SOPS_USERNAME,
        },
        "template_id": random.randint(1, 100),
        "name": "test",
        "host_info": SOPS_HOST_PARAMS,
    }

    def setUp(self):
        SopsParamFactory.init_db()

    def component_cls(self):
        return CreateAndStartTaskComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试创建并开始任务",
                inputs=self.COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(success=True, outputs={"polling_time": 0, "task_id": TASK_ID}),
                patchers=[Patcher(target="apps.backend.api.sops.get_client_by_user", side_effect=SopsMockClient)],
                schedule_assertion=ScheduleAssertion(
                    success=True,
                    schedule_finished=True,
                    outputs={"task_id": TASK_ID, "polling_time": 0},
                    callback_data=[],
                ),
                execute_call_assertion=None,
            )
        ]
