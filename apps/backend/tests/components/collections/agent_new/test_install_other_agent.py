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
import copy
from typing import Any, Dict, List, Type

import mock

from apps.backend.api.constants import (
    INSTALL_OTHER_AGENT_POLLING_TIMEOUT,
    POLLING_INTERVAL,
)
from apps.backend.components.collections.agent_new import install_other_agent
from apps.backend.components.collections.agent_new.components import (
    InstallOtherAgentComponent,
)
from apps.backend.subscription.errors import SubscriptionTaskNotReadyError
from apps.exceptions import ApiResultError
from apps.node_man import models
from apps.node_man.handlers.job import JobHandler
from apps.node_man.tests.utils import NodeApi, gen_job_data
from pipeline.component_framework.test import (
    ComponentTestCase,
    ExecuteAssertion,
    ScheduleAssertion,
)

from . import utils


def request_multi_thread_client(func, params_list, get_data=lambda x: []):
    res = []
    for param in params_list:
        res.extend(get_data(func(**param)))
    return res


class InstallOtherAgentBaseTestCase(utils.AgentServiceBaseTestCase):
    @classmethod
    def setup_obj_factory(cls) -> None:
        """设置 obj_factory"""
        cls.obj_factory.init_host_num = 10

    @classmethod
    def get_default_case_name(cls) -> str:
        return "测试额外agent安装"

    def get_install_result(self) -> Dict[str, Any]:
        data: Dict[str, Any] = gen_job_data("INSTALL_AGENT", self.obj_factory.init_host_num)
        for i, host_info in enumerate(data["hosts"]):
            host_info.update(self.obj_factory.structure_instance_host_info_list()[i])
        job_result = JobHandler().install(
            data["hosts"],
            data["op_type"],
            data["node_type"],
            data["job_type"],
            "ticket",
            extra_params={},
            extra_config={},
        )

        return job_result

    def update_common_inputs(self) -> None:
        self.common_inputs.update(extra_agent_version="V2")

    def get_node_api_class(self) -> Type[NodeApi]:
        self.install_result = None

        class CustomNodeApi(NodeApi):
            @staticmethod
            def install(*args, **kwargs):
                if self.install_result:
                    return self.install_result

                self.install_result = self.get_install_result()
                return self.install_result

            @staticmethod
            def get_subscription_task_status(params):
                task_results = NodeApi.get_subscription_task_status(params)
                task_results["count"] = self.obj_factory.init_host_num
                task_results["list"] = [
                    copy.deepcopy(task_results["list"][0]) for _ in range(self.obj_factory.init_host_num)
                ]
                for i, task_result in enumerate(task_results["list"]):
                    task_result["instance_info"]["host"]["bk_host_id"] = self.obj_factory.bk_host_ids[i]

                return task_results

        return CustomNodeApi

    def start_patch(self):
        self.node_api: Type[NodeApi] = self.get_node_api_class()

        mock.patch("apps.node_man.handlers.job.NodeApi", self.node_api).start()
        mock.patch("apps.backend.components.collections.agent_new.install_other_agent.NodeApi", self.node_api).start()
        mock.patch(
            "apps.backend.components.collections.agent_new.install_other_agent.request_multi_thread",
            request_multi_thread_client,
        ).start()

    def adjust_data(self):
        # 设置 [-1] -> [2.0接入点] 的映射
        self.access_point_v2 = models.AccessPoint.objects.first()
        models.GlobalSettings.set_config(
            models.GlobalSettings.KeyEnum.GSE2_GRAY_AP_MAP.value,
            {
                -1: self.access_point_v2.id,
            },
        )

        # 设置InstallOtherAgentService的超时时间
        models.GlobalSettings.set_config(
            models.GlobalSettings.KeyEnum.BACKEND_SERVICE_POLLING_TIMEOUT.value,
            {install_other_agent.InstallOtherAgentService.__name__: INSTALL_OTHER_AGENT_POLLING_TIMEOUT},
        )

    def setUp(self) -> None:
        super().setUp()

        self.start_patch()
        self.adjust_data()
        self.update_common_inputs()

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        return self.common_inputs["subscription_instance_ids"]

    def component_cls(self):
        InstallOtherAgentComponent.bound_service = install_other_agent.InstallOtherAgentService
        return InstallOtherAgentComponent

    def cases(self):
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=bool(self.fetch_succeeded_sub_inst_ids()),
                    outputs={
                        "succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids(),
                        "polling_time": 0,
                        "host_count": self.obj_factory.init_host_num,
                        "job_result": self.node_api.install(),
                    },
                ),
                schedule_assertion=ScheduleAssertion(
                    success=True,
                    schedule_finished=True,
                    outputs={
                        "succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids(),
                        "polling_time": 0,
                        "host_count": self.obj_factory.init_host_num,
                        "job_result": self.node_api.install(),
                    },
                ),
                execute_call_assertion=None,
                patchers=[],
            )
        ]


class TestCaseWithScheduleTwice(InstallOtherAgentBaseTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "测试额外agent安装(前两次返回SubscriptionTaskNotReadyError，进入下一次轮询，后面正常返回)"

    def get_node_api_class(self):
        self.task_status__call_count = 0
        node_api_class = super().get_node_api_class()

        class CustomNodeApi(node_api_class):
            @staticmethod
            def get_subscription_task_status(params):
                if self.task_status__call_count <= 1:
                    # 前两次调用返回异常，进入下一次轮询
                    self.task_status__call_count += 1
                    raise ApiResultError(code=SubscriptionTaskNotReadyError().code)
                else:
                    # 后面正常调用
                    return node_api_class.get_subscription_task_status(params)

        return CustomNodeApi

    def cases(self):
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=bool(self.fetch_succeeded_sub_inst_ids()),
                    outputs={
                        "succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids(),
                        "polling_time": 0,
                        "host_count": self.obj_factory.init_host_num,
                        "job_result": self.node_api.install(),
                    },
                ),
                schedule_assertion=[
                    # 第一次轮询，返回SubscriptionTaskNotReadyError
                    # 1. 此时 polling_time 为 上一次的polling_time + POLLING_INTERVAL
                    # 2. schedule_finished 为False
                    ScheduleAssertion(
                        success=True,
                        schedule_finished=False,
                        outputs={
                            "succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids(),
                            "polling_time": POLLING_INTERVAL,
                            "host_count": self.obj_factory.init_host_num,
                            "job_result": self.node_api.install(),
                        },
                    ),
                    # 第二次轮询，返回SubscriptionTaskNotReadyError
                    # 1. 此时 polling_time 为 上一次的polling_time + POLLING_INTERVAL
                    # 2. schedule_finished 为False
                    ScheduleAssertion(
                        success=True,
                        schedule_finished=False,
                        outputs={
                            "succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids(),
                            "polling_time": POLLING_INTERVAL * 2,
                            "host_count": self.obj_factory.init_host_num,
                            "job_result": self.node_api.install(),
                        },
                    ),
                    # 第三次轮询，正常返回数据
                    # 1. 此时 polling_time 为 上一次的polling_time
                    # 2. schedule_finished 为True
                    ScheduleAssertion(
                        success=True,
                        schedule_finished=True,
                        outputs={
                            "succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids(),
                            "polling_time": POLLING_INTERVAL * 2,
                            "host_count": self.obj_factory.init_host_num,
                            "job_result": self.node_api.install(),
                        },
                    ),
                ],
                execute_call_assertion=None,
                patchers=[],
            )
        ]


class TestCaseWithTimeout(InstallOtherAgentBaseTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "测试额外agent安装(超时)"

    def get_node_api_class(self):
        node_api_class = super().get_node_api_class()

        class CustomNodeApi(node_api_class):
            @staticmethod
            def get_subscription_task_status(params):
                raise ApiResultError(code=SubscriptionTaskNotReadyError().code)

        return CustomNodeApi

    def cases(self):
        # 疯狂轮询，叠加POLLING_INTERVAL
        # 每一次轮询都叠加 POLLING_INTERVAL, 所以到达 INSTALL_OTHER_AGENT_POLLING_TIMEOUT 需要次数为
        # INSTALL_OTHER_AGENT_POLLING_TIMEOUT // POLLING_INTERVAL
        schedule_assertions = [
            ScheduleAssertion(
                success=True,
                schedule_finished=False,
                outputs={
                    "succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids(),
                    "polling_time": POLLING_INTERVAL * (i + 1),
                    "host_count": self.obj_factory.init_host_num,
                    "job_result": self.node_api.install(),
                },
            )
            for i in range(INSTALL_OTHER_AGENT_POLLING_TIMEOUT // POLLING_INTERVAL)
        ]

        # 解释最后一次schedule
        # 此时的 polling_time 应该大于 INSTALL_OTHER_AGENT_POLLING_TIMEOUT ,
        # 值为 INSTALL_OTHER_AGENT_POLLING_TIMEOUT + POLLING_INTERVAL ,
        # 此时所有实例都被移到失败实例中，可以推导出 succeeded_subscription_instance_ids 为 []
        # 因为 succeeded_subscription_instance_ids 为 [], 可以推导出 success 为 False
        # 因为是最后一次调度, 此时的 schedule_finished 为 True
        schedule_assertions.append(
            ScheduleAssertion(
                success=False,
                schedule_finished=True,
                outputs={
                    "succeeded_subscription_instance_ids": [],
                    "polling_time": INSTALL_OTHER_AGENT_POLLING_TIMEOUT + POLLING_INTERVAL,
                    "host_count": self.obj_factory.init_host_num,
                    "job_result": self.node_api.install(),
                },
            )
        )
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=bool(self.fetch_succeeded_sub_inst_ids()),
                    outputs={
                        "succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids(),
                        "polling_time": 0,
                        "host_count": self.obj_factory.init_host_num,
                        "job_result": self.node_api.install(),
                    },
                ),
                schedule_assertion=schedule_assertions,
                execute_call_assertion=None,
                patchers=[],
            )
        ]
