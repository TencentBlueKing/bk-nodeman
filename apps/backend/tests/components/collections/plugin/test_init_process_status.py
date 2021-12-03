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
import copy
from typing import List
from unittest.mock import patch

from django.test import TestCase

from apps.backend.components.collections.plugin import InitProcessStatusComponent
from apps.backend.tests.components.collections.plugin import utils
from apps.node_man import constants as const
from apps.node_man import models
from pipeline.component_framework.test import (
    ComponentTestCase,
    ComponentTestMixin,
    ExecuteAssertion,
    ScheduleAssertion,
)


class InitProcessStatusTest(TestCase, ComponentTestMixin):
    def setUp(self):
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
        self.cmdb_client = patch(utils.CMDB_CLIENT_MOCK_PATH, utils.CmdbClient)
        self.cmdb_client.start()

    def tearDown(self):
        self.cmdb_client.stop()

    def component_cls(self):
        return InitProcessStatusComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试初始化任务状态",
                inputs=self.COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=True,
                    outputs={"succeeded_subscription_instance_ids": [self.ids["subscription_instance_record_id"]]},
                ),
                schedule_assertion=ScheduleAssertion(
                    success=True,
                    schedule_finished=True,
                    outputs={"succeeded_subscription_instance_ids": [self.ids["subscription_instance_record_id"]]},
                    callback_data=[],
                ),
                execute_call_assertion=None,
            )
        ]


class PluginMultiTestObjFactory(utils.PluginTestObjFactory):
    HOST_NUM = 3

    @classmethod
    def init_db(cls, init_subscription_param=None):
        # 先初始化父类数据
        ids = super().init_db()

        # 得到subscription和subscription_task用于构造sub_ins_record_params和host_params
        subscription_params = cls.subscription_obj(obj_attr_values=init_subscription_param)
        subscription = models.Subscription.objects.get(**subscription_params)

        subscription_task_params = cls.subscription_task_obj(obj_attr_values={"subscription_id": subscription.id})
        subscription_task = models.SubscriptionTask.objects.get(**subscription_task_params)

        # 批量创建主机测试数据
        multi_sub_ins_record_obj_params = cls.multi_subscription_instance_record_obj(
            obj_attr_values={"subscription_id": subscription.id, "task_id": subscription_task.id}
        )
        multi_sub_ins_record_obj = models.SubscriptionInstanceRecord.objects.bulk_create(
            multi_sub_ins_record_obj_params
        )

        multi_host_params = cls.multi_host_obj()
        multi_host = models.Host.objects.bulk_create(multi_host_params)

        ids.update(
            {
                "subscription_instance_record_ids": [sub.id for sub in multi_sub_ins_record_obj],
                "bk_host_ids": [host.bk_host_id for host in multi_host],
            }
        )

        return ids

    @classmethod
    def multi_subscription_instance_record_obj(cls, obj_attr_values=None, instance_info_attr_values=None):
        sub_ins_record_obj_list: List[models.SubscriptionInstanceRecord] = []

        for index in range(1, cls.HOST_NUM + 1):
            instance_info = copy.deepcopy(utils.INSTANCE_INFO)
            instance_info["bk_host_id"] = utils.BK_HOST_ID + index
            instance_info["bk_host_innerip"] = "127.0.0.{index}".format(index=index)
            # 将第一台主机修改为windows
            if index == 1:
                instance_info.update(
                    {
                        "account": "system",
                        "os_type": const.OsType.WINDOWS,
                        "bk_os_type": const.BK_OS_TYPE[const.OsType.WINDOWS],
                    }
                )

            sub_ins_record_params = copy.deepcopy(utils.SUBSCRIPTION_INSTANCE_RECORD_PARAMS)
            sub_ins_record_params["instance_info"] = {"host": instance_info}
            sub_ins_record_params["id"] = utils.SUBSCRIPTION_INSTANCE_RECORD_ID + index

            cls.replace_obj_attr_values(instance_info, instance_info_attr_values)
            if instance_info_attr_values is not None:
                sub_ins_record_params["instance_info"]["host"] = instance_info

            sub_ins_record_params["instance_id"] = utils.tools.create_node_id(
                {
                    "object_type": utils.DEFAULT_OBJ_TYPE,
                    "node_type": utils.DEFAULT_NODE_TYPE,
                    "bk_cloud_id": instance_info["bk_cloud_id"],
                    "ip": instance_info["bk_host_innerip"],
                }
            )
            cls.replace_obj_attr_values(sub_ins_record_params, obj_attr_values)
            sub_ins_record_obj_list.append(models.SubscriptionInstanceRecord(**sub_ins_record_params))

        return sub_ins_record_obj_list

    @classmethod
    def multi_host_obj(cls, obj_attr_values=None, is_obj=False):
        host_obj_list: List[models.Host] = []

        for index in range(1, cls.HOST_NUM + 1):
            host_params = copy.deepcopy(utils.HOST_PARAMS)
            host_params["bk_host_id"] = utils.BK_HOST_ID + index
            host_params["inner_ip"] = "127.0.0.{index}".format(index=index)
            # 将第一台主机修改为windows
            if index == 1:
                host_params["os_type"] = const.OsType.WINDOWS

            cls.replace_obj_attr_values(host_params, obj_attr_values)
            if not is_obj:
                host_params.pop("id", None)

            host_obj_list.append(models.Host(**host_params))

        return host_obj_list


class InitProcessMultiStatusTest(InitProcessStatusTest):
    def setUp(self):
        self.ids = PluginMultiTestObjFactory.init_db()
        self.COMMON_INPUTS = PluginMultiTestObjFactory.inputs(
            attr_values={
                "description": "description",
                "bk_host_ids": self.ids["bk_host_ids"],
                "subscription_instance_ids": self.ids["subscription_instance_record_ids"],
                "subscription_step_id": self.ids["subscription_step_id"],
            },
            # 主机信息保持和默认一致
            instance_info_attr_values={},
        )
        self.cmdb_client = patch(utils.CMDB_CLIENT_MOCK_PATH, utils.CmdbClient)
        self.cmdb_client.start()

    def cases(self):
        return [
            ComponentTestCase(
                name="测试批量初始化Windows&Linux任务状态",
                inputs=self.COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=True,
                    outputs={"succeeded_subscription_instance_ids": self.ids["subscription_instance_record_ids"][1:]},
                ),
                schedule_assertion=ScheduleAssertion(
                    success=True,
                    schedule_finished=True,
                    outputs={"succeeded_subscription_instance_ids": [self.ids["subscription_instance_record_ids"][1:]]},
                    callback_data=[],
                ),
                execute_call_assertion=None,
            )
        ]
