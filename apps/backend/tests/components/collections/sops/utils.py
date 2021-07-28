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
import random

from apps.backend.tests.components.collections.agent.utils import BK_HOST_ID
from apps.node_man import constants as const
from apps.node_man import models

DEFAULT_BIZ_ID_NAME = {"bk_biz_id": "10", "bk_biz_name": "测试Pipeline原子专用"}

SOPS_BIZ = "1"
SOPS_USERNAME = "admin"

# 测试伪造ip
TEST_IP = "127.0.0.1"
TASK_ID = random.randint(100, 1000)
# 目标主机信息
SOPS_HOST_PARAMS = {
    "bk_host_id": BK_HOST_ID,
    "bk_biz_id": DEFAULT_BIZ_ID_NAME["bk_biz_id"],
    "bk_cloud_id": const.DEFAULT_CLOUD,
    "inner_ip": TEST_IP,
    "outer_ip": TEST_IP,
    "login_ip": TEST_IP,
    "data_ip": None,
    "os_type": "LINUX",
    "node_type": const.NodeType.AGENT,
    "node_from": "NODE_MAN",
    "ap_id": const.DEFAULT_AP_ID,
    "upstream_nodes": [],
    "is_manual": 0,
    "extra_data": {"bt_speed_limit": None, "peer_exchange_switch_for_agent": 1},
}


class SopsMockClient:
    def __init__(self, *args, **kwargs):
        pass

    class sops:
        def create_task(self, *args, **kwargs):
            return {
                "result": True,
                "data": {"task_id": TASK_ID},
            }

        def start_task(self, *args, **kwargs):
            return {"result": True, "data": {}}

        def get_task_status(self, *args, **kwargs):
            return {"result": True, "data": {"state": "FINISHED"}}


class SopsParamFactory:
    @classmethod
    def init_db(self):
        models.Host.objects.create(**SOPS_HOST_PARAMS)
