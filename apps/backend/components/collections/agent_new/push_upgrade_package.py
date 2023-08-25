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

import os.path
from typing import List, Tuple

from django.conf import settings

from apps.node_man import constants, models

from .base import AgentCommonData, AgentTransferFileService


class PushUpgradeFileService(AgentTransferFileService):
    def get_file_target_path(self, data, common_data: AgentCommonData, host: models.Host) -> str:
        host_ap = self.get_host_ap(common_data=common_data, host=host)
        return host_ap.get_agent_config(host.os_type)["temp_path"]

    def get_upgrade_package_source_path(self, common_data: AgentCommonData, host: models.Host) -> Tuple[str, str]:
        """
        获取升级包源路径
        """
        host_ap = self.get_host_ap(common_data=common_data, host=host)
        # 1.x 升级到 1.x，使用老到路径，升级包直接放在 download 目录下
        agent_path = root_path = host_ap.nginx_path or settings.DOWNLOAD_PATH
        if not common_data.agent_step_adapter.is_legacy:
            # 2.x 升级到 2.x，根据操作系统、CPU 架构等组合路径
            agent_path = os.path.join(root_path, "agent", host.os_type.lower(), host.cpu_arch.lower())
        return root_path, agent_path

    def get_file_list(self, data, common_data: AgentCommonData, host: models.Host) -> List[str]:
        root_path, agent_path = self.get_upgrade_package_source_path(common_data, host)
        agent_upgrade_package_name = self.get_agent_pkg_name(common_data, host=host, is_upgrade=True)

        file_list: List[str] = [os.path.join(agent_path, agent_upgrade_package_name)]

        # Windows 机器需要添加解压工具
        if host.os_type == constants.OsType.WINDOWS:
            for zip_tool in ["7z.dll", "7z.exe"]:
                file_list.append(os.path.join(root_path, zip_tool))

        return file_list
