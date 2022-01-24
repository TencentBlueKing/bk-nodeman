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

from apps.backend.views import generate_gse_config
from apps.node_man import models
from apps.utils.files import PathHandler

from .base import AgentCommonData, AgentPushConfigService


class RenderAndPushGseConfigService(AgentPushConfigService):
    def get_config_info_list(self, data, common_data: AgentCommonData, host: models.Host) -> List[Dict[str, Any]]:
        file_name = "agent.conf"
        general_node_type = self.get_general_node_type(host.node_type)
        content = generate_gse_config(
            host=host, filename=file_name, node_type=general_node_type, ap=common_data.host_id__ap_map[host.bk_host_id]
        )
        return [{"file_name": file_name, "content": content}]

    def get_file_target_path(self, data, common_data: AgentCommonData, host: models.Host) -> str:
        general_node_type = self.get_general_node_type(host.node_type)
        path_handler = PathHandler(host.os_type)
        setup_path = common_data.host_id__ap_map[host.bk_host_id].get_agent_config(host.os_type)["setup_path"]
        return path_handler.join(setup_path, general_node_type, "etc")
