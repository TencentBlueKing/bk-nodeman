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
from unittest.mock import patch

from django.test import TestCase

from apps.backend.components.collections.plugin import (
    GseOperateProcComponent,
    GseOperateProcService,
)
from apps.backend.tests.components.collections.plugin import utils
from apps.node_man import constants, models
from pipeline.component_framework.test import (
    ComponentTestCase,
    ComponentTestMixin,
    ExecuteAssertion,
    ScheduleAssertion,
)


class GseOperateProcTest(TestCase, ComponentTestMixin):
    def setUp(self):
        self.ids = utils.PluginTestObjFactory.init_db()
        self.COMMON_INPUTS = utils.PluginTestObjFactory.inputs(
            attr_values={
                "description": "description",
                "bk_host_id": utils.BK_HOST_ID,
                "subscription_instance_ids": [self.ids["subscription_instance_record_id"]],
                "subscription_step_id": self.ids["subscription_step_id"],
            },
            # 主机信息保持和默认一致
            instance_info_attr_values={},
        )

        self.cmdb_client = patch(utils.CMDB_CLIENT_MOCK_PATH, utils.CmdbClient)
        self.plugin_client = patch(utils.PLUGIN_CLIENT_MOCK_PATH, utils.JobMockClient)
        self.plugin_multi_thread = patch(utils.PLUGIN_MULTI_THREAD_PATH, utils.request_multi_thread_client)
        self.job_jobapi = patch(utils.JOB_JOBAPI, utils.JobMockClient)
        self.job_multi_thread = patch(utils.JOB_MULTI_THREAD_PATH, utils.request_multi_thread_client)
        self.plugin_gseapi = patch(utils.PLUGIN_GSEAPI, utils.GseMockClient)

        self.plugin_gseapi.start()
        self.cmdb_client.start()
        self.plugin_client.start()
        self.plugin_multi_thread.start()
        self.job_jobapi.start()
        self.job_multi_thread.start()

    def tearDown(self):
        self.cmdb_client.stop()
        self.plugin_client.stop()
        self.plugin_multi_thread.stop()
        self.job_jobapi.stop()
        self.job_multi_thread.stop()
        self.plugin_gseapi.stop()

    def component_cls(self):
        return GseOperateProcComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试gse操作进程",
                inputs=self.COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=True,
                    outputs={"task_id": 10000, "polling_time": 0, "succeeded_subscription_instance_ids": [95]},
                ),
                schedule_assertion=ScheduleAssertion(
                    success=True,
                    schedule_finished=True,
                    outputs={
                        "succeeded_subscription_instance_ids": [self.ids["subscription_instance_record_id"]],
                        "polling_time": 5,
                        "task_id": utils.JOB_INSTANCE_ID,
                    },
                    callback_data=[],
                ),
                execute_call_assertion=None,
            )
        ]


class TestGseOperateResourcePolicy(TestCase):
    PLUGIN_NAME = "bkmonitorbeat"
    CPU_LIMIT = 20
    MEM_LIMIT = 30

    def init_service_template_resource_policy(self):
        models.PluginResourcePolicy.objects.create(
            plugin_name=self.PLUGIN_NAME,
            cpu=self.CPU_LIMIT,
            mem=self.MEM_LIMIT,
            bk_biz_id=utils.DEFAULT_BIZ_ID_NAME["bk_biz_id"],
            bk_obj_id=constants.CmdbObjectId.SERVICE_TEMPLATE,
            bk_inst_id=utils.SERVICE_TEMPLATE_ID,
        )

    def setUp(self):
        self.ids = utils.PluginTestObjFactory.init_db()
        self.init_service_template_resource_policy()
        self.cmdb_client = patch(utils.CMDB_CLIENT_MOCK_PATH, utils.CmdbClient)
        self.cmdb_client.start()

    def test_get_resource_policy(self):
        resource_policy = GseOperateProcService.get_resource_policy({utils.BK_HOST_ID}, self.PLUGIN_NAME)
        self.assertDictEqual(resource_policy[utils.BK_HOST_ID]["resource"], {"cpu": 20, "mem": 30})

    def test_get_resource_policy_by_non_set_host_id(self):
        # 未配置资源配额，预期拿到默认值
        non_set_host_id = 123456789
        resource_policy = GseOperateProcService.get_resource_policy({non_set_host_id}, self.PLUGIN_NAME)
        self.assertDictEqual(
            resource_policy[non_set_host_id]["resource"],
            {"cpu": constants.PLUGIN_DEFAULT_CPU_LIMIT, "mem": constants.PLUGIN_DEFAULT_MEM_LIMIT},
        )

    def test_get_resource_policy_cmdb_component_error(self):
        # 接口不存在时，则直接使用默认值
        bk_host_id_set = {1, 2}
        resource_policy = GseOperateProcService.get_resource_policy(bk_host_id_set, self.PLUGIN_NAME)
        for bk_host_id in bk_host_id_set:
            self.assertDictEqual(
                resource_policy[bk_host_id]["resource"],
                {"cpu": constants.PLUGIN_DEFAULT_CPU_LIMIT, "mem": constants.PLUGIN_DEFAULT_MEM_LIMIT},
            )

    def tearDown(self):
        self.cmdb_client.stop()
