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

from unittest.mock import patch

from apps.node_man import constants
from apps.node_man.models import Host, ProcessStatus
from apps.node_man.periodic_tasks.sync_agent_status_task import (
    update_or_create_host_agent_status,
)
from apps.utils.unittest.testcase import CustomBaseTestCase

from .mock_data import MOCK_GET_AGENT_STATUS, MOCK_HOST
from .utils import MockClient, modify_constant_data


class TestSyncAgentStatus(CustomBaseTestCase):
    @patch("apps.node_man.periodic_tasks.sync_agent_status_task.client_v2", MockClient)
    def test_update_or_create_host_agent_status(self):
        host, _ = Host.objects.get_or_create(**MOCK_HOST)

        # 测试创建ProcessStatus对象
        update_or_create_host_agent_status(None, 0, 1)
        self.assertEqual(ProcessStatus.objects.count(), 1)

        # agent状态为alive时 更新主机信息node_from为NODE_MAN
        update_or_create_host_agent_status(None, 0, 1)
        self.assertEqual(Host.objects.get(bk_host_id=host.bk_host_id).node_from, constants.NodeFrom.NODE_MAN)

        # agent状态信息为not alive时 更新进程信息为NOT_INSTALLED/TERMINATED
        with modify_constant_data(
            [(MOCK_GET_AGENT_STATUS[f"{host.bk_cloud_id}:{host.inner_ip}"], {"bk_agent_alive": 0})]
        ):
            update_or_create_host_agent_status(None, 0, 1)
            self.assertEqual(
                ProcessStatus.objects.get(bk_host_id=host.bk_host_id).status, constants.PROC_STATUS_DICT[2]
            )
