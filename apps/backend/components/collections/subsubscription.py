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
import abc
import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from apps.backend.api.constants import POLLING_INTERVAL, POLLING_TIMEOUT
from apps.backend.components.collections.base import BaseService, CommonData
from apps.backend.subscription import errors
from apps.node_man import constants
from apps.utils.batch_request import request_multi_thread
from common.api import NodeApi
from pipeline.core.flow import Service, StaticIntervalGenerator

logger = logging.getLogger("app")


class SubSubscriptionBaseService(BaseService, metaclass=abc.ABCMeta):
    """
    子订阅
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(POLLING_INTERVAL)

    def outputs_format(self):
        return super().outputs_format() + [
            Service.InputItem(name="subscription_ids", key="subscription_ids", type="list", required=True),
            Service.InputItem(name="polling_time", key="polling_time", type="int", required=True),
        ]

    @staticmethod
    def create_subscriptions(common_data: CommonData) -> List[int]:
        raise NotImplementedError()

    @staticmethod
    def check_subscription_task_result(subscription_ids: List[int]) -> List[List[Dict]]:
        params_list = [
            {
                "params": {
                    "subscription_id": subscription_id,
                }
            }
            for subscription_id in subscription_ids
        ]
        task_results = request_multi_thread(NodeApi.get_subscription_task_status, params_list, get_data=lambda x: [x])
        return task_results

    @staticmethod
    def extract_failed_reason_from_steps(steps: List[Dict]) -> str:
        failed_reasons = []
        for step in steps:
            if step["status"] != constants.JobStatusType.FAILED:
                continue
            node_name = step.get("node_name")
            for host in step["target_hosts"]:
                for sub_step in host["sub_steps"]:
                    if sub_step["status"] != constants.JobStatusType.FAILED:
                        continue
                    sub_step_node_name = sub_step.get("node_name")
                    failed_reasons.append(
                        "{node_name}-{sub_step_node_name} 失败".format(
                            node_name=node_name, sub_step_node_name=sub_step_node_name
                        )
                    )
        return ", ".join(failed_reasons)

    def handle_task_results(self, task_results_list: List[List[Dict]]) -> Tuple[bool, Dict[int, str]]:
        is_finished = True
        failed_host_reason_map: Dict[int, Optional[List, str]] = defaultdict(list)
        for task_results in task_results_list:
            for task_result in task_results:
                bk_host_id = task_result["instance_info"]["host"]["bk_host_id"]
                if task_result["status"] in [constants.JobStatusType.PENDING, constants.JobStatusType.RUNNING]:
                    is_finished = False
                    failed_host_reason_map[bk_host_id].append(
                        "{node_name} 执行超时".format(node_name=task_result["steps"][0]["node_name"])
                    )
                if task_result["status"] == constants.JobStatusType.FAILED:
                    failed_reason = self.extract_failed_reason_from_steps(task_result["steps"])
                    failed_host_reason_map[bk_host_id].append(failed_reason)
                    continue
        for bk_host_id, failed_reasons in failed_host_reason_map.items():
            failed_host_reason_map[bk_host_id] = ", ".join(failed_reasons)
        return is_finished, failed_host_reason_map

    def handle_failed_reasons(self, data, failed_host_reason_map: Dict[int, str]):
        # 处理个别执行失败的任务并标记失败状态
        common_data = self.get_common_data(data)
        failed_reason__sub_inst_ids_map = defaultdict(list)
        for bk_host_id, failed_reason in failed_host_reason_map.items():
            sub_inst_id = common_data.host_id__sub_inst_id_map.get(bk_host_id, 0)
            failed_reason__sub_inst_ids_map[failed_reason].append(sub_inst_id)
        for failed_reason, sub_inst_ids in failed_reason__sub_inst_ids_map.items():
            self.move_insts_to_failed(sub_inst_ids=sub_inst_ids, log_content=failed_reason)

    def _execute(self, data, parent_data, common_data: CommonData):
        data.outputs.subscription_ids = self.create_subscriptions(common_data)

    def _schedule(self, data, parent_data, callback_data=None):
        polling_time = data.get_one_of_outputs("polling_time") or 0
        next_polling_time = polling_time + POLLING_INTERVAL
        subscription_ids = data.get_one_of_outputs("subscription_ids")
        try:
            task_results = self.check_subscription_task_result(subscription_ids)
        except errors.SubscriptionTaskNotReadyError:
            # 任务未就绪，等待下一次轮询
            data.outputs.polling_time = next_polling_time
            return True

        is_finished, failed_host_reason_map = self.handle_task_results(task_results)
        if is_finished:
            self.handle_failed_reasons(data, failed_host_reason_map)
            self.finish_schedule()
            return True
        elif next_polling_time > POLLING_TIMEOUT:
            # 任务执行超时
            self.handle_failed_reasons(data, failed_host_reason_map)
            self.finish_schedule()
            return False
        data.outputs.polling_time = next_polling_time
