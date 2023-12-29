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
from datetime import timedelta

from django.utils import timezone
from unittest.mock import patch

from apps.backend.periodic_tasks import clean_subscription_instance_record_data
from apps.node_man import models
from apps.utils.unittest.testcase import CustomBaseTestCase


class SubscriptionInstanceRecordCleanTestCase(CustomBaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_db()

    @classmethod
    def init_db(cls):
        cls.create_subscription_data()
        pipeline_ids = cls.create_subscription_task_data()
        cls.create_node_man_pipelinetree_data(pipeline_ids)
        cls.create_subscription_instance_record_data()

    @classmethod
    def create_subscription_data(cls):
        models.Subscription.objects.create(
            id=2,
            name="policy_subscription",
            object_type=models.Subscription.ObjectType.HOST,
            node_type=models.Subscription.NodeType.INSTANCE,
            from_system="blueking",
            creator="admin",
            category=models.Subscription.CategoryType.POLICY,
        )

    @classmethod
    def create_subscription_task_data(cls):
        subscription_tasks = list()

        default_clean_pipeline_id = "e785e7129bda4ab49b451ed45d93ec32"
        policy_pipeline_id = "4411e2d3958d46ce8e8268513c9c9f50"
        latest_pipeline_id = "1acf69efba324e4ca97bf90d7a93c6ec"
        config_clean_pipeline_id = "62c321effcdd4e2d85408f9eb6ad05c8"

        subscription_tasks.append(models.SubscriptionTask(
            id=1,
            subscription_id=1,
            scope={},
            actions={},
            pipeline_id=default_clean_pipeline_id,
        ))
        subscription_tasks.append(models.SubscriptionTask(
            id=2,
            subscription_id=2,
            scope={},
            actions={},
            pipeline_id=policy_pipeline_id,
        ))
        subscription_tasks.append(models.SubscriptionTask(
            id=3,
            subscription_id=3,
            scope={},
            actions={},
            pipeline_id=latest_pipeline_id,
        ))
        subscription_tasks.append(models.SubscriptionTask(
            id=4,
            subscription_id=4,
            scope={},
            actions={},
            pipeline_id=config_clean_pipeline_id,
        ))

        models.SubscriptionTask.objects.bulk_create(subscription_tasks)

        return [default_clean_pipeline_id, policy_pipeline_id, latest_pipeline_id, config_clean_pipeline_id]

    @classmethod
    def create_subscription_instance_record_data(cls):
        with patch('django.utils.timezone.now', return_value=cls.generate_dateTime_field_value(40)):
            subscription_instance_records = list()

            subscription_instance_records.append(models.SubscriptionInstanceRecord(
                id=1,
                task_id=1,
                subscription_id=1,
                instance_id="",
                instance_info={},
                steps={},
                is_latest=False,
            ))
            subscription_instance_records.append(models.SubscriptionInstanceRecord(
                id=2,
                task_id=2,
                subscription_id=2,
                instance_id="",
                instance_info={},
                steps={},
                is_latest=False,
            ))
            subscription_instance_records.append(models.SubscriptionInstanceRecord(
                id=3,
                task_id=3,
                subscription_id=3,
                instance_id="",
                instance_info={},
                steps={},
                is_latest=True,
            ))

            models.SubscriptionInstanceRecord.objects.bulk_create(subscription_instance_records)

        with patch('django.utils.timezone.now', return_value=cls.generate_dateTime_field_value(20)):
            models.SubscriptionInstanceRecord.objects.create(
                id=4,
                task_id=4,
                subscription_id=4,
                instance_id="",
                instance_info={},
                steps={},
                is_latest=False,
            )

    @classmethod
    def create_node_man_pipelinetree_data(cls, pipeline_ids):
        pipeline_trees = list()

        for pipeline_id in pipeline_ids:
            pipeline_trees.append(models.PipelineTree(
                id=pipeline_id,
                tree={},
            ))

        models.PipelineTree.objects.bulk_create(pipeline_trees)

    @classmethod
    def generate_dateTime_field_value(cls, days):
        delta = timedelta(days=days)
        now = timezone.now()
        return now - delta

    def test_sub_instance_record(self):
        self.assertEqual(models.SubscriptionTask.objects.count(), 4)
        self.assertEqual(models.SubscriptionInstanceRecord.objects.count(), 4)
        self.assertEqual(models.PipelineTree.objects.count(), 4)

        clean_subscription_instance_record_data()

        self.assertEqual(models.SubscriptionTask.objects.count(), 3)
        self.assertEqual(models.SubscriptionInstanceRecord.objects.count(), 3)
        self.assertEqual(models.PipelineTree.objects.count(), 3)

        # 手动配置
        sub_clean_map = {
            "enable_clean_subscription_data": True,
            "alive_days": 10,
            "limit": 10,
        }

        models.GlobalSettings.set_config(
            models.GlobalSettings.KeyEnum.CLEAN_SUBSCRIPTION_DATA_MAP.value,
            sub_clean_map
        )

        clean_subscription_instance_record_data()

        self.assertEqual(models.SubscriptionTask.objects.count(), 2)
        self.assertEqual(models.SubscriptionInstanceRecord.objects.count(), 2)
        self.assertEqual(models.PipelineTree.objects.count(), 2)
