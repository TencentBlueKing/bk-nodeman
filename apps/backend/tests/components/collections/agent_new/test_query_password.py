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

import importlib

import mock

from apps.backend.components.collections.agent_new import query_password
from apps.backend.components.collections.agent_new.components import (
    QueryPasswordComponent,
)
from apps.node_man import constants, models
from pipeline.component_framework.test import ComponentTestCase, ExecuteAssertion

from . import utils


class QueryPasswordTestCase(utils.AgentServiceBaseTestCase):
    GET_PASSWORD_MOCK_PATH = "apps.node_man.handlers.password.TjjPasswordHandler.get_password"

    def component_cls(self):
        importlib.reload(query_password)
        QueryPasswordComponent.bound_service = query_password.QueryPasswordService
        return QueryPasswordComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试主机无需查询密码",
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=True,
                    outputs={"succeeded_subscription_instance_ids": self.common_inputs["subscription_instance_ids"]},
                ),
                schedule_assertion=None,
                execute_call_assertion=None,
                patchers=[],
            )
        ]


class QueryPasswordSucceededTestCase(QueryPasswordTestCase):
    def get_password(*args, **kwargs):
        return True, {"0-127.0.0.1": "passwordSuccessExample"}, {}, "success"

    def set_identity_to_query_password(self):
        models.IdentityData.objects.filter(bk_host_id__in=self.obj_factory.bk_host_ids).update(
            auth_type=constants.AuthType.TJJ_PASSWORD
        )

    def setUp(self) -> None:
        self.set_identity_to_query_password()
        mock.patch(target=self.GET_PASSWORD_MOCK_PATH, side_effect=self.get_password).start()
        super().setUp()

    def cases(self):
        return [
            ComponentTestCase(
                name="测试查询密码成功",
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=True,
                    outputs={"succeeded_subscription_instance_ids": self.common_inputs["subscription_instance_ids"]},
                ),
                schedule_assertion=None,
                execute_call_assertion=None,
                patchers=[],
            )
        ]

    def tearDown(self):
        # 状态检查
        self.assertTrue(models.IdentityData.objects.filter(retention=1, password="passwordSuccessExample").exists())


class QueryPasswordFailedTestCase(QueryPasswordTestCase):
    @classmethod
    def get_password(cls, *args, **kwargs):
        return False, {}, {}, "{'10': 'ticket is expired'}"

    def set_identity_to_query_password(self):
        models.IdentityData.objects.filter(bk_host_id__in=self.obj_factory.bk_host_ids).update(
            auth_type=constants.AuthType.TJJ_PASSWORD
        )

    def setUp(self) -> None:
        self.set_identity_to_query_password()
        mock.patch(target=self.GET_PASSWORD_MOCK_PATH, side_effect=self.get_password).start()
        super().setUp()

    def cases(self):
        return [
            ComponentTestCase(
                name="测试查询密码失败",
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=False,
                    outputs={"succeeded_subscription_instance_ids": []},
                ),
                schedule_assertion=None,
                execute_call_assertion=None,
                patchers=[],
            )
        ]
