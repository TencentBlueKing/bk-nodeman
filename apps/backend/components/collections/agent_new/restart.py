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

from apps.node_man import constants, models
from apps.utils.files import PathHandler

from .base import AgentCommonData, AgentExecuteScriptService


class RestartService(AgentExecuteScriptService):
    @property
    def script_name(self):
        return "restart"

    def get_script_content(self, data, common_data: AgentCommonData, host: models.Host) -> str:
        """
        获取脚本内容
        :param data:
        :param common_data:
        :param host: 主机对象
        :return: 脚本内容
        """
        # 路径处理器
        path_handler = PathHandler(host.os_type)
        ctl_exe_name = ("gsectl", "gsectl.bat")[host.os_type == constants.OsType.WINDOWS]
        cmd_suffix = ("restart >/dev/null 2>&1", "restart")[host.os_type == constants.OsType.WINDOWS]
        general_node_type = self.get_general_node_type(host.node_type)
        setup_path = common_data.host_id__ap_map[host.bk_host_id].get_agent_config(host.os_type)["setup_path"]
        agent_path = path_handler.join(setup_path, general_node_type, "bin", ctl_exe_name)

        return f"{agent_path} {cmd_suffix}"
