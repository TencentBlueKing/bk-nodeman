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

from typing import List

from django.utils.translation import ugettext_lazy as _

from apps.node_man import constants
from apps.node_man.models import Host, ProcessStatus
from pipeline.core.flow import Service

from .base import AgentBaseService, AgentCommonData


class UpdateProcessStatusService(AgentBaseService):
    def inputs_format(self):
        return super().inputs_format() + [Service.InputItem(name="status", key="status", type="str", required=True)]

    def _execute(self, data, parent_data, common_data: AgentCommonData):
        status = data.get_one_of_inputs("status")
        host_id_obj_map = common_data.host_id_obj_map
        subscription_instance_ids = common_data.subscription_instance_ids
        bk_host_ids = common_data.bk_host_ids

        if status == constants.ProcStateType.NOT_INSTALLED:
            update_host_ids: List[int] = []

            for host_id, host_obj in host_id_obj_map.items():
                if host_obj.node_from != constants.NodeFrom.CMDB:
                    update_host_ids.append(host_id)

            # TODO 修改主机的逻辑应该单独抽出一个插件，防止后续插件复用，该更新逻辑影响其他流程
            Host.objects.filter(bk_host_id__in=update_host_ids).update(node_from=constants.NodeFrom.CMDB)

            # 更新进程状态
            ProcessStatus.objects.filter(bk_host_id__in=bk_host_ids, **self.agent_proc_common_data).update(
                status=constants.ProcStateType.NOT_INSTALLED
            )

            self.log_info(
                sub_inst_ids=subscription_instance_ids, log_content=_("更新主机状态为{status}".format(status=status))
            )
            return True
