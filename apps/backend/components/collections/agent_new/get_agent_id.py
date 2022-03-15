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
from typing import Any, Dict, List

from django.utils.translation import ugettext_lazy as _

from apps.backend.api.constants import POLLING_INTERVAL, POLLING_TIMEOUT
from apps.component.esbclient import client_v2
from apps.node_man import models
from apps.utils import batch_request
from pipeline.core.flow import Service, StaticIntervalGenerator

from .base import AgentBaseService, AgentCommonData


class GetAgentIDService(AgentBaseService):
    """安装后AgentID同步到CMDB后才认为是可用的"""

    __need_schedule__ = True
    interval = StaticIntervalGenerator(POLLING_INTERVAL)

    def outputs_format(self):
        return super().outputs_format() + [
            Service.InputItem(name="polling_time", key="polling_time", type="int", required=True),
        ]

    @staticmethod
    def update_host_agent_id(cmdb_host_infos: List[Dict[str, Any]]):
        need_update_hosts = [
            models.Host(bk_host_id=host_info["bk_host_id"], bk_agent_id=host_info.get("bk_agent_id"))
            for host_info in cmdb_host_infos
        ]
        models.Host.objects.bulk_update(need_update_hosts, fields=["bk_agent_id"])

    def _execute(self, data, parent_data, common_data: AgentCommonData):
        self.log_info(sub_inst_ids=common_data.subscription_instance_ids, log_content=_("开始查询从 CMDB 查询主机的 Agent ID"))
        data.outputs.polling_time = 0

    def _schedule(self, data, parent_data, callback_data=None):
        common_data: AgentCommonData = self.get_common_data(data)
        list_cmdb_hosts_params = {
            "fields": ["bk_host_id", "bk_agent_id"],
            "host_property_filter": {
                "condition": "AND",
                "rules": [
                    {"field": "bk_host_id", "operator": "in", "value": common_data.bk_host_ids},
                ],
            },
        }
        cmdb_host_infos: List[Dict[str, Any]] = batch_request.batch_request(
            func=client_v2.cc.list_hosts_without_biz, params=list_cmdb_hosts_params
        )

        # CMDB 中 AgentID 为空的主机ID列表
        no_agent_id_host_ids = [
            host_info["bk_host_id"] for host_info in cmdb_host_infos if not host_info.get("bk_agent_id")
        ]
        if not no_agent_id_host_ids:
            self.update_host_agent_id(cmdb_host_infos)
            self.finish_schedule()
            return

        polling_time = data.get_one_of_outputs("polling_time")
        if polling_time + POLLING_INTERVAL > POLLING_TIMEOUT:
            sub_inst_ids = [common_data.host_id__sub_inst_id_map[host_id] for host_id in no_agent_id_host_ids]
            self.move_insts_to_failed(
                sub_inst_ids=sub_inst_ids,
                log_content=_("此主机在 CMDB 中未查到对应 Agent ID，请联系 GSE 及 CMDB 团队排查 Agent ID 上报处理是否异常！"),
            )
            self.update_host_agent_id(cmdb_host_infos)
            self.finish_schedule()
            return

        data.outputs.polling_time = polling_time + POLLING_INTERVAL
