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
import json

from apps.backend import constants
from apps.backend.periodic_tasks.schedule_running_subscription_task import (
    clean_deleted_subscription,
    schedule_run_subscription,
    schedule_update_subscription,
)
from apps.backend.subscription.handler import SubscriptionHandler
from apps.backend.tests.components.collections.plugin import utils
from apps.backend.utils.redis import REDIS_INST
from apps.node_man import constants as node_man_constants
from apps.node_man import models
from apps.utils.unittest.testcase import CustomBaseTestCase


class CreatePreData(CustomBaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.init_db()

    def init_db(self):
        self.ids = utils.PluginTestObjFactory.init_db()
        self.COMMON_INPUTS = utils.PluginTestObjFactory.inputs(
            attr_values={
                "description": "description",
                "bk_host_id": utils.BK_HOST_ID,
                "subscription_instance_ids": [self.ids["subscription_instance_record_id"]],
                "subscription_step_id": self.ids["subscription_step_id"],
            },
            # 主机信息保持和默认一致
            instance_info_attr_values={},
        )


class TestScheduleRunningSubscriptionTask(CreatePreData):
    def setUp(self) -> None:
        super().setUp()
        models.SubscriptionInstanceRecord.objects.filter(id=self.ids["subscription_instance_record_id"]).update(
            status="RUNNING"
        )
        SubscriptionHandler(self.ids["subscription_id"]).run()

    def test_schedule_running_subscription_task(self):
        name: str = constants.RUN_SUBSCRIPTION_REDIS_KEY_TPL
        length: int = min(REDIS_INST.llen(name), constants.MAX_RUN_SUBSCRIPTION_TASK_COUNT)
        run_params = REDIS_INST.lrange(name, -length, -1)
        self.assertEqual(
            json.loads(run_params[0].decode()),
            {"subscription_id": self.ids["subscription_id"], "scope": None, "actions": None},
        )
        # 模拟之前的订阅任务跑完，调度订阅任务执行
        models.SubscriptionInstanceRecord.objects.filter(id=self.ids["subscription_instance_record_id"]).update(
            status="SUCCESS"
        )
        # 执行订阅后会创建一个订阅任务
        schedule_run_subscription()
        num = models.SubscriptionTask.objects.filter(subscription_id=self.ids["subscription_id"]).count()
        self.assertEqual(num, 2)


class TestScheduleUpdateSubscriptionTask(CreatePreData):
    def setUp(self) -> None:
        super().setUp()
        scope = {
            "bk_biz_id": 1,
            "node_type": "HOST",
            "nodes": [{"ip": None, "bk_host_id": 79}],
            "need_register": False,
            "instance_selector": None,
        }
        steps = [
            {
                "id": 1,
                "type": "PLUGIN",
                "config": {"plugin_name": "test_plugin", "plugin_version": "1.0.0"},
                "params": {},
            }
        ]
        self.params = {
            "subscription_id": self.ids["subscription_id"],
            "scope": scope,
            "steps": steps,
            "operate_info": [],
            "bk_biz_scope": [],
            "run_immediately": True,
        }
        models.SubscriptionInstanceRecord.objects.filter(id=self.ids["subscription_instance_record_id"]).update(
            status="RUNNING"
        )
        SubscriptionHandler.update_subscription(params=self.params)

    def test_schedule_update_subscription_task(self):
        name: str = constants.UPDATE_SUBSCRIPTION_REDIS_KEY_TPL

        update_params = REDIS_INST.hgetall(name=name)
        for update_param in update_params.values():
            self.assertEqual(json.loads(update_param.decode()), self.params)
        models.SubscriptionInstanceRecord.objects.filter(
            id=self.ids["subscription_instance_record_id"], subscription_id=self.ids["subscription_id"]
        ).update(status="SUCCESS")
        schedule_update_subscription()
        num = models.SubscriptionTask.objects.filter(subscription_id=self.ids["subscription_id"]).count()
        self.assertEqual(num, 2)


class TestCleanDeletedSubscriptionTask(CreatePreData):
    def setUp(self) -> None:
        super().setUp()
        models.Subscription.objects.filter(id=self.ids["subscription_id"]).update(from_system="bkmonitorv3")
        models.Subscription.objects.filter(id=self.ids["subscription_id"]).delete()
        models.SubscriptionInstanceRecord.objects.filter(subscription_id=self.ids["subscription_id"]).update(
            status=node_man_constants.StatusType.FAILED
        )

    def test_clean_subscription_task(self):
        # 调度清理任务，将nodes设置为空列表，并且启用订阅巡检
        clean_deleted_subscription()
        subscription = models.Subscription.objects.get(id=self.ids["subscription_id"])
        self.assertEqual(subscription.nodes, [])
        self.assertEqual(subscription.enable, True)
        self.assertEqual(subscription.is_deleted, False)
