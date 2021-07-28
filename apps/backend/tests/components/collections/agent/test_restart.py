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
from mock import patch

from apps.backend.components.collections.agent import RestartComponent, RestartService
from apps.backend.tests.components.collections.agent import utils
from apps.node_man import constants, models
from pipeline.component_framework.test import (
    ComponentTestCase,
    ComponentTestMixin,
    ExecuteAssertion,
)

DESCRIPTION = "重启"

COMMON_INPUTS = utils.AgentTestObjFactory.inputs(
    attr_values={"description": DESCRIPTION, "bk_host_id": utils.BK_HOST_ID},
    # 主机信息保持和默认一致
    instance_info_attr_values={},
)

COMMON_INPUTS.update({"bk_username": utils.DEFAULT_CREATOR})

COMMON_INPUTS["host_info"]["bk_host_id"] = utils.BK_HOST_ID


class RestartTestService(RestartService):
    id = utils.JOB_TASK_PIPELINE_ID
    root_pipeline_id = utils.INSTANCE_RECORD_ROOT_PIPELINE_ID


class RestartTestComponent(RestartComponent):
    bound_service = RestartTestService


class RestartLinuxAgentSuccessTest(TestCase, ComponentTestMixin):
    JOB_MOCK_CLIENT = utils.JobMockClient(
        fast_execute_script_return=utils.JOB_INSTANCE_ID_METHOD_V2_C_RETURN,
        get_job_instance_status_return=utils.GET_JOB_INSTANCE_STATUS_V2_C_RETURN,
    )

    def setUp(self):
        utils.AgentTestObjFactory.init_db()
        # 设置，默认接入点
        default_ap = models.AccessPoint.objects.get(name="默认接入点")
        models.Host.objects.filter(bk_host_id=utils.BK_HOST_ID).update(ap_id=default_ap.id)
        self.client_v2 = patch(utils.CLIENT_V2_MOCK_PATH, self.JOB_MOCK_CLIENT)
        self.client_v2.start()

    def component_cls(self):
        return RestartTestComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试重启Linux Agent成功",
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
        self.client_v2.stop()


class RestartWindowsAgentSuccessTest(RestartLinuxAgentSuccessTest):
    def setUp(self):
        super().setUp()
        models.Host.objects.filter(bk_host_id=utils.BK_HOST_ID).update(os_type=constants.OsType.WINDOWS)

    def cases(self):
        return [
            ComponentTestCase(
                name="测试重启Windows Agent成功",
                inputs=COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(success=True, outputs={}),
                schedule_assertion=None,
                execute_call_assertion=None,
                patchers=None,
            )
        ]
