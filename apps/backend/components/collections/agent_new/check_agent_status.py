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

from collections import defaultdict
from typing import Dict, List

from django.utils.translation import ugettext_lazy as _

from apps.node_man import constants
from apps.node_man.models import ProcessStatus

from .base import AgentBaseService, AgentCommonData


class CheckAgentStatusService(AgentBaseService):
    @classmethod
    def proc_queryset_filter(cls, proc_queryset: List[ProcessStatus], host_id_to_inst_id_map: Dict[int, int]):
        inst_ids: List[int] = []
        overage_proc_ids: List[int] = []
        proc_status_ids_gby_host_id: Dict[int, List[int]] = defaultdict(list)
        for proc in proc_queryset:
            proc_status_ids_gby_host_id[proc.bk_host_id].append(proc.id)
        for bk_host_id, proc_status_ids in proc_status_ids_gby_host_id.items():
            overage_proc_ids.extend(proc_status_ids[1:])
            inst_ids.append(host_id_to_inst_id_map[bk_host_id])

        return inst_ids, overage_proc_ids

    def _execute(self, data, parent_data, common_data: AgentCommonData, callback_data=None):
        subscription_instances = common_data.subscription_instances
        subscription_instance_ids = common_data.subscription_instance_ids
        bk_host_ids = common_data.bk_host_ids

        with_running_proc_host_ids: List[int] = []
        running_process_statuses: List[ProcessStatus] = []
        host_id_to_inst_id_map: Dict[int, int] = defaultdict()
        unexpected_process_statuses: List[ProcessStatus] = []
        unexpected_proc_ids_map: Dict[int, List[int]] = defaultdict(list)

        for subscription_instance in subscription_instances:
            bk_host_id = subscription_instance.instance_info["host"]["bk_host_id"]
            host_id_to_inst_id_map[bk_host_id] = subscription_instance.id

        all_process_statuses = ProcessStatus.objects.filter(
            bk_host_id__in=bk_host_ids,
            name=ProcessStatus.GSE_AGENT_PROCESS_NAME,
        )
        for proc in all_process_statuses:
            if proc.status == constants.ProcStateType.RUNNING:
                with_running_proc_host_ids.append(proc.bk_host_id)
                running_process_statuses.append(proc)
            else:
                unexpected_process_statuses.append(proc)
                unexpected_proc_ids_map[proc.bk_host_id].append(proc.id)

        if not running_process_statuses:
            self.move_insts_to_failed(sub_inst_ids=subscription_instance_ids, log_content=_("Agent 状态【异常】"))
            return False

        unexpected_proc_ids: List[int] = []
        for bk_host_id in with_running_proc_host_ids:
            unexpected_proc_ids.extend(unexpected_proc_ids_map[bk_host_id])
        # 对于有两种进程状态的主机对应的非ruuning记录进行清理
        ProcessStatus.objects.filter(id__in=unexpected_proc_ids).delete()

        running_inst_ids, overage_running_proc_ids = self.proc_queryset_filter(
            running_process_statuses, host_id_to_inst_id_map
        )
        ProcessStatus.objects.filter(id__in=overage_running_proc_ids).delete()
        self.log_info(sub_inst_ids=running_inst_ids, log_content=_("Agent 状态【正常】"))

        unexpected_inst_ids, overage_unexpected_proc_ids = self.proc_queryset_filter(
            unexpected_process_statuses, host_id_to_inst_id_map
        )
        ProcessStatus.objects.filter(id__in=overage_unexpected_proc_ids).delete()
        self.move_insts_to_failed(sub_inst_ids=unexpected_inst_ids, log_content=_("Agent 状态【异常】"))
