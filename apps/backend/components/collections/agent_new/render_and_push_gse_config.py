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

from dataclasses import dataclass, fields
from typing import Any, Dict, List

from apps.node_man import models
from apps.node_man.periodic_tasks.sync_agent_status_task import (
    update_or_create_host_agent_status,
)
from apps.utils.files import PathHandler

from .base import AgentCommonData, AgentPushConfigService


@dataclass
class RenderAndPushConfigCommonData(AgentCommonData):
    # 主机Agent版本信息
    host_id__agent_state_info: Dict[int, Dict[str, Any]]


class RenderAndPushGseConfigService(AgentPushConfigService):
    def _execute(self, data, parent_data, common_data: AgentCommonData):
        # 2.0重载配置实时获取Agent版本
        is_need_request_agent_version: bool = data.get_one_of_inputs("is_need_request_agent_version")
        if not is_need_request_agent_version or common_data.agent_step_adapter.is_legacy:
            host_id__agent_state_info: Dict = {}
        else:
            host_id__agent_state_info: Dict[int, Dict[str, Any]] = update_or_create_host_agent_status(
                task_id="[reload_agent_fill_agent_state_info_to_hosts]",
                host_queryset=models.Host.objects.filter(bk_host_id__in=common_data.bk_host_ids),
            )
        render_and_push_common_data = RenderAndPushConfigCommonData(
            host_id__agent_state_info=host_id__agent_state_info,
            **{field.name: getattr(common_data, field.name) for field in fields(common_data)}
        )

        return super()._execute(data, parent_data, render_and_push_common_data)

    def get_config_info_list(
        self, data, common_data: RenderAndPushConfigCommonData, host: models.Host
    ) -> List[Dict[str, Any]]:
        file_name_list: List[str] = common_data.agent_step_adapter.get_config_filename_by_node_type(host.node_type)
        general_node_type = self.get_general_node_type(host.node_type)
        host_ap: models.AccessPoint = self.get_host_ap(common_data=common_data, host=host)

        config_file_list: List[Dict[str, Any]] = []
        for file_name in file_name_list:
            config_file_list.append(
                {
                    "file_name": file_name,
                    "content": common_data.agent_step_adapter.get_config(
                        host=host,
                        filename=file_name,
                        node_type=general_node_type,
                        ap=host_ap,
                        target_version=common_data.host_id__agent_state_info.get(host.bk_host_id, {}).get("version"),
                    ),
                }
            )
        return config_file_list

    def get_file_target_path(self, data, common_data: RenderAndPushConfigCommonData, host: models.Host) -> str:
        general_node_type = self.get_general_node_type(host.node_type)
        path_handler = PathHandler(host.os_type)
        host_ap: models.AccessPoint = self.get_host_ap(common_data=common_data, host=host)
        setup_path = host_ap.get_agent_config(host.os_type)["setup_path"]
        return path_handler.join(setup_path, general_node_type, "etc")
