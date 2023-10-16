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
import importlib
from typing import Callable, List, Optional
from unittest.mock import Mock

import mock

from apps.backend.api.constants import POLLING_INTERVAL
from apps.backend.components.collections.agent_new import push_host_identifier
from apps.backend.components.collections.agent_new.components import (
    PushIdentifierHostsComponent,
)
from apps.mock_data import api_mkd
from apps.mock_data import utils as mock_data_utils
from apps.mock_data.api_mkd.cmdb.unit import CMDB_PUSH_IDENTIFIER_DATA
from pipeline.component_framework.test import (
    ComponentTestCase,
    ExecuteAssertion,
    ScheduleAssertion,
)

from . import utils


class PushIdentifierHostsTestCase(utils.AgentServiceBaseTestCase):
    CC_API_MOCK_PATHS: List[str] = ["apps.backend.components.collections.agent_new.push_host_identifier.CCApi"]

    cc_api_mock_client: Optional[api_mkd.cmdb.utils.CCApiMockClient] = None

    MOCK_HOST_NUMBER = 300

    BATCH_HOST_LIMIT = 200

    mock_task_id_side_effect: Callable = None

    @classmethod
    def push_identifier_task_result_func(cls, query_params):
        return {"task_id": cls.mock_task_id_side_effect()}

    @classmethod
    def get_default_case_name(cls) -> str:
        return "推送主机身份成功"

    @classmethod
    def find_push_host_identifier_result(cls, bk_host_ids):
        return {"success_list": bk_host_ids, "failed_list": [], "pending_list": []}

    @classmethod
    def get_task_ids_by_host_number(cls, host_number: int):
        host_lists = cls.get_host_lists_by_host_number(host_number)

        if getattr(cls, "task_list", None):
            task_list = getattr(cls, "task_list")
        else:
            task_list = [
                "{CMDB_PUSH_IDENTIFIER_DATA}-{x}".format(CMDB_PUSH_IDENTIFIER_DATA=CMDB_PUSH_IDENTIFIER_DATA, x=x)
                for x in range(1, len(host_lists) + 1)
            ]
            setattr(cls, "task_list", task_list)
        return task_list

    @classmethod
    def get_host_lists_by_host_number(cls, host_number: int):
        return [
            [x for x in range(1, host_number + 1)][i : i + cls.BATCH_HOST_LIMIT]
            for i in range(0, host_number, cls.BATCH_HOST_LIMIT)
        ]

    def init_mock_clients(self):
        self.cc_api_mock_client = api_mkd.cmdb.utils.CCApiMockClient(
            push_host_identifier_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.SIDE_EFFECT.value,
                return_obj=self.push_identifier_task_result_func,
            ),
            find_host_identifier_push_result_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.RETURN_VALUE.value,
                return_obj=self.find_push_host_identifier_result(bk_host_ids=self.obj_factory.bk_host_ids),
            ),
        )

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        return self.common_inputs["subscription_instance_ids"]

    @classmethod
    def setup_obj_factory(cls):
        """设置 obj_factory"""
        cls.obj_factory.init_host_num = cls.MOCK_HOST_NUMBER

    def setUp(self) -> None:
        self.init_mock_clients()
        super().setUp()

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.mock_task_id_side_effect = Mock()
        cls.mock_task_id_side_effect.side_effect = cls.get_task_ids_by_host_number(cls.MOCK_HOST_NUMBER)

    def cases(self):
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=True,
                    outputs={
                        "push_identifier_task_ids": self.get_task_ids_by_host_number(self.MOCK_HOST_NUMBER),
                        "succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids(),
                        "polling_time": 0,
                    },
                ),
                schedule_assertion=ScheduleAssertion(
                    success=True,
                    schedule_finished=True,
                    outputs={
                        "push_identifier_task_ids": self.get_task_ids_by_host_number(self.MOCK_HOST_NUMBER),
                        "succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids(),
                        "polling_time": 0,
                    },
                ),
                execute_call_assertion=None,
            )
        ]

    def component_cls(self):
        importlib.reload(push_host_identifier)
        PushIdentifierHostsComponent.bound_service = push_host_identifier.PushIdentifierHostsService
        for cc_api_mock_path in self.CC_API_MOCK_PATHS:
            mock.patch(cc_api_mock_path, self.cc_api_mock_client).start()

        return PushIdentifierHostsComponent


class PushIdentifierFailedTestCase(PushIdentifierHostsTestCase):

    MOCK_HOST_NUMBER = 200

    @classmethod
    def get_default_case_name(cls) -> str:
        return "推送主机身份失败"

    @classmethod
    def find_push_host_identifier_result(cls, bk_host_ids):
        return {"success_list": [], "failed_list": bk_host_ids, "pending_list": []}

    def cases(self):
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=True,
                    outputs={
                        "push_identifier_task_ids": self.get_task_ids_by_host_number(self.MOCK_HOST_NUMBER),
                        "succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids(),
                        "polling_time": 0,
                    },
                ),
                schedule_assertion=ScheduleAssertion(
                    success=False,
                    schedule_finished=False,
                    outputs={
                        "push_identifier_task_ids": self.get_task_ids_by_host_number(self.MOCK_HOST_NUMBER),
                        "succeeded_subscription_instance_ids": [],
                        "polling_time": POLLING_INTERVAL,
                        "total_failed_push_host_ids": self.obj_factory.bk_host_ids,
                    },
                ),
                execute_call_assertion=None,
            )
        ]


class PushIdentifierPendingTestCase(PushIdentifierHostsTestCase):

    MOCK_HOST_NUMBER = 300

    @classmethod
    def get_default_case_name(cls) -> str:
        return "推送主机身份等待失败"

    def setUp(self) -> None:
        super().setUp()
        mock.patch(
            "apps.backend.components.collections.base.PollingTimeoutMixin.service_polling_timeout",
            2 * POLLING_INTERVAL - 1,
        ).start()

    @classmethod
    def find_push_host_identifier_result(cls, bk_host_ids):
        return {"success_list": [], "failed_list": [], "pending_list": bk_host_ids}

    def cases(self):
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=True,
                    outputs={
                        "push_identifier_task_ids": self.get_task_ids_by_host_number(self.MOCK_HOST_NUMBER),
                        "succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids(),
                        "polling_time": 0,
                    },
                ),
                schedule_assertion=[
                    ScheduleAssertion(
                        success=True,
                        schedule_finished=False,
                        outputs={
                            "push_identifier_task_ids": self.get_task_ids_by_host_number(self.MOCK_HOST_NUMBER),
                            "succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids(),
                            "total_failed_push_host_ids": [],
                            "polling_time": POLLING_INTERVAL,
                        },
                    ),
                    ScheduleAssertion(
                        success=False,
                        schedule_finished=True,
                        outputs={
                            "push_identifier_task_ids": self.get_task_ids_by_host_number(self.MOCK_HOST_NUMBER),
                            "succeeded_subscription_instance_ids": [],
                            "polling_time": POLLING_INTERVAL,
                            "total_failed_push_host_ids": [],
                        },
                    ),
                ],
                execute_call_assertion=None,
            )
        ]
