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
from typing import Any, Dict, List, Type

import mock
from django.test import override_settings

from apps.mock_data import utils as mock_data_utils
from apps.node_man import models
from apps.node_man.tests.utils import CcApi, NodeApi
from apps.utils.unittest import testcase

from .. import handlers
from .utils import GrayTestObjFactory


class GrayHandlerTestCase(testcase.CustomBaseTestCase):

    OBJ_FACTORY_CLASS: Type[GrayTestObjFactory] = GrayTestObjFactory
    TEST_IP: str = "0.0.0.1"
    TEST_CLOUD_IP: str = f"0:{TEST_IP}"

    def setUp(self) -> None:
        mock.patch("apps.node_man.handlers.job.NodeApi", NodeApi).start()
        mock.patch("apps.core.ipchooser.query.resource.CCApi", CcApi).start()

    @classmethod
    def setUpClass(cls):
        cls.obj_factory = cls.OBJ_FACTORY_CLASS()
        super().setUpClass()

    @classmethod
    def setUpTestData(cls):
        cls.obj_factory.init_db()

    @override_settings(BK_BACKEND_CONFIG=True)
    def test_biz_gray_build(self):
        validated_data: Dict[str, List[Any]] = {"bk_biz_ids": [mock_data_utils.DEFAULT_BK_BIZ_ID]}
        handlers.GrayHandler.build(validated_data=validated_data)
        # 断言主机已灰度为2.0接入点
        self.assertTrue(models.Host.objects.get(inner_ip=self.TEST_IP).ap_id == self.OBJ_FACTORY_CLASS.GSE_V2_AP_ID)
        self.assertTrue(
            models.Host.objects.get(inner_ip=self.TEST_IP).gse_v1_ap_id == self.OBJ_FACTORY_CLASS.GSE_V1_AP_ID
        )
        # 断言业务已写入灰度列表
        self.assertTrue(mock_data_utils.DEFAULT_BK_BIZ_ID in handlers.GrayTools.get_or_create_gse2_gray_scope_list())

    @override_settings(BK_BACKEND_CONFIG=True)
    def test_cloud_ips_gray_build(self):
        validated_data: Dict[str, List[Any]] = {
            "bk_biz_ids": [mock_data_utils.DEFAULT_BK_BIZ_ID],
            "cloud_ips": [self.TEST_CLOUD_IP],
        }
        handlers.GrayHandler.build(validated_data=validated_data)
        # 断言主机已灰度为2.0接入点
        self.assertTrue(models.Host.objects.get(inner_ip=self.TEST_IP).ap_id == self.OBJ_FACTORY_CLASS.GSE_V2_AP_ID)
        self.assertTrue(
            models.Host.objects.get(inner_ip=self.TEST_IP).gse_v1_ap_id == self.OBJ_FACTORY_CLASS.GSE_V1_AP_ID
        )
        # 断言业务未写入灰度列表
        self.assertTrue(
            mock_data_utils.DEFAULT_BK_BIZ_ID not in handlers.GrayTools.get_or_create_gse2_gray_scope_list()
        )

    @override_settings(BK_BACKEND_CONFIG=True)
    def test_biz_gray_rollback(self):
        self.OBJ_FACTORY_CLASS.structure_biz_gray_data()
        validated_data: Dict[str, List[Any]] = {"bk_biz_ids": [mock_data_utils.DEFAULT_BK_BIZ_ID]}
        handlers.GrayHandler.rollback(validated_data=validated_data)
        # 断言主机已灰度为1.0接入点
        self.assertTrue(models.Host.objects.get(inner_ip=self.TEST_IP).ap_id == self.OBJ_FACTORY_CLASS.GSE_V1_AP_ID)
        self.assertTrue(models.Host.objects.get(inner_ip=self.TEST_IP).gse_v1_ap_id is None)
        # 断言业务未写入灰度列表
        self.assertTrue(
            mock_data_utils.DEFAULT_BK_BIZ_ID not in handlers.GrayTools.get_or_create_gse2_gray_scope_list()
        )

    @override_settings(BK_BACKEND_CONFIG=True)
    def test_cloud_ips_rollback(self):
        self.OBJ_FACTORY_CLASS.structure_biz_gray_data()
        validated_data: Dict[str, List[Any]] = {
            "bk_biz_ids": [mock_data_utils.DEFAULT_BK_BIZ_ID],
            "cloud_ips": [self.TEST_CLOUD_IP],
        }
        handlers.GrayHandler.rollback(validated_data=validated_data)
        # 断言主机已灰度为1.0接入点
        self.assertTrue(models.Host.objects.get(inner_ip=self.TEST_IP).ap_id == self.OBJ_FACTORY_CLASS.GSE_V1_AP_ID)
        self.assertTrue(models.Host.objects.get(inner_ip=self.TEST_IP).gse_v1_ap_id is None)
        # 断言业务未写入灰度列表
        self.assertTrue(
            mock_data_utils.DEFAULT_BK_BIZ_ID not in handlers.GrayTools.get_or_create_gse2_gray_scope_list()
        )

    def upgrade_to_agent_id_checker(self, validated_data: Dict[str, List[Any]]):
        result: Dict[str, List[List[str]]] = handlers.GrayHandler.generate_upgrade_to_agent_id_request_params(
            validated_data=validated_data
        )
        # 断言no_bk_agent_id_hosts列表
        self.assertTrue(result["no_bk_agent_id_hosts"][0] == self.TEST_CLOUD_IP)

        models.Host.objects.update(bk_agent_id="test_agent_id")
        # 断言success列表
        result: Dict[str, List[List[str]]] = handlers.GrayHandler.generate_upgrade_to_agent_id_request_params(
            validated_data=validated_data
        )
        self.assertTrue(result["request_hosts"][0]["bk_agent_id"] == "test_agent_id")

    def rollback_agent_id_checker(self, validated_data: Dict[str, List[Any]]):
        result: Dict[str, List[List[str]]] = handlers.GrayHandler.generate_upgrade_to_agent_id_request_params(
            validated_data=validated_data, rollback=True
        )
        self.assertTrue(result["request_hosts"][0]["bk_agent_id"] == self.TEST_CLOUD_IP)

    def test_biz_upgrade_to_agent_id(self):
        self.OBJ_FACTORY_CLASS.structure_biz_gray_data()
        validated_data: Dict[str, List[Any]] = {"bk_biz_ids": [mock_data_utils.DEFAULT_BK_BIZ_ID]}
        self.upgrade_to_agent_id_checker(validated_data=validated_data)

    def test_cloud_ip_upgrade_to_agent_id(self):
        self.OBJ_FACTORY_CLASS.structure_biz_gray_data()
        validated_data: Dict[str, List[Any]] = {
            "bk_biz_ids": [mock_data_utils.DEFAULT_BK_BIZ_ID],
            "cloud_ips": [self.TEST_CLOUD_IP],
        }
        self.upgrade_to_agent_id_checker(validated_data=validated_data)

    def test_biz_rollback_agent_id(self):
        self.OBJ_FACTORY_CLASS.structure_biz_gray_data()
        validated_data: Dict[str, List[Any]] = {
            "bk_biz_ids": [mock_data_utils.DEFAULT_BK_BIZ_ID],
        }
        self.rollback_agent_id_checker(validated_data=validated_data)

    def test_cloud_ip_rollback_agent_id(self):
        self.OBJ_FACTORY_CLASS.structure_biz_gray_data()
        validated_data: Dict[str, List[Any]] = {
            "bk_biz_ids": [mock_data_utils.DEFAULT_BK_BIZ_ID],
            "cloud_ips": [self.TEST_CLOUD_IP],
        }
        self.rollback_agent_id_checker(validated_data=validated_data)
