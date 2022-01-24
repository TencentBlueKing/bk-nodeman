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

from typing import Set

from django.utils.translation import ugettext_lazy as _

from apps.node_man import constants, models

from .base import AgentBaseService, AgentCommonData


class CheckAgentStatusService(AgentBaseService):
    def _execute(self, data, parent_data, common_data: AgentCommonData, callback_data=None):

        # 保证进程记录唯一性
        self.maintain_agent_proc_status_uniqueness(common_data.bk_host_ids)

        # 查询正常的 Agent 进程记录
        host_ids_with_normal_agent = models.ProcessStatus.objects.filter(
            **self.agent_proc_common_data,
            bk_host_id__in=common_data.bk_host_ids,
            status=constants.ProcStateType.RUNNING
        ).values_list("bk_host_id", flat=True)

        normal_sub_inst_ids: Set[int] = set()
        # 做存在性校验，使用 set 提高 in 执行效率
        host_ids_with_running_agent = set(host_ids_with_normal_agent)
        for sub_inst_id in common_data.subscription_instance_ids:
            bk_host_id = common_data.sub_inst_id__host_id_map[sub_inst_id]
            if bk_host_id in host_ids_with_running_agent:
                normal_sub_inst_ids.add(sub_inst_id)

        self.log_info(sub_inst_ids=normal_sub_inst_ids, log_content=_("Agent 状态【正常】"))
        self.move_insts_to_failed(
            sub_inst_ids=common_data.subscription_instance_ids - normal_sub_inst_ids, log_content=_("Agent 状态【异常】")
        )
        return True
