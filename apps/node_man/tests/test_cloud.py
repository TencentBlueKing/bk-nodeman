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
import random
from unittest.mock import patch

from django.test import TestCase

from apps.exceptions import ValidationError
from apps.node_man.exceptions import CloudNotExistError, CloudUpdateHostError
from apps.node_man.handlers.cloud import CloudHandler
from apps.node_man.models import IdentityData
from apps.node_man.tests.utils import DIGITS, MockClient, create_cloud_area, create_host


class TestCloud(TestCase):
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    @patch("apps.node_man.handlers.cloud.get_request_username", return_value="admin")
    def test_cloud_list(self, *args, **kwargs):
        # 创建云区域1000个
        number = 1000
        bk_cloud_ids = create_cloud_area(number)

        # 测试过期代理和异常代理
        create_host(number=1, node_type="PROXY", bk_host_id=1, proc_type="UNKNOWN", bk_cloud_id=2)
        create_host(number=1, node_type="PROXY", bk_host_id=2, bk_cloud_id=3)
        identity = IdentityData.objects.get(bk_host_id=2)
        identity.password = None
        identity.key = None
        identity.save()

        # 测试携带云区域
        clouds = CloudHandler().list({"with_default_area": True})
        self.assertEqual(len(clouds), len(bk_cloud_ids) + 1)
        # 测试查询，不包括云区域
        clouds = CloudHandler().list({"with_default_area": False})
        self.assertEqual(len(clouds), len(bk_cloud_ids))

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_cloud_retrieve(self):
        # 创建云区域1000个
        number = 1000
        bk_cloud_ids = create_cloud_area(number)

        # 测试云区域不存在
        self.assertRaises(CloudNotExistError, CloudHandler().retrieve, 998989898)

        # 测试查询接口
        for bk_cloud_id in bk_cloud_ids:
            cloud = CloudHandler().retrieve(bk_cloud_id)
            self.assertEqual(bk_cloud_id, cloud["bk_cloud_id"])

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_cloud_create(self):
        # 测试正常创建
        CloudHandler().create(
            {
                "isp": ["腾讯云", "阿里云", "AWS"][random.randint(0, 2)],
                "ap_id": -1,
                "bk_cloud_name": "".join(random.choice(DIGITS) for x in range(8)),
                "is_visible": 1,
                "is_deleted": 0,
            },
            "admin",
        )

        # 测试重复名字创建
        kwarg = {
            "isp": ["腾讯云", "阿里云", "AWS"][random.randint(0, 2)],
            "ap_id": -1,
            "bk_cloud_name": "ck_test",
            "is_visible": 1,
            "is_deleted": 0,
        }
        CloudHandler().create(kwarg, "admin")
        self.assertRaises(ValidationError, CloudHandler().create, kwarg, "admin")

        # 测试直连区域报错
        kwarg = {
            "isp": ["腾讯云", "阿里云", "AWS"][random.randint(0, 2)],
            "ap_id": -1,
            "bk_cloud_name": "直连区域",
            "is_visible": 1,
            "is_deleted": 0,
        }
        self.assertRaises(ValidationError, CloudHandler().create, kwarg, "admin")

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_cloud_update(self):
        kwarg = {
            "isp": ["腾讯云", "阿里云", "AWS"][random.randint(0, 2)],
            "ap_id": -1,
            "bk_cloud_name": "".join(random.choice(DIGITS) for x in range(8)),
            "is_visible": 1,
            "is_deleted": 0,
        }
        cloud = CloudHandler().create(kwarg, "admin")

        # 测试更新
        bk_cloud_id = cloud["bk_cloud_id"]
        kwarg["ap_id"] = 1
        kwarg["bk_cloud_name"] = "cktest"
        CloudHandler().update(bk_cloud_id, kwarg["bk_cloud_name"], kwarg["isp"], kwarg["ap_id"])

        # 测试重复名字
        CloudHandler().create(
            {
                "isp": ["腾讯云", "阿里云", "AWS"][random.randint(0, 2)],
                "ap_id": -1,
                "bk_cloud_name": "ck_test",
                "is_visible": 1,
                "is_deleted": 0,
            },
            "admin",
        )

        kwarg["bk_cloud_name"] = "ck_test"
        self.assertRaises(
            ValidationError, CloudHandler().update, bk_cloud_id, kwarg["bk_cloud_name"], kwarg["isp"], kwarg["ap_id"]
        )

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_cloud_destroy(self):
        # 正常创建
        cloud = CloudHandler().create(
            {
                "isp": ["腾讯云", "阿里云", "AWS"][random.randint(0, 2)],
                "ap_id": -1,
                "bk_cloud_name": "".join(random.choice(DIGITS) for x in range(8)),
                "is_visible": 1,
                "is_deleted": 0,
            },
            "admin",
        )
        bk_cloud_id = cloud["bk_cloud_id"]
        CloudHandler().destroy(bk_cloud_id)

        # 测试【删除的云区域下已有主机】的校验
        cloud = CloudHandler().create(
            {
                "isp": ["腾讯云", "阿里云", "AWS"][random.randint(0, 2)],
                "ap_id": -1,
                "bk_cloud_name": "".join(random.choice(DIGITS) for x in range(8)),
                "is_visible": 1,
                "is_deleted": 0,
            },
            "admin",
        )
        bk_cloud_id = cloud["bk_cloud_id"]
        create_host(1, bk_cloud_id=bk_cloud_id)
        self.assertRaises(CloudUpdateHostError, CloudHandler().destroy, bk_cloud_id)

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_list_cloud_info(self):
        number = 1000
        bk_cloud_ids = create_cloud_area(number)
        cloud_info = CloudHandler().list_cloud_info(bk_cloud_ids)
        # 减去默认云区域
        self.assertEqual(len(bk_cloud_ids), len(cloud_info) - 1)

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    @patch("apps.node_man.handlers.cloud.get_request_username", return_value="admin")
    def test_list_cloud_name(self, *args, **kwargs):
        CloudHandler().create(
            {
                "isp": ["腾讯云", "阿里云", "AWS"][random.randint(0, 2)],
                "ap_id": -1,
                "bk_cloud_name": "".join(random.choice(DIGITS) for x in range(8)),
                "is_visible": 1,
                "is_deleted": 0,
            },
            "admin",
        )

        cloud_info = CloudHandler().list_cloud_name()
        self.assertEqual(len(cloud_info), 1)
