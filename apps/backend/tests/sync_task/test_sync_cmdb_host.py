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
from django.conf import settings

from apps.backend.sync_task import constants
from apps.utils.unittest.testcase import CustomAPITestCase
from apps.backend.utils.redis import REDIS_INST
from apps.exceptions import ValidationError


class SyncTaskTestCase(CustomAPITestCase):
    def setUp(self):
        self.client.common_request_data = {
            "bk_app_code": settings.APP_CODE,
            "bk_username": settings.SYSTEM_USE_API_ACCOUNT,
        }
        super().setUp()

    def test_sync_task_validation_error(self):
        invalid_task_name = "invalid_task_name"
        result = self.client.post(
            path="/backend/api/sync_task/create/",
            data={"task_name": invalid_task_name}
        )

        self.assertEqual(result["code"], ValidationError().code)

    def test_sync_cmdb_host(self):
        task_info = self.client.post(
            path="/backend/api/sync_task/create/",
            data={"task_name": "sync_cmdb_host"}
        )
        assert task_info["result"]

        task_id = task_info["data"]["task_id"]

        task_key_tpl_map = constants.SyncTaskType.get_member__cache_key_map()
        task_key_tpl = task_key_tpl_map[constants.SyncTaskType.SYNC_CMDB_HOST]
        cached_task_id = REDIS_INST.get(task_key_tpl.format(bk_biz_id="all")).decode()

        self.assertEqual(task_id, cached_task_id)

    def test_task_status(self):
        task_id = "29b7039f-14b0-45a7-aeab-b24601353d52"
        task_status = self.client.get(
            path="/backend/api/sync_task/status/",
            data={"task_id": task_id}
        )
        self.assertEqual(task_status["data"]["task_id"], task_id)
