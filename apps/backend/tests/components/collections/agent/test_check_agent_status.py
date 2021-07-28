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
from django.test import TestCase

from apps.backend.components.collections.agent import (
    CheckAgentStatusComponent,
    CheckAgentStatusService,
)
from apps.backend.tests.components.collections.agent import utils
from apps.node_man import constants, models
from pipeline.component_framework.test import (
    ComponentTestCase,
    ComponentTestMixin,
    ExecuteAssertion,
)

DESCRIPTION = "检查Agent状态"

COMMON_INPUTS = utils.AgentTestObjFactory.inputs(
    attr_values={"description": DESCRIPTION, "bk_host_id": utils.BK_HOST_ID},
    # 主机信息保持和默认一致
    instance_info_attr_values={},
)


class CheckAgentStatusTestService(CheckAgentStatusService):
    id = utils.JOB_TASK_PIPELINE_ID
    root_pipeline_id = utils.INSTANCE_RECORD_ROOT_PIPELINE_ID


class CheckAgentStatusTestComponent(CheckAgentStatusComponent):
    bound_service = CheckAgentStatusTestService


class CheckAgentNormalStatusTest(TestCase, ComponentTestMixin):
    def setUp(self):
        utils.AgentTestObjFactory.init_db()
        models.ProcessStatus.objects.create(
            bk_host_id=utils.BK_HOST_ID,
            name=models.ProcessStatus.GSE_AGENT_PROCESS_NAME,
            source_type=models.ProcessStatus.SourceType.DEFAULT,
            # 设置正常的Agent状态
            status=constants.ProcStateType.RUNNING,
        )

    def component_cls(self):
        return CheckAgentStatusTestComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试检查正常的Agent状态",
                inputs=COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(success=True, outputs={}),
                schedule_assertion=None,
                execute_call_assertion=None,
                patchers=None,
            )
        ]

    def tearDown(self):
        # 状态检查
        self.assertTrue(
            models.JobTask.objects.filter(bk_host_id=utils.BK_HOST_ID, current_step__endswith=DESCRIPTION).exists()
        )


class CheckAgentStatusFailTest(CheckAgentNormalStatusTest):
    def setUp(self):
        super().setUp()
        # 将主机进程更新为一个不正常的状态
        models.ProcessStatus.objects.filter(
            bk_host_id=utils.BK_HOST_ID, name=models.ProcessStatus.GSE_AGENT_PROCESS_NAME
        ).update(status=constants.ProcStateType.NOT_INSTALLED)

    def cases(self):
        return [
            ComponentTestCase(
                name="测试检查异常的Agent状态",
                inputs=COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(success=False, outputs={}),
                schedule_assertion=None,
                execute_call_assertion=None,
                patchers=None,
            )
        ]
