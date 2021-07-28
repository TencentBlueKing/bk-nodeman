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
    QueryTjjPasswordComponent,
    QueryTjjPasswordService,
)
from apps.backend.tests.components.collections.agent import utils
from apps.node_man import constants, models
from pipeline.component_framework.test import (
    ComponentTestCase,
    ComponentTestMixin,
    ExecuteAssertion,
    Patcher,
)

DESCRIPTION = "查询铁将军密码"


COMMON_INPUTS = utils.AgentTestObjFactory.inputs(
    attr_values={"description": DESCRIPTION, "bk_host_id": utils.BK_HOST_ID},
    # 主机信息保持和默认一致
    instance_info_attr_values={},
)


class QueryTjjPasswordTestService(QueryTjjPasswordService):
    id = utils.JOB_TASK_PIPELINE_ID
    root_pipeline_id = utils.INSTANCE_RECORD_ROOT_PIPELINE_ID


class QueryTjjPasswordTestComponent(QueryTjjPasswordComponent):
    bound_service = QueryTjjPasswordTestService


class UsePasswordSuccessTest(TestCase, ComponentTestMixin):
    def setUp(self):
        utils.AgentTestObjFactory.init_db()

    def component_cls(self):
        return QueryTjjPasswordTestComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试无需通过铁将军查询密码",
                inputs=COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(success=True, outputs={}),
                schedule_assertion=None,
                execute_call_assertion=None,
                patchers=None,
            )
        ]

    def tearDown(self):
        # 状态查询
        self.assertTrue(models.JobTask.objects.filter(current_step__endswith=DESCRIPTION).exists())


class UseTjjPwdSuccessTest(TestCase, ComponentTestMixin):
    TJJ_GET_PASSWORD_PATH = "apps.backend.components.collections.agent.TjjHandler.get_password"
    TJJ_GET_PASSWORD_RETURN = (True, {"127.0.0.1": "fddsrgytrwsehygrt"}, {}, "success")

    def setUp(self):
        ids_combine = utils.AgentTestObjFactory.init_db()
        # 修改认证类型
        models.IdentityData.objects.filter(bk_host_id=ids_combine["bk_host_id"]).update(
            auth_type=constants.AuthType.TJJ_PASSWORD, extra_data={"oa_ticket": "oa_ticket_value"}
        )

    def component_cls(self):
        return QueryTjjPasswordTestComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试铁将军密码验证通过",
                inputs=COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(success=True, outputs={}),
                schedule_assertion=None,
                execute_call_assertion=None,
                patchers=[Patcher(target=self.TJJ_GET_PASSWORD_PATH, return_value=self.TJJ_GET_PASSWORD_RETURN)],
            )
        ]

    def tearDown(self):
        # 查询IdentityData显示是否正确
        self.assertTrue(models.IdentityData.objects.filter(retention=1, password="fddsrgytrwsehygrt").exists())
        # 状态查询
        self.assertTrue(models.JobTask.objects.filter(current_step__endswith=DESCRIPTION).exists())


class UseTjjPwdFailedTest(TestCase, ComponentTestMixin):
    TJJ_GET_PASSWORD_PATH = "apps.backend.components.collections.agent.TjjHandler.get_password"
    TJJ_GET_PASSWORD_OA_EXPIRED_RETURN = (False, {}, {}, "oa ticket expired")
    TJJ_GET_PASSWORD_FAILED_IP_RETURN = (True, {}, {"127.0.0.1": {"Message": "host not exists"}}, "host not exists")

    def setUp(self):
        ids_combine = utils.AgentTestObjFactory.init_db()
        # 修改认证类型
        models.IdentityData.objects.filter(bk_host_id=ids_combine["bk_host_id"]).update(
            auth_type=constants.AuthType.TJJ_PASSWORD, extra_data={"oa_ticket": "oa_ticket_value"}
        )

    def component_cls(self):
        return QueryTjjPasswordTestComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试铁将军OA TICKET 过期情况",
                inputs=COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(success=False, outputs={}),
                schedule_assertion=None,
                execute_call_assertion=None,
                patchers=[
                    Patcher(target=self.TJJ_GET_PASSWORD_PATH, return_value=self.TJJ_GET_PASSWORD_OA_EXPIRED_RETURN)
                ],
            ),
            ComponentTestCase(
                name="铁将军返回不可用主机情况",
                inputs=COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(success=False, outputs={}),
                schedule_assertion=None,
                execute_call_assertion=None,
                patchers=[
                    Patcher(target=self.TJJ_GET_PASSWORD_PATH, return_value=self.TJJ_GET_PASSWORD_FAILED_IP_RETURN)
                ],
            ),
        ]

    def tearDown(self):
        # 状态查询
        self.assertTrue(models.JobTask.objects.filter(current_step__endswith=DESCRIPTION).exists())
