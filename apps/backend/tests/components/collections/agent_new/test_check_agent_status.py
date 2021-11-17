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
from typing import List

from apps.backend.components.collections.agent_new.components import (
    CheckAgentStatusComponent,
)
from apps.node_man import constants
from apps.node_man.models import ProcessStatus
from pipeline.component_framework.test import ComponentTestCase, ExecuteAssertion

from . import utils


class CheckAgentStatusTestCase(utils.AgentServiceBaseTestCase):
    @classmethod
    def add_process_record(cls, status, multiple):
        bk_host_ids = cls.obj_factory.bk_host_ids
        proc_list = [
            ProcessStatus(bk_host_id=bk_host_id, name=ProcessStatus.GSE_AGENT_PROCESS_NAME, status=status)
            for bk_host_id in bk_host_ids
            for __ in range(multiple)
        ]
        ProcessStatus.objects.bulk_create(proc_list)

    @classmethod
    def get_default_case_name(cls) -> str:
        return "检查agent状态时无多余进程记录"

    @classmethod
    def init_db(cls):
        bk_host_ids = cls.obj_factory.bk_host_ids
        proc_list = [
            ProcessStatus(
                bk_host_id=bk_host_id, name=ProcessStatus.GSE_AGENT_PROCESS_NAME, status=constants.ProcStateType.RUNNING
            )
            for bk_host_id in bk_host_ids
        ]
        ProcessStatus.objects.bulk_create(proc_list)

    def setUp(self) -> None:
        super().setUp()
        self.init_db()

    def component_cls(self):
        return CheckAgentStatusComponent

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        return self.common_inputs["subscription_instance_ids"]

    def cases(self):
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=bool(self.fetch_succeeded_sub_inst_ids()),
                    outputs={"succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids()},
                ),
                schedule_assertion=None,
                patchers=None,
            )
        ]

    def tearDown(self) -> None:
        bk_host_ids = self.obj_factory.bk_host_ids
        ProcessStatus.objects.filter(bk_host_id__in=bk_host_ids).delete()


class WithOverageRunningTestCase(CheckAgentStatusTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.add_process_record(constants.ProcStateType.RUNNING, 10)

    @classmethod
    def get_default_case_name(cls) -> str:
        return "检查agent状态有多余RUNNING进程记录"


class WithOverageUnknownTestCase(CheckAgentStatusTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.add_process_record(constants.ProcStateType.UNKNOWN, 10)
        ProcessStatus.objects.filter(status=constants.ProcStateType.RUNNING).delete()

    @classmethod
    def get_default_case_name(cls) -> str:
        return "检查agent状态时只有UNKNOWN进程记录"

    def cases(self):
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(success=False, outputs={"succeeded_subscription_instance_ids": []}),
                schedule_assertion=None,
                patchers=None,
            )
        ]
