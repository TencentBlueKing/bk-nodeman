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

from apps.node_man.models import (
    GlobalSettings,
    IdentityData,
    ResourceWatchEvent,
    SubscriptionInstanceRecord,
)
from apps.node_man.periodic_tasks import clean_requests_tracker_records_periodic_task
from apps.node_man.periodic_tasks.clean_expired_info import clean_identity_data
from apps.node_man.periodic_tasks.clean_resource_watch_event import (
    clean_resource_watch_event_periodic_task,
)
from apps.node_man.periodic_tasks.clean_subscription_record_info import (
    update_subscription_instance_record,
)
from apps.node_man.tests.test_pericdic_tasks.mock_data import (
    MOCK_IDENTITY_DATA,
    MOCK_RECORD,
    MOCK_RESOURCE_WATCH_EVENT,
    MOCK_SUBSCRIPTION_INSTANCE_RECORD,
)
from apps.utils.unittest.testcase import CustomBaseTestCase
from requests_tracker.models import Record

KEY = "UPDATE_SUBSCRIPTION_INSTANCE_RECORD__LAST_ID"


class TestCleanRelatedTask(CustomBaseTestCase):
    """
    测试相关清除数据的定时任务
    """

    def test_clean_expired_info(self):
        IdentityData.objects.get_or_create(**MOCK_IDENTITY_DATA)
        clean_identity_data(None, 0, 1)
        mock_identity_data = IdentityData.objects.get(bk_host_id=MOCK_IDENTITY_DATA["bk_host_id"])

        self.assertEqual(
            [mock_identity_data.password, mock_identity_data.key, mock_identity_data.extra_data], [None, None, None]
        )

    def test_clean_requests_tracker_records(self):
        mock_record, _ = Record.objects.get_or_create(**MOCK_RECORD)
        clean_requests_tracker_records_periodic_task()
        mock_record = Record.objects.filter(uid=mock_record.uid)

        self.assertEqual(len(mock_record), 0)

    def test_clean_subscription_record_info(self):
        SubscriptionInstanceRecord.objects.get_or_create(**MOCK_SUBSCRIPTION_INSTANCE_RECORD)
        update_subscription_instance_record(None)
        mock_instance_record = SubscriptionInstanceRecord.objects.get(id=MOCK_SUBSCRIPTION_INSTANCE_RECORD["id"])
        last_sub_task_id = GlobalSettings.get_config(KEY, None)

        self.assertEqual(
            [last_sub_task_id, mock_instance_record.instance_info["host"]["password"]], [mock_instance_record.id, ""]
        )

    def test_clean_resource_watch_event(self):
        mock_resource_watch_event, _ = ResourceWatchEvent.objects.get_or_create(**MOCK_RESOURCE_WATCH_EVENT)
        clean_resource_watch_event_periodic_task()

        self.assertEqual(ResourceWatchEvent.objects.count(), 0)
