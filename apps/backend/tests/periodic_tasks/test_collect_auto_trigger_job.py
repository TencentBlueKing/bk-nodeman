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
from itertools import chain
from typing import Any, Dict, List

from apps.backend.periodic_tasks import collect_auto_trigger_job
from apps.mock_data import common_unit
from apps.node_man import models
from apps.utils import basic
from apps.utils.unittest.testcase import CustomBaseTestCase


class TestCollectAutoTriggerJob(CustomBaseTestCase):

    init_sub_num: int = 3
    init_sub_objs: List[models.Subscription] = []
    init_sub_task_objs: List[models.SubscriptionTask] = []
    init_auto_sub_task_objs: List[models.SubscriptionTask] = []

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # 初始化订阅
        subs_to_be_created = []
        for idx in range(cls.init_sub_num):
            subs_to_be_created.append(
                models.Subscription(
                    **basic.remove_keys_from_dict(origin_data=common_unit.subscription.POLICY_MODEL_DATA, keys=["id"])
                )
            )
        models.Subscription.objects.bulk_create(subs_to_be_created)
        cls.init_sub_objs = list(models.Subscription.objects.all())
        assert len(cls.init_sub_objs) == cls.init_sub_num

        # 创建订阅关联的主动触发任务
        sub_tasks_to_be_created = []
        for sub_obj in cls.init_sub_objs:
            sub_task_data: Dict[str, Any] = basic.remove_keys_from_dict(
                origin_data=common_unit.subscription.SUB_TASK_MODEL_DATA, keys=["id"]
            )
            sub_task_data.update({"subscription_id": sub_obj.id, "is_auto_trigger": False})
            sub_tasks_to_be_created.append(models.SubscriptionTask(**sub_task_data))
        models.SubscriptionTask.objects.bulk_create(sub_tasks_to_be_created)
        cls.init_sub_task_objs = list(models.SubscriptionTask.objects.all())

        # 创建主动触发任务关联的任务历史记录
        jobs_to_be_created = []
        for sub_task_obj in cls.init_sub_task_objs:
            job_data = basic.remove_keys_from_dict(origin_data=common_unit.job.JOB_MODEL_DATA, keys=["id"])
            job_data.update(
                {
                    "subscription_id": sub_task_obj.subscription_id,
                    "task_id_list": [sub_task_obj.id],
                    "is_auto_trigger": False,
                }
            )
            jobs_to_be_created.append(models.Job(**job_data))
        models.Job.objects.bulk_create(jobs_to_be_created)

        # 创建订阅关联的自动触发任务，这些任务待同步
        auto_sub_tasks_to_be_created = []
        for sub_obj in cls.init_sub_objs:
            auto_sub_task_data: Dict[str, Any] = basic.remove_keys_from_dict(
                origin_data=common_unit.subscription.SUB_TASK_MODEL_DATA, keys=["id"]
            )
            auto_sub_task_data.update({"subscription_id": sub_obj.id, "is_auto_trigger": True})
            auto_sub_tasks_to_be_created.append(models.SubscriptionTask(**auto_sub_task_data))
        models.SubscriptionTask.objects.bulk_create(auto_sub_tasks_to_be_created)
        cls.init_auto_sub_task_objs = list(models.SubscriptionTask.objects.filter(is_auto_trigger=True))
        assert cls.init_sub_num == len(cls.init_auto_sub_task_objs)

        cls.init_sub_ids = [sub.id for sub in cls.init_sub_objs]
        cls.init_auto_sub_task_ids = [auto_sub_task_obj.id for auto_sub_task_obj in cls.init_auto_sub_task_objs]

    @classmethod
    def create_auto_task(cls, is_ready: bool) -> models.SubscriptionTask:
        sub_obj = random.choice(cls.init_sub_objs)
        auto_sub_task_data: Dict = basic.remove_keys_from_dict(
            common_unit.subscription.SUB_TASK_MODEL_DATA, keys=["id"]
        )
        auto_sub_task_data.update({"subscription_id": sub_obj.id, "is_auto_trigger": True, "is_ready": is_ready})
        auto_sub_task_obj = models.SubscriptionTask(**auto_sub_task_data)
        auto_sub_task_obj.save()
        return auto_sub_task_obj

    def test_first_collect(self):
        """测试初次同步，此时global settings 还未保存执行端点"""

        # 同步前验证DB中无存量数据
        self.assertTrue(
            models.Job.objects.filter(subscription_id__in=self.init_sub_ids, is_auto_trigger=True).count() == 0
        )
        self.assertTrue(
            models.GlobalSettings.get_config(models.GlobalSettings.KeyEnum.LAST_SUB_TASK_ID.value, None) is None
        )
        self.assertTrue(
            models.GlobalSettings.get_config(models.GlobalSettings.KeyEnum.NOT_READY_TASK_INFO_MAP.value, None) is None
        )

        collect_result = collect_auto_trigger_job()
        # init_auto_sub_task_objs 均为正常数据，此时会执行到末尾
        auto_sub_task_ids = [auto_sub_task_obj.id for auto_sub_task_obj in self.init_auto_sub_task_objs]
        except_last_sub_task_id = max(auto_sub_task_ids)
        self.assertEqual(collect_result[models.GlobalSettings.KeyEnum.LAST_SUB_TASK_ID.value], except_last_sub_task_id)
        self.assertEqual(
            collect_result["TASK_IDS_GBY_REASON"], {"NOT_READY": [], "READY": auto_sub_task_ids, "ERROR": []}
        )
        self.assertEqual(
            models.GlobalSettings.get_config(models.GlobalSettings.KeyEnum.LAST_SUB_TASK_ID.value),
            except_last_sub_task_id,
        )
        self.assertEqual(
            models.GlobalSettings.get_config(models.GlobalSettings.KeyEnum.NOT_READY_TASK_INFO_MAP.value), {}
        )

        # 验证任务历史已同步
        auto_job_objs = models.Job.objects.filter(subscription_id__in=self.init_sub_ids, is_auto_trigger=True)
        self.assertListEqual(
            list(chain(*[auto_job.task_id_list for auto_job in auto_job_objs])),
            self.init_auto_sub_task_ids,
            is_sort=True,
        )

    def test_exist_not_ready(self):
        """测试存在未就绪task的情况"""
        self.test_first_collect()

        # 创建一个未就绪状态的sub task
        auto_sub_task_obj = self.create_auto_task(is_ready=False)

        collect_result = collect_auto_trigger_job()

        # 未就绪id记录到global settings, 指针前移
        self.assertEqual(collect_result[models.GlobalSettings.KeyEnum.LAST_SUB_TASK_ID.value], auto_sub_task_obj.id)
        self.assertEqual(
            collect_result["TASK_IDS_GBY_REASON"], {"NOT_READY": [auto_sub_task_obj.id], "READY": [], "ERROR": []}
        )
        self.assertEqual(
            models.GlobalSettings.get_config(models.GlobalSettings.KeyEnum.LAST_SUB_TASK_ID.value), auto_sub_task_obj.id
        )
        self.assertEqual(
            models.GlobalSettings.get_config(models.GlobalSettings.KeyEnum.NOT_READY_TASK_INFO_MAP.value),
            {str(auto_sub_task_obj.id): 1},
        )
        # 未就绪任务无需同步到Job
        self.assertFalse(models.Job.objects.filter(task_id_list__contains=auto_sub_task_obj.id).exists())

    def test_not_tasks_in_next_collect(self):
        """测试周期同步轮空的情况"""
        self.test_first_collect()

        collect_result = collect_auto_trigger_job()

        # 指针不变
        self.assertEqual(
            collect_result[models.GlobalSettings.KeyEnum.LAST_SUB_TASK_ID.value], max(self.init_auto_sub_task_ids)
        )
        self.assertEqual(collect_result["TASK_IDS_GBY_REASON"], {"NOT_READY": [], "READY": [], "ERROR": []})

    def test_history_not_ready(self):
        """验证无新增且历史存在not ready时，指针不回退"""

        self.test_exist_not_ready()

        # 创建一个就绪状态的sub task
        auto_sub_task_obj = self.create_auto_task(is_ready=True)

        # 第一次收集，指针前进至 auto_sub_task_obj.id
        collect_auto_trigger_job()
        # 第二次收集，not_ready task 依然存在，但此时没有新增task，预期排除not ready后，指针保持原值
        collect_auto_trigger_job()

        # 验证指针不回退
        last_sub_task_id = models.GlobalSettings.get_config(models.GlobalSettings.KeyEnum.LAST_SUB_TASK_ID.value)
        self.assertEqual(auto_sub_task_obj.id, last_sub_task_id)
