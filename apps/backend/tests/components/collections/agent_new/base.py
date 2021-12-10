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
from abc import ABC
from collections import ChainMap
from typing import Any, Dict, List, Optional

import mock

from apps.mock_data import api_mkd
from apps.mock_data import utils as mock_data_utils
from apps.node_man import constants
from pipeline.component_framework.test import (
    ComponentTestCase,
    ExecuteAssertion,
    ScheduleAssertion,
)

from . import utils


class JobBaseTestCase(utils.AgentServiceBaseTestCase, ABC):
    """用于JobV3BaseService子类的测试基类"""

    JOB_API_MOCK_PATHS = [
        "apps.core.files.base.JobApi",
        "apps.backend.components.collections.job.JobApi",
    ]

    job_api_mock_client: Optional[api_mkd.job.utils.JobApiMockClient] = None
    get_job_instance_status_result: Optional[Dict[str, Any]] = None

    @staticmethod
    def get_job_instance_ip_log_func(query_params):
        """
        mock JobApi.get_job_instance_ip_log
        :param query_params: 请求数据
        :return:
        """
        get_job_instance_ip_log_data = copy.deepcopy(api_mkd.job.unit.GET_JOB_INSTANCE_IP_LOG_DATA)
        get_job_instance_ip_log_data.update(bk_cloud_id=query_params["bk_cloud_id"], ip=query_params["ip"])
        return get_job_instance_ip_log_data

    @classmethod
    def structure_mock_data(cls):
        """
        构造GSE接口返回数据
        :return:
        """

        step_ip_result_list = []
        step_ip_result = copy.deepcopy(api_mkd.job.unit.STEP_IP_RESULT)
        cls.get_job_instance_status_result = copy.deepcopy(api_mkd.job.unit.GET_JOB_INSTANCE_STATUS_DATA)
        for host_obj in cls.obj_factory.host_objs:
            info_to_be_updated = {
                "ip": host_obj.inner_ip,
                "bk_cloud_id": host_obj.bk_cloud_id,
                "status": constants.BkJobStatus.SUCCEEDED,
            }
            step_ip_result_list.append(dict(ChainMap(info_to_be_updated, step_ip_result)))
        cls.get_job_instance_status_result["step_instance_list"][0]["step_ip_result_list"] = step_ip_result_list

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # 初始化DB数据后再修改
        cls.structure_mock_data()

    @classmethod
    def get_default_case_name(cls) -> str:
        raise NotImplementedError()

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        return self.common_inputs["subscription_instance_ids"]

    def init_mock_clients(self):
        self.job_api_mock_client = api_mkd.job.utils.JobApiMockClient(
            get_job_instance_status_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.RETURN_VALUE.value,
                return_obj=self.get_job_instance_status_result,
            ),
            get_job_instance_ip_log_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.SIDE_EFFECT.value,
                return_obj=self.get_job_instance_ip_log_func,
            ),
        )

    def structure_common_outputs(self, polling_time: Optional[int] = None, **extra_kw) -> Dict[str, Any]:
        """
        构造原子返回数据
        :param polling_time: 轮询时间
        :param extra_kw: 额外需要添加的数据
        :return:
        """
        base_common_outputs = {"succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids()}
        if polling_time is not None:
            base_common_outputs["polling_time"] = polling_time

        return dict(ChainMap(extra_kw, base_common_outputs))

    def setUp(self) -> None:
        self.init_mock_clients()
        for gse_api_mock_path in self.JOB_API_MOCK_PATHS:
            mock.patch(gse_api_mock_path, self.job_api_mock_client).start()
        super().setUp()

    def cases(self):
        # 根据 component_cls 是否实现来跳过基类的测试
        try:
            self.component_cls()
        except NotImplementedError:
            return []
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=bool(self.fetch_succeeded_sub_inst_ids()), outputs=self.structure_common_outputs()
                ),
                schedule_assertion=[
                    ScheduleAssertion(
                        success=True, schedule_finished=True, outputs=self.structure_common_outputs(polling_time=5)
                    ),
                ],
                execute_call_assertion=None,
            )
        ]


class JobFailedBaseTestCase(JobBaseTestCase, ABC):
    @staticmethod
    def get_job_instance_ip_log_func(query_params):
        get_job_instance_ip_log_data = super().get_job_instance_ip_log_func(query_params)
        get_job_instance_ip_log_data.update(log_content="can not find agent by ip")
        return get_job_instance_ip_log_data

    @classmethod
    def structure_mock_data(cls):
        """
        构造GSE接口返回数据
        :return:
        """
        super().structure_mock_data()
        cls.get_job_instance_status_result["job_instance"]["status"] = constants.BkJobStatus.FAILED
        for step_ip_result in cls.get_job_instance_status_result["step_instance_list"][0]["step_ip_result_list"]:
            step_ip_result.update(
                status=constants.BkJobIpStatus.AGENT_ABNORMAL, error_code=constants.BkJobErrorCode.AGENT_ABNORMAL
            )

    def cases(self):
        # 根据 component_cls 是否实现来跳过基类的测试
        try:
            self.component_cls()
        except NotImplementedError:
            return []
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=bool(self.fetch_succeeded_sub_inst_ids()), outputs=self.structure_common_outputs()
                ),
                schedule_assertion=[
                    ScheduleAssertion(
                        success=False,
                        schedule_finished=True,
                        outputs=self.structure_common_outputs(polling_time=5, succeeded_subscription_instance_ids=[]),
                    ),
                ],
                execute_call_assertion=None,
            )
        ]
