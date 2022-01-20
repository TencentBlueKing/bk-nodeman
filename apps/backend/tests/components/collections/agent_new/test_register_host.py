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
import random
from typing import Dict, List, Optional

import mock

from apps.backend.components.collections.agent_new.components import (
    RegisterHostComponent,
)
from apps.mock_data import api_mkd
from apps.mock_data import utils as mock_data_utils
from apps.node_man import constants, models
from pipeline.component_framework.test import ComponentTestCase, ExecuteAssertion

from . import utils


class RegisterHostTestCase(utils.AgentServiceBaseTestCase):
    CLIENT_V2_MOCK_PATHS: List[str] = [
        "apps.backend.subscription.tools.client_v2",
        "apps.backend.components.collections.agent_new.register_host.client_v2",
    ]

    search_business_result: Optional[Dict] = None
    list_cmdb_hosts_result: Optional[Dict] = None
    add_host_to_resource_result: Optional[Dict] = None
    list_hosts_without_biz_result: Optional[Dict] = None
    find_host_biz_relations_result: Optional[List[Dict]] = None
    cmdb_mock_client: Optional[api_mkd.cmdb.utils.CMDBMockClient] = None

    @classmethod
    def structure_cmdb_mock_data(cls):
        """
        构造CMDB接口返回数据
        :return:
        """
        cls.search_business_result = {
            "count": 1,
            "info": [
                {
                    "bk_biz_id": mock_data_utils.DEFAULT_BK_BIZ_ID,
                    "bk_biz_name": mock_data_utils.DEFAULT_BK_BIZ_NAME,
                    "bk_biz_maintainer": mock_data_utils.DEFAULT_USERNAME,
                }
            ],
        }
        cls.list_cmdb_hosts_result = {
            "count": len(cls.obj_factory.host_objs),
            "info": [
                {
                    "bk_host_id": host_obj.bk_host_id,
                    "bk_cloud_id": host_obj.bk_cloud_id,
                    "bk_host_innerip": host_obj.inner_ip,
                }
                for host_obj in cls.obj_factory.host_objs
            ],
        }
        cls.list_hosts_without_biz_result = {"count": 0, "info": []}
        cls.add_host_to_resource_result = {
            "success": [str(index) for index, __ in enumerate(cls.obj_factory.host_objs)]
        }
        cls.find_host_biz_relations_result = []

    @classmethod
    def adjust_test_data_in_db(cls):
        """
        调整DB中的测试数据
        :return:
        """
        models.Host.objects.filter(bk_host_id__in=cls.obj_factory.bk_host_ids).delete()
        models.IdentityData.objects.filter(bk_host_id__in=cls.obj_factory.bk_host_ids).delete()

        for sub_inst_obj in cls.obj_factory.sub_inst_record_objs:
            sub_inst_obj.instance_info["host"].pop("bk_host_id")

        models.SubscriptionInstanceRecord.objects.bulk_update(
            cls.obj_factory.sub_inst_record_objs, fields=["instance_info"]
        )

    @classmethod
    def get_default_case_name(cls) -> str:
        return "注册主机到配置平台成功"

    def init_mock_clients(self):
        self.cmdb_mock_client = api_mkd.cmdb.utils.CMDBMockClient(
            search_business_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.RETURN_VALUE.value, return_obj=self.search_business_result
            ),
            list_biz_hosts_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.RETURN_VALUE.value, return_obj=self.list_cmdb_hosts_result
            ),
            list_hosts_without_biz_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.RETURN_VALUE.value,
                return_obj=self.list_hosts_without_biz_result,
            ),
            find_host_biz_relations_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.RETURN_VALUE.value,
                return_obj=self.find_host_biz_relations_result,
            ),
            add_host_to_resource_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.RETURN_VALUE.value,
                return_obj=self.add_host_to_resource_result,
            ),
        )

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        return self.common_inputs["subscription_instance_ids"]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # 初始化DB数据后再修改
        cls.structure_cmdb_mock_data()
        cls.adjust_test_data_in_db()

    def setUp(self) -> None:
        self.init_mock_clients()
        for client_v2_mock_path in self.CLIENT_V2_MOCK_PATHS:
            mock.patch(client_v2_mock_path, self.cmdb_mock_client).start()
        super().setUp()

    def cases(self):
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=bool(self.fetch_succeeded_sub_inst_ids()),
                    outputs={"succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids()},
                ),
                schedule_assertion=None,
                execute_call_assertion=None,
            )
        ]

    def component_cls(self):
        return RegisterHostComponent

    def assert_in_teardown(self):
        bk_host_ids = self.obj_factory.bk_host_ids
        host_objs = models.Host.objects.filter(bk_host_id__in=bk_host_ids)
        identity_data_objs = models.IdentityData.objects.filter(bk_host_id__in=bk_host_ids)

        self.assertEqual(
            models.ProcessStatus.objects.filter(
                bk_host_id__in=bk_host_ids,
                name=models.ProcessStatus.GSE_AGENT_PROCESS_NAME,
                source_type=models.ProcessStatus.SourceType.DEFAULT,
            ).count(),
            len(bk_host_ids),
        )
        self.assertEqual(len(host_objs), len(bk_host_ids))
        self.assertEqual(len(identity_data_objs), len(bk_host_ids))

        host_id__identity_data_obj_map: Dict[int, models.IdentityData] = {
            identity_data_obj.bk_host_id: identity_data_obj for identity_data_obj in identity_data_objs
        }
        host_key__host_obj_map: Dict[str, models.Host] = {
            f"{host_obj.bk_cloud_id}-{host_obj.inner_ip}": host_obj for host_obj in host_objs
        }
        for sub_inst in models.SubscriptionInstanceRecord.objects.filter(id__in=self.obj_factory.sub_inst_record_ids):
            host_info = sub_inst.instance_info["host"]
            identity_data_obj = host_id__identity_data_obj_map[host_info["bk_host_id"]]
            host_obj = host_key__host_obj_map[f"{host_info['bk_cloud_id']}-{host_info['bk_host_innerip']}"]
            self.assertEqual(host_info["bk_biz_id"], host_obj.bk_biz_id)
            self.assertEqual(host_info["bk_host_id"], host_obj.bk_host_id)
            self.assertEqual(identity_data_obj.port, host_info["port"])
            self.assertEqual(identity_data_obj.auth_type, host_info["auth_type"])
            self.assertEqual(identity_data_obj.password, base64.b64decode(host_info.get("password", "")).decode())

    def assert_in_teardown__empty_db(self):
        bk_host_ids = self.obj_factory.bk_host_ids
        self.assertFalse(models.Host.objects.filter(bk_host_id__in=bk_host_ids).exists())
        self.assertFalse(models.IdentityData.objects.filter(bk_host_id__in=bk_host_ids).exists())
        self.assertFalse(
            models.ProcessStatus.objects.filter(
                bk_host_id__in=bk_host_ids,
                name=models.ProcessStatus.GSE_AGENT_PROCESS_NAME,
                source_type=models.ProcessStatus.SourceType.DEFAULT,
            ).exists()
        )

    def tearDown(self) -> None:
        self.assert_in_teardown()
        super().tearDown()


class UpdateDBTestCase(RegisterHostTestCase):
    @classmethod
    def adjust_test_data_in_db(cls):
        """
        调整DB中的测试数据
        :return:
        """

        for host_obj in cls.obj_factory.host_objs:
            host_obj.bk_biz_id = random.randint(100, 200)
            host_obj.bk_cloud_id = random.randint(100, 200)
            host_obj.inner_ip = ""
        for identity_data_obj in cls.obj_factory.identity_data_objs:
            identity_data_obj.auth_type = random.choice(constants.AUTH_TUPLE)
            identity_data_obj.port = random.randint(3306, 65535)
            identity_data_obj.password = "test"
        for sub_inst_obj in cls.obj_factory.sub_inst_record_objs:
            sub_inst_obj.instance_info["host"].pop("bk_host_id")
        models.Host.objects.bulk_update(cls.obj_factory.host_objs, fields=["bk_biz_id", "bk_cloud_id", "inner_ip"])
        models.IdentityData.objects.bulk_update(
            cls.obj_factory.identity_data_objs, fields=["auth_type", "port", "password"]
        )
        models.SubscriptionInstanceRecord.objects.bulk_update(
            cls.obj_factory.sub_inst_record_objs, fields=["instance_info"]
        )

    @classmethod
    def get_default_case_name(cls) -> str:
        return "注册主机到配置平台成功「更新DB存量数据」"


class EmptyAuthInfoTestCase(RegisterHostTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "主机登录认证信息被清空"

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        return []

    @classmethod
    def adjust_test_data_in_db(cls):
        """
        调整DB中的测试数据
        :return:
        """
        super().adjust_test_data_in_db()
        for sub_inst_obj in cls.obj_factory.sub_inst_record_objs:
            sub_inst_obj.instance_info["auth_type"] = constants.AuthType.PASSWORD
            sub_inst_obj.instance_info["host"].pop("password")
            sub_inst_obj.instance_info["host"].pop("key")
            sub_inst_obj.save()

    def assert_in_teardown(self):
        self.assert_in_teardown__empty_db()


class CannotFindInCMDB(RegisterHostTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "未在CMDB中查询到主机信息"

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        return []

    @classmethod
    def structure_cmdb_mock_data(cls):
        """
        构造CMDB接口返回数据
        :return:
        """
        super().structure_cmdb_mock_data()
        cls.list_cmdb_hosts_result = {"count": 0, "info": []}
        cls.list_hosts_without_biz_result = {"count": 0, "info": []}

    def assert_in_teardown(self):
        self.assert_in_teardown__empty_db()


class ExistInOtherBiz(RegisterHostTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "注册到其他业务下"

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        return []

    @classmethod
    def structure_cmdb_mock_data(cls):
        """
        构造CMDB接口返回数据
        :return:
        """
        super().structure_cmdb_mock_data()

        cls.list_cmdb_hosts_result, cls.list_hosts_without_biz_result = (
            cls.list_hosts_without_biz_result,
            cls.list_cmdb_hosts_result,
        )
        cls.find_host_biz_relations_result = [
            {
                "bk_biz_id": random.randint(100, 200),
                "bk_module_id": random.randint(100, 200),
                "bk_supplier_account": "0",
                "bk_host_id": host_obj.bk_host_id,
                "bk_set_id": random.randint(100, 200),
            }
            for host_obj in cls.obj_factory.host_objs
        ]

    def assert_in_teardown(self):
        self.assert_in_teardown__empty_db()
