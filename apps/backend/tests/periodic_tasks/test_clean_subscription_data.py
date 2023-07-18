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

import datetime
import typing
from itertools import cycle

from django.utils import timezone

from apps.backend.periodic_tasks.clean_subscription_data import clean_subscription_data
from apps.mock_data.api_mkd.job.unit import DEFAULT_JOB_INSTANCE_ID
from apps.mock_data.common_unit import subscription
from apps.node_man import constants
from apps.node_man.models import (
    GlobalSettings,
    JobSubscriptionInstanceMap,
    SubscriptionInstanceStatusDetail,
)
from apps.utils.unittest.testcase import CustomBaseTestCase


class SubscriptionCleanTestCase(CustomBaseTestCase):

    sub_detail_save_log_status = [constants.JobStatusType.SUCCESS, constants.JobStatusType.FAILED]
    job_sub_instance_clean_status = [constants.BkJobStatus.SUCCEEDED, constants.BkJobStatus.FAILED]

    def setUp(self):
        super().setUp()
        self.init_db()

    @classmethod
    def init_db(cls):
        minutes: int = 0
        # 创建不同事件跨度和不同日志级别的 SubscriptionInstanceStatusDetail
        sub_instance_detail_records: typing.List[SubscriptionInstanceStatusDetail] = []
        job_sub_instance_map_records: typing.List[JobSubscriptionInstanceMap] = []
        for minutes in [7 * 24 * 60, 50 * 24 * 60]:
            time_offset = datetime.timedelta(minutes=minutes)
            create_time = timezone.now() - time_offset
            for status in [s for s, _ in zip(cycle(cls.sub_detail_save_log_status), range(50))]:

                sub_instance_detail_record: SubscriptionInstanceStatusDetail = SubscriptionInstanceStatusDetail(
                    subscription_instance_record_id=subscription.DEFAULT_SUBSCRIPTION_ID,
                    node_id="45f9d4adc1c24e499891c69bc80172bc",
                    log="",
                    create_time=create_time,
                    status=status,
                )
                sub_instance_detail_records.append(sub_instance_detail_record)

            for status in [status for status, _ in zip(cycle(cls.job_sub_instance_clean_status), range(50))]:
                job_sub_instance_map: JobSubscriptionInstanceMap = JobSubscriptionInstanceMap(
                    subscription_instance_ids=subscription.DEFAULT_SUBSCRIPTION_ID,
                    job_instance_id=DEFAULT_JOB_INSTANCE_ID,
                    status=status,
                    node_id="45f9d4adc1c24e499891c69bc80172bc",
                )
                job_sub_instance_map_records.append(job_sub_instance_map)

        SubscriptionInstanceStatusDetail.objects.bulk_create(sub_instance_detail_records)
        JobSubscriptionInstanceMap.objects.bulk_create(job_sub_instance_map_records)

    def test_sub_clean_with_alive_day(self):
        sub_clean_map: typing.Dict[str, typing.Any] = {
            "enable_clean_subscription_data": True,
            "limit": 10,
            "alive_days": 10,
            "sub_ins_detail_save_log_status": [],
            "job_map_clean_status": self.job_sub_instance_clean_status,
        }
        GlobalSettings.set_config(GlobalSettings.KeyEnum.CLEAN_SUBSCRIPTION_DATA_MAP.value, sub_clean_map)
        clean_subscription_data()
        self.assertEqual(SubscriptionInstanceStatusDetail.objects.count(), 90)
        for _ in range(4):
            clean_subscription_data()
        self.assertEqual(SubscriptionInstanceStatusDetail.objects.count(), 50)

    def test_sub_clean_with_status(self):
        sub_clean_map: typing.Dict[str, typing.Any] = {
            "enable_clean_subscription_data": True,
            "sub_ins_detail_save_log_status": [constants.JobStatusType.SUCCESS],
            "job_map_clean_status": self.job_sub_instance_clean_status,
        }

        GlobalSettings.set_config(GlobalSettings.KeyEnum.CLEAN_SUBSCRIPTION_DATA_MAP.value, sub_clean_map)
        self.assertEqual(SubscriptionInstanceStatusDetail.objects.count(), 100)
        self.assertEqual(JobSubscriptionInstanceMap.objects.count(), 100)
        clean_subscription_data()
        self.assertEqual(SubscriptionInstanceStatusDetail.objects.count(), 75)
        # JobSubscriptionInstanceMap 没有存活时间的概念，只要状态符合就会被清理
        self.assertEqual(JobSubscriptionInstanceMap.objects.count(), 0)

    def test_sub_clean_witout_config(self):
        self.assertEqual(SubscriptionInstanceStatusDetail.objects.count(), 100)
        self.assertEqual(JobSubscriptionInstanceMap.objects.count(), 100)
        # 没有配置时，默认清理 30 天前的数据，limit 5000
        clean_subscription_data()
        self.assertEqual(SubscriptionInstanceStatusDetail.objects.count(), 75)
        # JOB 映射表没有时间概念，只要状态符合就会被清理，默认不清理，所以为 100
        self.assertEqual(JobSubscriptionInstanceMap.objects.count(), 100)
