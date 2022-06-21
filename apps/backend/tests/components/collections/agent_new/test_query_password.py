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
import base64
import importlib
import random

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

    @staticmethod
    def get_password(*args, **kwargs):
        cloud_ip_list = args[1]
        cloud_ip__pwd_map = {cloud_ip: "passwordSuccessExample" for cloud_ip in cloud_ip_list}
        return True, cloud_ip__pwd_map, {}, "success"

    @classmethod
    def setup_obj_factory(cls):
        """设置 obj_factory"""
        cls.obj_factory.init_host_num = 255

    @classmethod
    def adjust_test_data_in_db(cls):
        without_identity_data_host_ids = random.sample(
            cls.obj_factory.bk_host_ids, random.randint(10, cls.obj_factory.init_host_num)
        )
        models.IdentityData.objects.filter(bk_host_id__in=without_identity_data_host_ids).delete()

        for sub_inst in cls.obj_factory.sub_inst_record_objs:
            host_info = sub_inst.instance_info["host"]
            host_info["auth_type"] = random.choice(constants.AUTH_TUPLE)
            host_info["port"] = random.randint(3306, 65535)
            host_info["password"] = base64.b64encode(f"test-{host_info['bk_host_id']}".encode()).decode()

        models.SubscriptionInstanceRecord.objects.bulk_update(
            cls.obj_factory.sub_inst_record_objs, fields=["instance_info"]
        )

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.adjust_test_data_in_db()

    def setUp(self) -> None:
        mock.patch(target=self.GET_PASSWORD_MOCK_PATH, side_effect=self.get_password).start()
        super().setUp()

    def component_cls(self):
        importlib.reload(query_password)
        QueryPasswordComponent.bound_service = query_password.QueryPasswordService
        return QueryPasswordComponent

    def cases(self):
        return [
            ComponentTestCase(
                name=QueryPasswordComponent.name,
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

    def assert_in_teardown(self):
        identity_data_objs = models.IdentityData.objects.filter(bk_host_id__in=self.obj_factory.bk_host_ids)
        self.assertEqual(self.obj_factory.init_host_num, len(identity_data_objs))
        host_id__identity_data_objs_map = {
            identity_data_obj.bk_host_id: identity_data_obj for identity_data_obj in identity_data_objs
        }
        for sub_inst in self.obj_factory.sub_inst_record_objs:
            host_info = sub_inst.instance_info["host"]
            identity_data_obj = host_id__identity_data_objs_map.get(host_info["bk_host_id"])
            auth_type = host_info["auth_type"]
            self.assertEqual(identity_data_obj.auth_type, auth_type)
            self.assertEqual(identity_data_obj.port, host_info["port"])
            self.assertEqual(identity_data_obj.auth_type, host_info["auth_type"])
            if auth_type == constants.AuthType.TJJ_PASSWORD:
                self.assertEqual(identity_data_obj.password, "passwordSuccessExample")
            else:
                self.assertEqual(identity_data_obj.password, base64.b64decode(host_info.get("password", "")).decode())

    def tearDown(self) -> None:
        self.assert_in_teardown()
        super().tearDown()


class QueryPasswordFailedTestCase(QueryPasswordTestCase):
    @staticmethod
    def get_password(*args, **kwargs):
        return False, {}, {}, "{'10': 'ticket is expired'}"

    @classmethod
    def adjust_test_data_in_db(cls):
        super().adjust_test_data_in_db()

        # 全量更新为需要查询密码的认证类型
        for sub_inst in cls.obj_factory.sub_inst_record_objs:
            sub_inst.instance_info["host"]["auth_type"] = constants.AuthType.TJJ_PASSWORD
        models.SubscriptionInstanceRecord.objects.bulk_update(
            cls.obj_factory.sub_inst_record_objs, fields=["instance_info"]
        )
        # 密码置空
        models.IdentityData.objects.filter(bk_host_id__in=cls.obj_factory.bk_host_ids).update(password=None)

    def setUp(self) -> None:
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

    def assert_in_teardown(self):
        self.assertEqual(
            models.IdentityData.objects.filter(
                bk_host_id__in=self.obj_factory.bk_host_ids, auth_type=constants.AuthType.TJJ_PASSWORD
            ).count(),
            len(self.obj_factory.bk_host_ids),
        )
