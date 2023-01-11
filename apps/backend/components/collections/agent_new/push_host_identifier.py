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
from typing import Any, Dict, List, Optional

from django.utils.translation import ugettext_lazy as _

from apps.backend.api.constants import POLLING_INTERVAL, POLLING_TIMEOUT
from apps.core.concurrent import controller
from apps.utils import concurrent
from common.api import CCApi
from pipeline.core.flow import Service, StaticIntervalGenerator

from . import base
from .base import AgentBaseService, AgentCommonData


class PushIdentifierHostsService(AgentBaseService):
    __need_schedule__ = True
    interval = StaticIntervalGenerator(POLLING_INTERVAL)

    def outputs_format(self):
        return super().outputs_format() + [
            Service.InputItem(name="polling_time", key="polling_time", type="int", required=True),
            Service.InputItem(
                name="push_identifier_task_ids", key="push_identifier_task_ids", type="list", required=True
            ),
        ]

    @controller.ConcurrentController(
        data_list_name="bk_host_ids",
        batch_call_func=concurrent.batch_call,
        get_data=lambda x: [x["task_id"]],
        get_config_dict_func=lambda: {"limit": 200},
    )
    def push_host_identifier(self, bk_host_ids: List[int], host_id__sub_inst_id_map: Dict[int, int]):
        push_host_instance_ids: List[int] = []
        push_host_identifier_result: Dict[str, Any] = CCApi.push_host_identifier({"bk_host_ids": bk_host_ids})
        for bk_host_id in bk_host_ids:
            push_host_instance_ids.append(host_id__sub_inst_id_map[bk_host_id])
        self.log_info(
            sub_inst_ids=push_host_instance_ids,
            log_content=_("推送主机身份的任务为: [{task_id}]").format(task_id=push_host_identifier_result["task_id"]),
        )
        return push_host_identifier_result

    @controller.ConcurrentController(
        data_list_name="task_ids",
        batch_call_func=concurrent.batch_call,
        get_data=lambda x: [x],
        get_config_dict_func=lambda: {"limit": 1},
    )
    def find_host_identifier_push_result(self, task_ids: List[str]):
        identifier_push_result: Dict[str, List[int]] = CCApi.find_host_identifier_push_result({"task_id": task_ids[0]})
        return identifier_push_result

    def _execute(self, data, parent_data, common_data: base.AgentCommonData):
        host_id__sub_inst_id_map = common_data.host_id__sub_inst_id_map
        push_identifier_task_ids: List[str] = self.push_host_identifier(
            bk_host_ids=list(common_data.bk_host_ids), host_id__sub_inst_id_map=host_id__sub_inst_id_map
        )
        data.outputs.push_identifier_task_ids = push_identifier_task_ids
        data.outputs.polling_time = 0

    def _schedule(self, data, parent_data, callback_data=None):
        common_data: AgentCommonData = self.get_common_data(data)
        polling_time: int = data.get_one_of_outputs("polling_time")
        push_identifier_task_ids: List[str] = data.get_one_of_outputs("push_identifier_task_ids")
        total_failed_push_host_ids: List[int] = data.get_one_of_outputs("total_failed_push_host_ids") or []

        addition_failed_push_host_ids: List[int] = []
        pending_push_host_ids: List[int] = []

        push_identifier_tasks_result: List[Dict[str, List[int]]] = self.find_host_identifier_push_result(
            task_ids=push_identifier_task_ids
        )
        for push_identifier_task_result in push_identifier_tasks_result:

            addition_failed_push_host_ids: Optional[List[int]] = [
                bk_host_id
                for bk_host_id in push_identifier_task_result.get("failed_list", [])
                if bk_host_id not in total_failed_push_host_ids
            ]
            pending_push_host_ids.extend(push_identifier_task_result.get("pending_list", []))

        if addition_failed_push_host_ids:
            failed_push_instance_ids: List[int] = [
                common_data.host_id__sub_inst_id_map[bk_host_id] for bk_host_id in addition_failed_push_host_ids
            ]
            self.move_insts_to_failed(sub_inst_ids=failed_push_instance_ids, log_content=_("推送主机身份失败"))

        pending_push_instance_ids: List[int] = [
            common_data.host_id__sub_inst_id_map[bk_host_id] for bk_host_id in set(pending_push_host_ids)
        ]

        if not pending_push_host_ids and not addition_failed_push_host_ids:
            self.finish_schedule()
            return

        if polling_time + POLLING_INTERVAL > POLLING_TIMEOUT:
            self.move_insts_to_failed(sub_inst_ids=pending_push_instance_ids, log_content=_("推送主机身份超时"))
            self.finish_schedule()
            return

        data.outputs.polling_time = polling_time + POLLING_INTERVAL
        data.outputs.total_failed_push_host_ids = list(set(total_failed_push_host_ids + addition_failed_push_host_ids))
