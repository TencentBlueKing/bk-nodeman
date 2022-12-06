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

from typing import Dict, List, Union

from django.utils.translation import ugettext_lazy as _

from apps.adapters.api.gse import GseApiHelper

from .base import AgentBaseService, AgentCommonData


class UpgradeToAgentIDService(AgentBaseService):
    def _execute(self, data, parent_data, common_data: AgentCommonData):
        upgrade_hosts: List[Dict[str, Union[int, str]]] = []
        cloud_ip__sub_inst_id_map: Dict[str, int] = {}
        # 如果主机有AgentID，则调用 upgrade_to_agent_id 将基于 Host IP 的配置升级到基于 Agent-ID 的配置
        for host_id, sub_inst_id in common_data.host_id__sub_inst_id_map.items():
            host = common_data.host_id_obj_map[host_id]
            upgrade_hosts.append(
                {"ip": host.inner_ip, "bk_cloud_id": host.bk_cloud_id, "bk_agent_id": host.bk_agent_id}
            )
            cloud_ip__sub_inst_id_map[f"{host.bk_cloud_id}:{host.inner_ip}"] = sub_inst_id

        upgrade_hosts = [
            {"ip": host.inner_ip, "bk_cloud_id": host.bk_cloud_id, "bk_agent_id": host.bk_agent_id}
            for host in common_data.host_id_obj_map.values()
            if host.bk_agent_id
        ]

        if not upgrade_hosts:
            return True
        result = GseApiHelper.upgrade_to_agent_id(hosts=upgrade_hosts)
        failed_cloud_ips = result.get("failed") or []
        failed_sub_inst_ids = [cloud_ip__sub_inst_id_map[cloud_ip] for cloud_ip in failed_cloud_ips]
        self.move_insts_to_failed(failed_sub_inst_ids, log_content=_("升级 Agent-ID 配置失败"))
