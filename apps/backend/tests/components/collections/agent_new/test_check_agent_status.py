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
from typing import List

from apps.backend.components.collections.agent_new.components import (
    CheckAgentStatusComponent,
)
from apps.node_man import constants, models
from pipeline.component_framework.test import ComponentTestCase, ExecuteAssertion

from . import utils


class CheckAgentStatusTestCase(utils.AgentServiceBaseTestCase):

    succeeded_sub_inst_ids: List[int] = None

    @classmethod
    def adjust_test_data_in_db(cls):

        host_id__sub_inst_id_map = {
            sub_inst.instance_info["host"]["bk_host_id"]: sub_inst.id
            for sub_inst in cls.obj_factory.sub_inst_record_objs
        }

        # 抽取部分主机，用于构造关联进程
        host_ids_with_multi_agent_procs = random.sample(
            cls.obj_factory.bk_host_ids, k=random.randint(1, cls.obj_factory.init_host_num - 1)
        )
        succeeded_sub_inst_ids = set()
        proc_statuses_to_be_created = []
        for host_id in host_ids_with_multi_agent_procs:
            proc_num = random.randint(1, 5)
            for __ in range(proc_num):
                status = random.choice(constants.PROC_STATE_TUPLE)
                # 只要有正常的状态，说明该主机执行成功
                if status == constants.ProcStateType.RUNNING:
                    succeeded_sub_inst_ids.add(host_id__sub_inst_id_map[host_id])
                proc_statuses_to_be_created.append(
                    models.ProcessStatus(
                        bk_host_id=host_id,
                        name=models.ProcessStatus.GSE_AGENT_PROCESS_NAME,
                        source_type=models.ProcessStatus.SourceType.DEFAULT,
                        status=status,
                    )
                )
        models.ProcessStatus.objects.bulk_create(proc_statuses_to_be_created)
        cls.succeeded_sub_inst_ids = list(succeeded_sub_inst_ids)

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.adjust_test_data_in_db()

    @classmethod
    def get_default_case_name(cls) -> str:
        return "检查Agent状态"

    @classmethod
    def setup_obj_factory(cls):
        """设置 obj_factory"""
        cls.obj_factory.init_host_num = 100

    def component_cls(self):
        return CheckAgentStatusComponent

    def cases(self):
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=bool(self.succeeded_sub_inst_ids),
                    outputs={"succeeded_subscription_instance_ids": self.succeeded_sub_inst_ids},
                ),
                schedule_assertion=None,
                patchers=None,
            )
        ]

    def tearDown(self) -> None:
        # 验证最终进程唯一
        proc_qs = models.ProcessStatus.objects.filter(
            bk_host_id__in=self.obj_factory.bk_host_ids,
            name=models.ProcessStatus.GSE_AGENT_PROCESS_NAME,
            source_type=models.ProcessStatus.SourceType.DEFAULT,
        ).values_list("bk_host_id", flat=True)
        self.assertListEqual(list(proc_qs), self.obj_factory.bk_host_ids, is_sort=True)
        super().tearDown()
