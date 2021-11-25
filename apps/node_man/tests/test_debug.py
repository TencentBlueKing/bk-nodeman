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
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase

from apps.node_man import models
from apps.node_man.handlers.debug import DebugHandler
from apps.node_man.tests.utils import NodeApi, create_host


class TestDebug(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Django testcase 创建测试类的钩子，仅在testcase创建时执行一次
        # save() 会缓存自增id值到obj，防止id写死导致其他testcase的同model创建断言异常

        cls.subscription_obj = models.Subscription(
            nodes=[{"bk_host_id": 1}, {"bk_host_id": 2}],
        )
        cls.subscription_obj.save()

        cls.subscription_task_obj = models.SubscriptionTask(
            subscription_id=cls.subscription_obj.id,
            scope={
                "object_type": "HOST",
                "node_type": "TOPO",
                "nodes": [
                    {"bk_biz_id": 1, "bk_inst_id": 100, "bk_obj_id": "set"},
                    {"bk_biz_id": 2, "bk_inst_id": 10, "bk_obj_id": "module"},
                ],
            },
            actions={},
        )
        cls.subscription_task_obj.save()

        cls.sub_inst_record_obj = models.SubscriptionInstanceRecord(
            task_id=cls.subscription_task_obj.id,
            subscription_id=cls.subscription_obj.id,
            instance_id="host|instance|host|1",
            is_latest=True,
        )
        cls.sub_inst_record_obj.save()

        host_to_create, _, _ = create_host(number=100)

        super().setUpTestData()

    @patch("common.api.NodeApi.get_subscription_task_detail", NodeApi.get_subscription_task_detail)
    def test_get_log(self):
        result = DebugHandler.get_log(
            subscription_id=self.subscription_obj.id, instance_id=self.sub_inst_record_obj.instance_id
        )
        for index, content in result.items():
            self.assertRegex(index, r"\d+_\d+")
            self.assertEqual(
                content, [{"step": "1", "status": "SUCCESS", "log": "1", "start_time": None, "finish_time": None}]
            )

    @patch("common.api.NodeApi.get_subscription_task_detail", NodeApi.get_subscription_task_detail)
    def test_task_detail(self):
        result = DebugHandler().task_details(
            subscription_id=self.subscription_obj.id, task_id=self.subscription_task_obj.id
        )
        self.assertEqual(result[0]["subscription_id"], self.subscription_obj.id)
        self.assertEqual(result[0]["task_id"], self.subscription_task_obj.id)
        for index, content in result[0]["logs"].items():
            self.assertRegex(index, r"\d+_\d+")
            self.assertEqual(
                content, [{"step": "1", "status": "SUCCESS", "log": "1", "start_time": None, "finish_time": None}]
            )

    def test_subscription_details(self):
        result = DebugHandler().subscription_details(subscription_id=self.subscription_obj.id)
        self.assertEqual(result[0]["task_id"], self.subscription_task_obj.id)
        self.assertEqual(
            result[0]["details"],
            f"{settings.BK_NODEMAN_HOST}/api/debug/fetch_task_details?"
            f"subscription_id={self.subscription_obj.id}&task_id={self.subscription_task_obj.id}",
        )

    def test_fetch_hosts_by_subscription(self):
        result = DebugHandler().fetch_hosts_by_subscription(subscription_id=self.subscription_obj.id)
        self.assertEqual(result["total"], 2)

    def test_fetch_subscriptions_by_host(self):
        result = DebugHandler().fetch_subscriptions_by_host(bk_host_id=1)
        self.assertEqual(
            result,
            [
                {
                    "subscription_id": self.subscription_obj.id,
                    "subscription_detail": f"{settings.BK_NODEMAN_HOST}/api/debug/fetch_subscription_details?"
                    f"subscription_id={self.subscription_obj.id}",
                }
            ],
        )
