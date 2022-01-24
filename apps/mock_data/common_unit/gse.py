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


from apps.node_man import constants

from . import host

GET_AGENT_STATUS_DATA = {
    f"{constants.DEFAULT_CLOUD}:{host.DEFAULT_IP}": {
        "ip": host.DEFAULT_IP,
        "bk_cloud_id": constants.DEFAULT_CLOUD,
        "bk_agent_alive": constants.BkAgentStatus.ALIVE.value,
    }
}

GET_AGENT_INFO_DATA = {
    f"{constants.DEFAULT_CLOUD}:{host.DEFAULT_IP}": {
        "ip": host.DEFAULT_IP,
        "version": "V0.01R060D38",
        "bk_cloud_id": 0,
        "parent_ip": host.DEFAULT_IP,
        "parent_port": 50000,
    }
}
