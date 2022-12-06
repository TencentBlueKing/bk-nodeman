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
from typing import List

from django.conf import settings

from apps.node_man import constants, models

from .base import AgentCommonData, AgentTransferFileService


class PushUpgradeFileService(AgentTransferFileService):
    def get_file_target_path(self, data, common_data: AgentCommonData, host: models.Host) -> str:
        return common_data.host_id__ap_map[host.bk_host_id].get_agent_config(host.os_type)["temp_path"]

    def get_upgrade_package_source_path(self, common_data: AgentCommonData, host: models.Host):
        """
        获取升级包源路径
        """
        # 1.x 升级到 1.x，使用老到路径，升级包直接放在 download 目录下
        download_path = common_data.host_id__ap_map[host.bk_host_id].nginx_path or settings.DOWNLOAD_PATH
        if not common_data.agent_step_adapter.is_legacy:
            # 2.x 升级到 2.x，根据操作系统、CPU 架构等组合路径
            download_path = os.path.join(download_path, "agent", host.os_type.lower(), host.cpu_arch.lower())
        return download_path

    def get_file_list(self, data, common_data: AgentCommonData, host: models.Host) -> List[str]:
        download_path = self.get_upgrade_package_source_path(common_data, host)
        agent_upgrade_package_name = self.get_agent_upgrade_pkg_name(common_data, host=host)

        file_names: List[str] = [agent_upgrade_package_name]

        # Windows 机器需要添加解压工具
        if host.os_type == constants.OsType.WINDOWS:
            file_names.extend(["7z.dll", "7z.exe"])

        return [os.path.join(download_path, file_name) for file_name in file_names]
