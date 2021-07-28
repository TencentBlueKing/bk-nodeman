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
from copy import deepcopy

from django.test import TestCase

from apps.backend.components.collections.agent import WaitComponent, WaitService
from apps.backend.tests.components.collections.agent import utils
from apps.node_man import models
from pipeline.component_framework.test import (
    ComponentTestCase,
    ComponentTestMixin,
    ExecuteAssertion,
    ScheduleAssertion,
)

DESCRIPTION = "等待"

COMMON_INPUTS = utils.AgentTestObjFactory.inputs(
    attr_values={"description": DESCRIPTION, "bk_host_id": utils.BK_HOST_ID},
    # 主机信息保持和默认一致
    instance_info_attr_values={},
)

# 设置等待时间
COMMON_INPUTS.update({"sleep_time": 1})


class WaitTestService(WaitService):
    id = utils.JOB_TASK_PIPELINE_ID
    root_pipeline_id = utils.INSTANCE_RECORD_ROOT_PIPELINE_ID


class WaitTestComponent(WaitComponent):
    bound_service = WaitTestService


class WaitSuccessTest(TestCase, ComponentTestMixin):
    INPUTS_WITHOUT_SLEEP_TIME = deepcopy(COMMON_INPUTS)

    def setUp(self):
        utils.AgentTestObjFactory.init_db()
        self.INPUTS_WITHOUT_SLEEP_TIME.pop("sleep_time", None)

    def component_cls(self):
        return WaitTestComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试带休眠参数等待成功",
                inputs=COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(success=True, outputs={}),
                schedule_assertion=[ScheduleAssertion(success=True, schedule_finished=True, outputs={})],
                execute_call_assertion=None,
                patchers=None,
            ),
            ComponentTestCase(
                name="测试没有带休眠参数等待成功:默认等待5秒",
                inputs=self.INPUTS_WITHOUT_SLEEP_TIME,
                parent_data={},
                execute_assertion=ExecuteAssertion(success=True, outputs={}),
                schedule_assertion=[ScheduleAssertion(success=True, schedule_finished=True, outputs={})],
                execute_call_assertion=None,
                patchers=None,
            ),
        ]

    def tearDown(self):
        # 状态检查
        self.assertTrue(
            models.JobTask.objects.filter(bk_host_id=utils.BK_HOST_ID, current_step__endswith=DESCRIPTION).exists()
        )
