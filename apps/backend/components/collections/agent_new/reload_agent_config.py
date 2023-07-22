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
from collections import defaultdict

from apps.node_man import constants, models
from apps.utils.files import PathHandler

from .base import AgentCommonData
from .restart import RestartService


class ReloadAgentConfigService(RestartService):
    @property
    def script_name(self):
        return "reload"

    def get_script_content(self, data, common_data: AgentCommonData, host: models.Host) -> str:
        """
        获取脚本内容
        :param data:
        :param common_data:
        :param host: 主机对象
        :return: 脚本内容
        """
        # Windows 复用重启逻辑完成重载操作
        if host.os_type == constants.OsType.WINDOWS:
            return super().get_script_content(data, common_data, host)

        # 路径处理器
        path_handler = PathHandler(host.os_type)
        general_node_type = self.get_general_node_type(host.node_type)
        setup_path = common_data.host_id__ap_map[host.bk_host_id].get_agent_config(host.os_type)["setup_path"]
        agent_path = path_handler.join(setup_path, general_node_type, "bin")
        if common_data.agent_step_adapter.is_legacy:
            return f"cd {agent_path} && ./gse_agent --reload"
        else:
            return f"cd {agent_path} && ./gsectl --reload agent"

    def update_host_upstream_nodes(self, common_data: AgentCommonData, gse_version: str):
        hosts = [host for host in common_data.host_id_obj_map.values() if host.bk_cloud_id != constants.DEFAULT_CLOUD]
        host_id__installation_tool_map = self.get_host_id__installation_tool_map(common_data, hosts, False, gse_version)
        # 把上游节点相同的主机进行分类并更新
        upstream_nodes__host_ids_map = defaultdict(list)
        for host_id, installation_tool in host_id__installation_tool_map.items():
            upstream_nodes__host_ids_map[installation_tool.upstream_nodes].append(host_id)
        for upstream_nodes, host_ids in upstream_nodes__host_ids_map.items():
            models.Host.objects.filter(bk_host_id__in=host_ids).update(upstream_nodes=upstream_nodes.split(","))

    def _execute(self, data, parent_data, common_data: AgentCommonData):
        gse_version: str = data.get_one_of_inputs("meta", {}).get("GSE_VERSION")
        super(ReloadAgentConfigService, self)._execute(data, parent_data, common_data)
        self.update_host_upstream_nodes(common_data, gse_version)
