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

from apps.node_man import models

from .base import AgentBaseService, AgentCommonData


class UpdateInstallInfoService(AgentBaseService):
    def _execute(self, data, parent_data, common_data: AgentCommonData):
        hosts_to_be_updated: List[models.Host] = []
        for sub_inst in common_data.subscription_instances:
            host_info = sub_inst.instance_info["host"]
            bk_host_id = host_info["bk_host_id"]
            host_obj = common_data.host_id_obj_map[bk_host_id]

            extra_data = {
                "peer_exchange_switch_for_agent": host_info.get("peer_exchange_switch_for_agent", True),
                "bt_speed_limit": host_info.get("bt_speed_limit", 0),
            }
            if host_info.get("data_path"):
                extra_data.update({"data_path": host_info["data_path"]})
            host_obj.extra_data = extra_data
            host_obj.ap_id = host_info["ap_id"]
            hosts_to_be_updated.append(host_obj)
        models.Host.objects.bulk_update(hosts_to_be_updated, fields=["extra_data", "ap_id"], batch_size=self.batch_size)
