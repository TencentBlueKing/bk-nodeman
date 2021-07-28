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

from apps.backend.components.collections.agent import (
    RegisterHostComponent,
    RegisterHostService,
)
from apps.backend.tests.components.collections.agent import utils
from apps.node_man import constants, models
from pipeline.component_framework.test import (
    ComponentTestCase,
    ComponentTestMixin,
    ExecuteAssertion,
    ScheduleAssertion,
)

SEARCH_BUSINESS_RESULT = {
    "count": 1,
    "info": [
        {
            "bk_biz_id": utils.DEFAULT_BIZ_ID_NAME["bk_biz_id"],
            "default": 0,
            "bk_biz_name": utils.DEFAULT_BIZ_ID_NAME["bk_biz_name"],
            "bk_biz_maintainer": utils.DEFAULT_CREATOR,
        }
    ],
}

LIST_BIZ_HOSTS_RESULT = {"info": [{"bk_host_id": utils.BK_HOST_ID, "bk_cloud_id": 0}]}

DESCRIPTION = "注册主机到配置平台"

COMMON_INPUTS = utils.AgentTestObjFactory.inputs(
    # bk_host_id 设置为空
    attr_values={"description": DESCRIPTION},
    # 主机信息保持和默认一致
    instance_info_attr_values={},
)


class RegisterHostTestService(RegisterHostService):
    id = utils.JOB_TASK_PIPELINE_ID
    root_pipeline_id = utils.INSTANCE_RECORD_ROOT_PIPELINE_ID


class RegisterHostTestComponent(RegisterHostComponent):
    bound_service = RegisterHostTestService


class RegisterHostSuccessTest(TestCase, ComponentTestMixin):
    CMDB_MOCK_CLIENT = None

    def setUp(self):
        utils.AgentTestObjFactory.init_db()
        self.CMDB_MOCK_CLIENT = utils.CMDBMockClient(
            add_host_to_resource_result={"count": 1},
            search_business_result=SEARCH_BUSINESS_RESULT,
            list_biz_hosts_result=LIST_BIZ_HOSTS_RESULT,
        )
        self.client_v2 = patch(utils.CLIENT_V2_MOCK_PATH, self.CMDB_MOCK_CLIENT)
        self.client_v2.start()

    def component_cls(self):
        return RegisterHostTestComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试注册主机成功",
                inputs=COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=True, outputs={"polling_time": 0, "is_register": False, "query_cc_count": 0}
                ),
                schedule_assertion=[
                    ScheduleAssertion(
                        success=True,
                        outputs={
                            "polling_time": 5,
                            "is_register": True,
                            "query_cc_count": 0,
                            "bk_host_id": utils.BK_HOST_ID,
                        },
                        callback_data=None,
                        schedule_finished=False,
                    ),
                    ScheduleAssertion(
                        success=True,
                        outputs={
                            "polling_time": 5,
                            "is_register": True,
                            "query_cc_count": 0,
                            "bk_host_id": utils.BK_HOST_ID,
                        },
                        callback_data=None,
                        schedule_finished=True,
                    ),
                ],
                execute_call_assertion=None,
                patchers=None,
            )
        ]

    def tearDown(self):
        # 安装任务，进程状态刚刚创建，状态是未安装
        self.assertTrue(
            models.ProcessStatus.objects.filter(
                bk_host_id=utils.BK_HOST_ID, status=constants.ProcStateType.NOT_INSTALLED
            ).exists()
        )

        # 检查是否在 subscription_instance_record.instance_info.host中新增bk_host_id字段
        bk_host_id = models.SubscriptionInstanceRecord.objects.get(
            pipeline_id=utils.INSTANCE_RECORD_ROOT_PIPELINE_ID
        ).instance_info["host"]["bk_host_id"]
        self.assertEqual(bk_host_id, utils.BK_HOST_ID)
        self.client_v2.stop()


class RegisterHostFailTest(TestCase, ComponentTestMixin):
    CMDB_MOCK_CLIENT = None

    def setUp(self):
        utils.AgentTestObjFactory.init_db()
        # 主机已被注册到bk_biz_id=1的业务
        self.CMDB_MOCK_CLIENT = utils.CMDBMockClient(
            add_host_to_resource_result={"count": 1},
            search_business_result=SEARCH_BUSINESS_RESULT,
            list_biz_hosts_result={"info": []},
            list_hosts_without_biz_result={"info": [{"bk_host_id": utils.BK_HOST_ID}]},
            find_host_biz_relations_result=[{"bk_biz_id": 1}],
        )
        self.client_v2 = patch(utils.CLIENT_V2_MOCK_PATH, self.CMDB_MOCK_CLIENT)
        self.polling_timeout = patch("apps.backend.components.collections.agent.POLLING_TIMEOUT", 600)

        self.client_v2.start()
        self.polling_timeout.start()

    def component_cls(self):
        return RegisterHostTestComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试注册主机失败，已被其他业务占用",
                inputs=COMMON_INPUTS,
                parent_data={},
                # 主机注册失败，output不存在bk_host_id
                execute_assertion=ExecuteAssertion(
                    success=True, outputs={"polling_time": 0, "is_register": False, "query_cc_count": 0}
                ),
                schedule_assertion=[
                    ScheduleAssertion(
                        success=True,
                        outputs={"polling_time": 5, "is_register": False, "query_cc_count": 1},
                        callback_data=None,
                        schedule_finished=False,
                    ),
                    ScheduleAssertion(
                        success=True,
                        outputs={"polling_time": 10, "is_register": False, "query_cc_count": 2},
                        callback_data=None,
                        schedule_finished=False,
                    ),
                    ScheduleAssertion(
                        success=True,
                        outputs={"polling_time": 15, "is_register": False, "query_cc_count": 3},
                        callback_data=None,
                        schedule_finished=False,
                    ),
                    ScheduleAssertion(
                        success=True,
                        outputs={"polling_time": 20, "is_register": False, "query_cc_count": 4},
                        callback_data=None,
                        schedule_finished=False,
                    ),
                    ScheduleAssertion(
                        success=False,
                        outputs={"polling_time": 20, "is_register": False, "query_cc_count": 4},
                        callback_data=None,
                        schedule_finished=True,
                    ),
                ],
                execute_call_assertion=None,
                patchers=None,
            )
        ]

    def tearDown(self):
        # 主机注册失败.
        self.assertFalse(
            models.ProcessStatus.objects.filter(
                bk_host_id=utils.BK_HOST_ID, status=constants.ProcStateType.NOT_INSTALLED
            ).exists()
        )
        self.client_v2.stop()
        self.polling_timeout.stop()
