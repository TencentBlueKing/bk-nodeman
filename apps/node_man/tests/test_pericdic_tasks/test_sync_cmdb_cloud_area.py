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

from apps.node_man.models import Cloud
from apps.node_man.periodic_tasks.sync_cmdb_cloud_area import (
    update_or_create_cloud_area,
)
from apps.utils.unittest.testcase import CustomBaseTestCase

from .mock_data import MOCK_SEARCH_CLOUD_AREA
from .utils import MockClient, modify_constant_data


class TestSyncCMDBCloudArea(CustomBaseTestCase):
    @patch("apps.node_man.periodic_tasks.sync_cmdb_cloud_area.client_v2", MockClient)
    def test_update_or_create_cloud_area(self):
        # 测试创建管控区域
        update_or_create_cloud_area(None, 0)
        self.assertEqual(Cloud.objects.count(), 1)
        # 测试更新管控区域
        with modify_constant_data([(MOCK_SEARCH_CLOUD_AREA["info"][0], {"bk_cloud_name": "test_cloud_2"})]):
            update_or_create_cloud_area(None, 0)
            self.assertEqual(Cloud.objects.all().first().bk_cloud_name, "test_cloud_2")

    @patch("apps.node_man.periodic_tasks.sync_cmdb_cloud_area.client_v2", MockClient)
    def test_delete_not_exist_cc_cloud_area(self):
        Cloud.objects.create(bk_cloud_id=9, bk_cloud_name="test_cloud_3")
        # 测试删除CC不存在的管控区域
        update_or_create_cloud_area(None, 0)
        cloud = list(Cloud.objects.filter(bk_cloud_id=9))
        self.assertEqual(len(cloud), 0)
