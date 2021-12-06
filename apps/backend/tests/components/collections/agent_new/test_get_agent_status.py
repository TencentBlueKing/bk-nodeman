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
from typing import Any, Dict, List

import mock

from apps.backend.components.collections.agent_new.components import (
    GetAgentStatusComponent,
)
from apps.mock_data import api_mkd, common_unit
from apps.node_man import constants, models
from apps.node_man.models import Host
from pipeline.component_framework.test import (
    ComponentTestCase,
    ExecuteAssertion,
    ScheduleAssertion,
)

from . import utils


class GetAgentStatusTestCase(utils.AgentServiceBaseTestCase):

    GSE_V2_MOCK_PATH: str = "apps.backend.components.collections.agent_new.get_agent_status.client_v2"

    def init_mock_client(self):
        self.gse_mock_client = api_mkd.gse.unit.GseMockClient(
            get_agent_status_return=common_unit.gse.GET_AGENT_STATUS_DATA,
            get_agent_info_return=common_unit.gse.GET_AGENT_INFO_DATA,
        )

    @classmethod
    def init_db(cls):
        models.GlobalSettings.set_config(key="BATCH_SIZE", value=50)
        proc_status_list: List[Dict[str, str]] = []
        for host_id in cls.obj_factory.bk_host_ids:
            proc_status_list.append(
                {
                    "bk_host_id": host_id,
                    "name": models.ProcessStatus.GSE_AGENT_PROCESS_NAME,
                    "source_type": models.ProcessStatus.SourceType.DEFAULT,
                }
            )
        cls.obj_factory.bulk_create_model(models.ProcessStatus, proc_status_list)

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        return self.common_inputs["subscription_instance_ids"]

    def component_cls(self):
        return GetAgentStatusComponent

    def adjust_input(self):
        return {**self.common_inputs, **{"expect_status": constants.PROC_STATUS_DICT[constants.BkAgentStatus.ALIVE]}}

    def setUp(self) -> None:
        self.init_db()
        self.init_mock_client()
        mock.patch(self.GSE_V2_MOCK_PATH, self.gse_mock_client).start()
        super().setUp()

    def cases(self):
        return [
            ComponentTestCase(
                name="查询Agent状态全部为RUNNING成功",
                inputs=self.adjust_input(),
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=True, outputs={"succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids()}
                ),
                schedule_assertion=None,
                patchers=None,
            )
        ]


class GetAbnormalAgentStatusTestCase(GetAgentStatusTestCase):
    @classmethod
    def fetch_abnormal_agent_return(cls):
        get_agent_status = copy.deepcopy(common_unit.gse.GET_AGENT_STATUS_DATA)
        for __, agent_status in get_agent_status.items():
            agent_status["bk_agent_alive"] = constants.BkAgentStatus.NOT_ALIVE
        return get_agent_status

    def init_mock_client(self):
        self.gse_mock_client = api_mkd.gse.unit.GseMockClient(
            get_agent_status_return=self.fetch_abnormal_agent_return(),
            get_agent_info_return=common_unit.gse.GET_AGENT_INFO_DATA,
        )

    def fetch_outputs(self) -> Dict[str, Any]:
        return {
            "unexpected_status_agents": self.obj_factory.bk_host_ids,
            "host_id_obj_map": {host_id: Host(bk_host_id=host_id) for host_id in self.obj_factory.bk_host_ids},
            "host_id_to_inst_id_map": {
                host_id: inst_id
                for host_id in self.obj_factory.bk_host_ids
                for inst_id in self.common_inputs["subscription_instance_ids"]
            },
            "succeeded_subscription_instance_ids": self.common_inputs["subscription_instance_ids"],
        }

    def setUp(self) -> None:
        super().setUp()
        self.init_mock_client()
        mock.patch(self.GSE_V2_MOCK_PATH, self.gse_mock_client).start()

    def cases(self):
        return [
            ComponentTestCase(
                name="查询Agent状态全部非RUNNING",
                inputs=self.adjust_input(),
                parent_data={},
                execute_assertion=ExecuteAssertion(success=True, outputs=self.fetch_outputs()),
                schedule_assertion=ScheduleAssertion(
                    success=True,
                    outputs=self.fetch_outputs(),
                    schedule_finished=False,
                ),
                patchers=None,
            )
        ]
