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

from typing import List

from apps.backend.components.collections.agent_new.components import (
    UpdateProcessStatusComponent,
)
from apps.node_man import constants
from apps.node_man.models import GlobalSettings, Host, ProcessStatus
from pipeline.component_framework.test import ComponentTestCase, ExecuteAssertion

from . import utils


class UpdateProcessStatusTestCase(utils.AgentServiceBaseTestCase):

    batch_size: int = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.batch_size = GlobalSettings.get_config("BATCH_SIZE", default=100)

    @classmethod
    def adjust_test_data_in_db(cls, node_from):
        bk_host_ids = cls.obj_factory.bk_host_ids
        adjust_host_list = [Host(bk_host_id=bk_host_id, node_from=node_from) for bk_host_id in bk_host_ids]
        Host.objects.bulk_update(adjust_host_list, ["node_from"], batch_size=cls.batch_size)

    @classmethod
    def get_default_case_name(cls) -> str:
        return "更新来源为CMDB的主机进程记录"

    @classmethod
    def add_process_record(cls, multiple):
        bk_host_ids = cls.obj_factory.bk_host_ids
        proc_list = [
            ProcessStatus(
                bk_host_id=bk_host_id, name=ProcessStatus.GSE_AGENT_PROCESS_NAME, status=constants.ProcStateType.RUNNING
            )
            for bk_host_id in bk_host_ids
            for __ in range(multiple)
        ]
        ProcessStatus.objects.bulk_create(proc_list)

    def setUp(self) -> None:
        super().setUp()
        self.init_db()
        self.add_process_record(5)
        self.adjust_test_data_in_db(node_from=constants.NodeFrom.CMDB)

    def init_db(self) -> None:
        proc_list: List[ProcessStatus] = []

        for host_id in self.obj_factory.bk_host_ids:
            proc_list.append(
                ProcessStatus(
                    bk_host_id=host_id,
                    name=ProcessStatus.GSE_AGENT_PROCESS_NAME,
                    status=constants.ProcStateType.RUNNING,
                    source_type=ProcessStatus.SourceType.DEFAULT,
                )
            )

        ProcessStatus.objects.bulk_create(proc_list)

    def component_cls(self):
        return UpdateProcessStatusComponent

    def adjust_input(self):
        return {**self.common_inputs, "status": constants.ProcStateType.NOT_INSTALLED}

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        return self.common_inputs["subscription_instance_ids"]

    def cases(self):
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.adjust_input(),
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=True, outputs={"succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids()}
                ),
                schedule_assertion=None,
                patchers=None,
            )
        ]

    def tearDown(self) -> None:
        cmdb_source_host_queryset = Host.objects.filter(
            node_from=constants.NodeFrom.CMDB, bk_host_id__in=self.obj_factory.bk_host_ids
        )
        proc_status_queryset = ProcessStatus.objects.filter(
            bk_host_id__in=self.obj_factory.bk_host_ids,
            name=ProcessStatus.GSE_AGENT_PROCESS_NAME,
            source_type=ProcessStatus.SourceType.DEFAULT,
            status=constants.ProcStateType.NOT_INSTALLED,
        )
        self.assertTrue(cmdb_source_host_queryset)
        self.assertTrue(proc_status_queryset)


class UpdateNodeManProcessTestCase(UpdateProcessStatusTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.adjust_test_data_in_db(node_from=constants.NodeFrom.NODE_MAN)

    @classmethod
    def get_default_case_name(cls) -> str:
        return "更新来源为NODE_MAN的主机进程记录"

    def tearDown(self) -> None:
        node_man_source_host_queryset = Host.objects.filter(
            node_from=constants.NodeFrom.NODE_MAN, bk_host_id__in=self.obj_factory.bk_host_ids
        )
        proc_status_queryset = ProcessStatus.objects.filter(
            bk_host_id__in=self.obj_factory.bk_host_ids,
            name=ProcessStatus.GSE_AGENT_PROCESS_NAME,
            source_type=ProcessStatus.SourceType.DEFAULT,
            status=constants.ProcStateType.NOT_INSTALLED,
        )
        self.assertFalse(node_man_source_host_queryset)
        self.assertTrue(proc_status_queryset)
