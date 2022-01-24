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

from apps.node_man import models

from .base import AgentCommonData, AgentTransferFileService


class PushFilesToProxyService(AgentTransferFileService):
    def get_file_list(self, data, common_data: AgentCommonData, host: models.Host) -> List[str]:
        file_list = data.get_one_of_inputs("file_list", default=[])
        download_path = common_data.host_id__ap_map[host.bk_host_id].nginx_path or settings.DOWNLOAD_PATH
        return [os.path.join(download_path, file_name) for file_name in file_list]
