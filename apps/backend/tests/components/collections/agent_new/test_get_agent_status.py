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
from collections import ChainMap
from typing import Any, Callable, Dict, List, Optional

import mock

from apps.backend.api.constants import POLLING_INTERVAL
from apps.backend.components.collections.agent_new import components
from apps.mock_data import api_mkd, common_unit
from apps.mock_data import utils as mock_data_utils
from apps.node_man import constants, models
from pipeline.component_framework.test import (
    ComponentTestCase,
    ExecuteAssertion,
    ScheduleAssertion,
)

from . import utils


class GetAgentStatusTestCaseMixin:
    EXPECT_STATUS = constants.ProcStateType.RUNNING
    GSE_API_MOCK_PATHS: List[str] = ["apps.backend.components.collections.agent_new.get_agent_status.GseApi"]

    host_ids_need_to_next_query: List[int] = None
    get_agent_info_func: Callable[[Dict], Dict] = None
    get_agent_status_func: Callable[[Dict], Dict] = None
    gse_api_mock_client: Optional[api_mkd.gse.utils.GseApiMockClient] = None

    @classmethod
    def setup_obj_factory(cls):
        """设置 obj_factory"""
        cls.obj_factory.init_host_num = 10

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.adjust_test_data_in_db()
        cls.structure_gse_mock_data()

    def init_mock_clients(self):
        self.gse_api_mock_client = api_mkd.gse.utils.GseApiMockClient(
            get_agent_info_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.SIDE_EFFECT.value, return_obj=self.get_agent_info_func
            ),
            get_agent_status_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.SIDE_EFFECT.value, return_obj=self.get_agent_status_func
            ),
        )

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        return self.common_inputs["subscription_instance_ids"]

    def structure_common_inputs(self) -> Dict[str, Any]:
        common_inputs = super().structure_common_inputs()
        return {**common_inputs, "expect_status": self.EXPECT_STATUS}

    def structure_common_outputs(self, polling_time: Optional[int] = None, **extra_kw) -> Dict[str, Any]:
        """
        构造原子返回数据
        :param polling_time: 轮询时间
        :param extra_kw: 额外需要添加的数据
        :return:
        """
        base_common_outputs = {
            "succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids(),
            "host_ids_need_to_query": self.obj_factory.bk_host_ids,
        }
        if polling_time is not None:
            base_common_outputs["polling_time"] = polling_time

        return dict(ChainMap(extra_kw, base_common_outputs))

    def component_cls(self):
        return components.GetAgentStatusComponent

    def setUp(self) -> None:
        self.init_mock_clients()
        for gse_api_mock_path in self.GSE_API_MOCK_PATHS:
            mock.patch(gse_api_mock_path, self.gse_api_mock_client).start()
        super().setUp()


class GetAgentStatusTestCase(GetAgentStatusTestCaseMixin, utils.AgentServiceBaseTestCase):
    @classmethod
    def structure_gse_mock_data(cls):
        """
        构造GSE接口返回数据
        :return:
        """

        cls.host_ids_need_to_next_query = random.sample(
            cls.obj_factory.bk_host_ids, k=random.randint(1, cls.obj_factory.init_host_num - 1)
        )

        host_key__host_id_map: Dict[str, int] = {}
        for host in cls.obj_factory.host_objs:
            host_key__host_id_map[f"{host.bk_cloud_id}:{host.inner_ip}"] = host.bk_host_id

        def _get_agent_status_func(_query_params):
            _get_agent_status_result = {}
            for _host in _query_params["hosts"]:
                _get_agent_status_result[f"{_host['bk_cloud_id']}:{_host['ip']}"] = {
                    "bk_agent_alive": constants.BkAgentStatus.ALIVE.value,
                    **_host,
                }
            if len(_query_params["hosts"]) != len(cls.obj_factory.host_objs):
                return _get_agent_status_result

            # 如果是第一次请求，构造部分 agent 异常状态
            for _index, _agent_status_info in enumerate(_get_agent_status_result.values()):
                bk_host_id = host_key__host_id_map[f"{_agent_status_info['bk_cloud_id']}:{_agent_status_info['ip']}"]
                if bk_host_id in cls.host_ids_need_to_next_query:
                    _agent_status_info["bk_agent_alive"] = random.choice(
                        [constants.BkAgentStatus.NOT_ALIVE.value, constants.BkAgentStatus.TERMINATED.value]
                    )

            return _get_agent_status_result

        def _get_agent_info_func(_query_params):
            _get_agent_info_result = {}
            for _host in _query_params["hosts"]:
                _get_agent_info_result[f"{_host['bk_cloud_id']}:{_host['ip']}"] = {
                    "version": f"1.0.{random.randint(1, 10)}",
                    "parent_ip": common_unit.host.DEFAULT_IP,
                    "parent_port": 48668,
                    **_host,
                }
            return _get_agent_info_result

        cls.get_agent_info_func = _get_agent_info_func
        cls.get_agent_status_func = _get_agent_status_func

    @classmethod
    def adjust_test_data_in_db(cls):

        # 抽取部分主机，用于构造关联进程
        host_ids_with_multi_agent_procs = random.sample(
            cls.obj_factory.bk_host_ids, k=random.randint(1, cls.obj_factory.init_host_num - 1)
        )
        proc_statuses_to_be_created = []
        for host_id in host_ids_with_multi_agent_procs:
            proc_num = random.randint(1, 5)
            for __ in range(proc_num):
                proc_statuses_to_be_created.append(
                    models.ProcessStatus(
                        bk_host_id=host_id,
                        name=models.ProcessStatus.GSE_AGENT_PROCESS_NAME,
                        source_type=models.ProcessStatus.SourceType.DEFAULT,
                    )
                )
        models.ProcessStatus.objects.bulk_create(proc_statuses_to_be_created)

    @classmethod
    def get_default_case_name(cls) -> str:
        return "查询Agent状态成功"

    def cases(self):
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=bool(self.fetch_succeeded_sub_inst_ids()),
                    outputs=self.structure_common_outputs(polling_time=0),
                ),
                schedule_assertion=[
                    ScheduleAssertion(
                        success=True,
                        schedule_finished=False,
                        outputs=self.structure_common_outputs(
                            polling_time=POLLING_INTERVAL, host_ids_need_to_query=self.host_ids_need_to_next_query
                        ),
                    ),
                    ScheduleAssertion(
                        success=True,
                        schedule_finished=True,
                        outputs=self.structure_common_outputs(polling_time=POLLING_INTERVAL, host_ids_need_to_query=[]),
                    ),
                ],
                execute_call_assertion=None,
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

        self.assertEqual(proc_qs.filter(status=constants.ProcStateType.RUNNING).count(), self.obj_factory.init_host_num)
        super().tearDown()


class TimeoutTestCase(GetAgentStatusTestCaseMixin, utils.AgentServiceBaseTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "查询Agent状态超时"

    @classmethod
    def structure_gse_mock_data(cls):
        """
        构造GSE接口返回数据
        :return:
        """

        cls.get_agent_info_func = lambda __: {}
        cls.get_agent_status_func = lambda __: {}

    @classmethod
    def adjust_test_data_in_db(cls):
        pass

    def setUp(self) -> None:
        super().setUp()
        mock.patch(
            "apps.backend.components.collections.agent_new.get_agent_status.POLLING_TIMEOUT",
            2 * POLLING_INTERVAL - 1,
        ).start()

    def cases(self):
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=bool(self.fetch_succeeded_sub_inst_ids()),
                    outputs=self.structure_common_outputs(polling_time=0),
                ),
                schedule_assertion=[
                    ScheduleAssertion(
                        success=True,
                        schedule_finished=False,
                        outputs=self.structure_common_outputs(polling_time=POLLING_INTERVAL),
                    ),
                    ScheduleAssertion(
                        success=False,
                        schedule_finished=True,
                        outputs=self.structure_common_outputs(
                            polling_time=POLLING_INTERVAL, succeeded_subscription_instance_ids=[]
                        ),
                    ),
                ],
                execute_call_assertion=None,
            )
        ]
