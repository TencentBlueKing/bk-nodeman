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
from typing import Any, Dict, List, Optional, Tuple

from django.utils.translation import ugettext as _

from apps.backend.api.constants import (
    POLLING_INTERVAL,
    SUB_SUBSCRIPTION_POLLING_TIMEOUT,
)
from apps.backend.components.collections.base import BaseService, CommonData
from apps.exceptions import ApiResultError
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
    def check_subscription_task_ready(subscription_id: int) -> Dict[str, Any]:
        try:
            sub_task_is_ready: bool = NodeApi.check_subscription_task_ready({"subscription_id": subscription_id})
            return {"subscription_id": subscription_id, "is_ready": sub_task_is_ready, "is_error": False}
        except ApiResultError as err:
            # 异常视为订阅任务创建失败
            return {"subscription_id": subscription_id, "is_ready": True, "is_error": True, "err_msg": err}

    @classmethod
    def bulk_check_subscription_task_ready(cls, subscription_ids: List[int]) -> List[Dict[str, Any]]:
        params_list = [{"subscription_id": subscription_id} for subscription_id in subscription_ids]
        task_ready_infos = request_multi_thread(cls.check_subscription_task_ready, params_list, get_data=lambda x: [x])
        return task_ready_infos

    @staticmethod
    def bulk_get_subscription_task_status(subscription_ids: List[int]) -> List[List[Dict]]:
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
                        _("{node_name}-{sub_step_node_name} 失败").format(
                            node_name=node_name, sub_step_node_name=sub_step_node_name
                        )
                    )
        return ", ".join(failed_reasons)

    def handle_task_results(self, task_results_list: List[List[Dict]]) -> Tuple[bool, Dict[int, str], Dict[int, str]]:
        is_finished = True
        failed_host_reason_map: Dict[int, Optional[List, str]] = defaultdict(list)
        succeeded_host_message_map: Dict[int, Optional[List, str]] = defaultdict(list)
        for task_results in task_results_list:
            for task_result in task_results:
                bk_host_id = task_result["instance_info"]["host"]["bk_host_id"]
                node_name = task_result["steps"][0]["node_name"]
                if task_result["status"] in [constants.JobStatusType.PENDING, constants.JobStatusType.RUNNING]:
                    is_finished = False
                    failed_host_reason_map[bk_host_id].append(_("{node_name} 执行超时").format(node_name=node_name))
                elif task_result["status"] == constants.JobStatusType.FAILED:
                    failed_reason = self.extract_failed_reason_from_steps(task_result["steps"])
                    failed_host_reason_map[bk_host_id].append(failed_reason)
                elif task_result["status"] == constants.JobStatusType.SUCCESS:
                    succeeded_host_message_map[bk_host_id].append(_("{node_name} 执行成功").format(node_name=node_name))
        for bk_host_id, failed_reasons in failed_host_reason_map.items():
            failed_host_reason_map[bk_host_id] = ", ".join(failed_reasons)
        for bk_host_id, messages in succeeded_host_message_map.items():
            succeeded_host_message_map[bk_host_id] = ", ".join(messages)
        return is_finished, failed_host_reason_map, succeeded_host_message_map

    def handle_task_result_message(
        self,
        data,
        failed_host_reason_map: Dict[int, str],
        succeeded_host_message_map: Dict[int, str],
        common_data: Optional[CommonData] = None,
    ):
        # 处理失败的任务并标记失败状态
        common_data = common_data or self.get_common_data(data)
        failed_reason__sub_inst_ids_map = defaultdict(list)
        for bk_host_id, failed_reason in failed_host_reason_map.items():
            sub_inst_id = common_data.host_id__sub_inst_id_map.get(bk_host_id, 0)
            failed_reason__sub_inst_ids_map[failed_reason].append(sub_inst_id)
        for failed_reason, sub_inst_ids in failed_reason__sub_inst_ids_map.items():
            self.move_insts_to_failed(sub_inst_ids=sub_inst_ids, log_content=failed_reason)

        # 处理成功的任务并聚合写日志
        succeeded_message__sub_inst_ids_map = defaultdict(list)
        for bk_host_id, message in succeeded_host_message_map.items():
            sub_inst_id = common_data.host_id__sub_inst_id_map.get(bk_host_id, 0)
            succeeded_message__sub_inst_ids_map[message].append(sub_inst_id)
        for message, sub_inst_ids in succeeded_message__sub_inst_ids_map.items():
            self.log_info(sub_inst_ids=sub_inst_ids, log_content=message)

    def _execute(self, data, parent_data, common_data: CommonData):
        data.outputs.subscription_ids = self.create_subscriptions(common_data)
        data.outputs.all_subscription_ids = data.outputs.subscription_ids
        # 不存在需要轮询结果的子订阅，手动结束调度
        if not data.outputs.subscription_ids:
            self.finish_schedule()
            return True

    def _schedule(self, data, parent_data, callback_data=None):
        polling_time: int = data.get_one_of_outputs("polling_time") or 0
        next_polling_time: int = polling_time + POLLING_INTERVAL
        subscription_ids: List[int] = data.get_one_of_outputs("subscription_ids")
        all_subscription_ids: List[int] = data.get_one_of_outputs("all_subscription_ids")
        error_sub_ids: List[int] = []
        ready_sub_ids: List[int] = []
        no_ready_sub_ids: List[int] = []
        task_ready_infos: List[Dict[str, Any]] = self.bulk_check_subscription_task_ready(subscription_ids)
        for task_ready_info in task_ready_infos:
            sub_id = task_ready_info["subscription_id"]
            if task_ready_info["is_error"]:
                error_sub_ids.append(sub_id)
                self.log_error(
                    log_content=_("子订阅【ID：{sub_id}】任务创建失败：{err_msg}").format(
                        sub_id=sub_id, err_msg=task_ready_info["err_msg"]
                    )
                )
            elif not task_ready_info["is_ready"]:
                no_ready_sub_ids.append(sub_id)
            else:
                # 订阅任务已就绪
                ready_sub_ids.append(sub_id)

        # 下一次仅轮询未创建失败的订阅ID
        data.outputs.subscription_ids = ready_sub_ids + no_ready_sub_ids

        # 当前所有任务均创建失败
        if len(error_sub_ids) == len(subscription_ids):
            common_data = self.get_common_data(data)
            self.move_insts_to_failed(sub_inst_ids=common_data.subscription_instance_ids)
            self.finish_schedule()
            return False

        # 部分任务仍处于未就绪状态，等待下一次轮询
        if no_ready_sub_ids:
            if next_polling_time > SUB_SUBSCRIPTION_POLLING_TIMEOUT:
                common_data = self.get_common_data(data)
                self.move_insts_to_failed(
                    sub_inst_ids=common_data.subscription_instance_ids,
                    log_content=_("子订阅【ID：{no_ready_sub_ids}】任务创建超时").format(no_ready_sub_ids=no_ready_sub_ids),
                )
                self.finish_schedule()
                return False
            data.outputs.polling_time = next_polling_time
            return True

        # 仅查询就绪任务的详情，创建失败的任务已在前面的逻辑报错
        task_results = self.bulk_get_subscription_task_status(ready_sub_ids)
        is_finished, failed_host_reason_map, succeeded_host_message_map = self.handle_task_results(task_results)
        if is_finished:
            common_data = self.get_common_data(data)
            self.handle_task_result_message(
                data, failed_host_reason_map, succeeded_host_message_map, common_data=common_data
            )
            self.finish_schedule()
            all_error_sub_ids = list(set(all_subscription_ids) - set(subscription_ids))
            if not all_error_sub_ids:
                return True
            else:
                self.move_insts_to_failed(
                    sub_inst_ids=common_data.subscription_instance_ids, log_content=_("部分子订阅任务创建失败")
                )

        elif next_polling_time > SUB_SUBSCRIPTION_POLLING_TIMEOUT:
            # 任务执行超时
            self.handle_task_result_message(data, failed_host_reason_map, succeeded_host_message_map)
            self.finish_schedule()
            return False
        data.outputs.polling_time = next_polling_time
