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

from apps.node_man import models
from apps.node_man.periodic_tasks.sync_all_isp_to_cmdb import (
    sync_all_isp_to_cmdb_periodic_task,
)
from apps.node_man.tests.utils import MockClient, create_cloud_area


class TestSyncAllIspToCmdb(TestCase):
    @staticmethod
    def init_db():
        create_cloud_area(2)

    @patch("apps.node_man.periodic_tasks.sync_all_isp_to_cmdb.client_v2", MockClient)
    def test_sync_all_isp_to_cmdb(self):
        self.init_db()
        # 构造CMDB内置云区域ID
        models.GlobalSettings.set_config(key=models.GlobalSettings.KeyEnum.CMDB_INTERNAL_CLOUD_IDS.value, value=[1])
        models.Cloud.objects.filter(bk_cloud_id=2).update(isp="TencentCloud")
        with patch("apps.node_man.periodic_tasks.sync_all_isp_to_cmdb.client_v2.cc.update_cloud_area") as update_cloud:
            update_cloud.return_value = {"result": True}
            sync_all_isp_to_cmdb_periodic_task()
            call_args = update_cloud.call_args
            bk_cloud_vendor_scope = [str(bk_cloud_vendor) for bk_cloud_vendor in range(1, 19)]
            self.assertIn(call_args[0][0]["bk_cloud_vendor"], bk_cloud_vendor_scope)
            self.assertNotIn(1, call_args[0][0])
