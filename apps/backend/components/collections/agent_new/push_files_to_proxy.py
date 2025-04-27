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
from typing import List, Optional

from django.conf import settings

from apps.node_man import constants, models

from .base import AgentCommonData, AgentTransferFileService


class PushFilesToProxyService(AgentTransferFileService):
    def get_file_list(self, data, common_data: AgentCommonData, host: models.Host) -> List[str]:
        file_list = data.get_one_of_inputs("file_list", default=[])
        exclude_map = {
            # 后续加入新的架构需要加入到此map
            constants.CpuType.x86_64: ("aarch64.tgz",),
            constants.CpuType.aarch64: ("x86_64.tgz",),
        }
        # 获取当前架构对应的排除后缀
        exclude_suffix = exclude_map.get(host.cpu_arch, tuple())
        if exclude_suffix:
            file_list = [item for item in file_list if not item.endswith(exclude_suffix)]
        from_type = data.get_one_of_inputs("from_type")
        host_ap: Optional[models.AccessPoint] = self.get_host_ap(common_data, host)
        if not host_ap:
            return []
        if from_type == constants.ProxyFileFromType.AP_CONFIG.value:
            file_list = host_ap.proxy_package or file_list
        download_path = host_ap.nginx_path or settings.DOWNLOAD_PATH
        return [os.path.join(download_path, file_name) for file_name in file_list]
