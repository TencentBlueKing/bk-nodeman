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

import os.path
from typing import List

from django.conf import settings

from apps.node_man import constants, models

from .base import AgentCommonData, AgentTransferPackageService


class PushUpgradePackageService(AgentTransferPackageService):
    def get_file_target_path(self, data, common_data: AgentCommonData, host: models.Host) -> str:
        return common_data.host_id__ap_map[host.bk_host_id].get_agent_config(host.os_type)["temp_path"]

    def get_file_list(self, data, common_data: AgentCommonData, host: models.Host) -> List[str]:

        download_path = common_data.host_id__ap_map[host.bk_host_id].nginx_path or settings.DOWNLOAD_PATH
        agent_upgrade_package_name = self.get_agent_upgrade_pkg_name(host=host)

        file_names: List[str] = [agent_upgrade_package_name]

        # Windows 机器需要添加解压工具
        if host.os_type == constants.OsType.WINDOWS:
            file_names.extend(["7z.dll", "7z.exe"])

        return [os.path.join(download_path, file_name) for file_name in file_names]
