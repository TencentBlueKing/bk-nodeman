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
from unittest.mock import patch

from django.conf import settings
from django.test import override_settings

from apps.adapters.api import gse
from apps.mock_data.api_mkd.gse.unit import GSE_PROCESS_VERSION
from apps.mock_data.api_mkd.gse.utils import GseApiMockClient
from apps.mock_data.common_unit.host import (
    HOST_MODEL_DATA,
    HOST_MODEL_DATA_WITH_AGENT_ID,
)
from apps.node_man import constants
from apps.node_man.models import Host, ProcessStatus
from apps.node_man.periodic_tasks.sync_agent_status_task import (
    sync_agent_status_periodic_task,
    update_or_create_host_agent_status,
)
from apps.utils.unittest.testcase import CustomBaseTestCase
from env.constants import GseVersion


class TestSyncAgentStatus(CustomBaseTestCase):
    def test_sync_agent_status_periodic_task(self):
        Host.objects.create(**HOST_MODEL_DATA)
        sync_agent_status_periodic_task()

    def test_update_or_create_host_agent_status_no_host(self):
        update_or_create_host_agent_status(None, 0, 1)
        self.assertEqual(ProcessStatus.objects.count(), 0)

    @patch(
        "apps.node_man.periodic_tasks.sync_agent_status_task.GseApiHelper",
        gse.get_gse_api_helper_class(settings.GSE_VERSION)(settings.GSE_VERSION, GseApiMockClient()),
    )
    def test_update_or_create_host_agent_status_alive(self):
        host = Host.objects.create(**HOST_MODEL_DATA)
        # 测试创建ProcessStatus对象
        update_or_create_host_agent_status(None, 0, 1)
        process_status = ProcessStatus.objects.get(bk_host_id=host.bk_host_id)
        self.assertEqual(process_status.status, constants.ProcStateType.RUNNING)
        self.assertEqual(process_status.version, GSE_PROCESS_VERSION)
        host = Host.objects.get(bk_host_id=host.bk_host_id)
        self.assertEqual(host.node_from, constants.NodeFrom.NODE_MAN)

    @patch(
        "apps.node_man.periodic_tasks.sync_agent_status_task.GseApiHelper",
        gse.get_gse_api_helper_class(settings.GSE_VERSION)(
            settings.GSE_VERSION,
            GseApiMockClient(get_agent_status_return=GseApiMockClient.GET_AGENT_NOT_ALIVE_STATUS_RETURN),
        ),
    )
    def test_update_or_create_host_agent_status_not_alive(self):
        host = Host.objects.create(**HOST_MODEL_DATA)
        # 测试创建ProcessStatus对象
        update_or_create_host_agent_status(None, 0, 1)
        process_status = ProcessStatus.objects.get(bk_host_id=host.bk_host_id)
        self.assertEqual(process_status.status, constants.ProcStateType.NOT_INSTALLED)

        # Agent异常且已在节点管理录入过的，标记状态为异常
        host.node_from = constants.NodeFrom.NODE_MAN
        host.save()
        update_or_create_host_agent_status(None, 0, 1)
        process_status = ProcessStatus.objects.get(bk_host_id=host.bk_host_id)
        self.assertEqual(process_status.status, constants.ProcStateType.TERMINATED)

    @override_settings(GSE_VERSION=GseVersion.V2.value)
    @patch(
        "apps.node_man.periodic_tasks.sync_agent_status_task.GseApiHelper",
        gse.get_gse_api_helper_class(GseVersion.V2.value)(GseVersion.V2.value, GseApiMockClient()),
    )
    def test_update_or_create_host_agent_status_alive_gse_v2(self):
        host = Host.objects.create(**HOST_MODEL_DATA_WITH_AGENT_ID)
        # 测试创建ProcessStatus对象
        update_or_create_host_agent_status(None, 0, 1)
        process_status = ProcessStatus.objects.get(bk_host_id=host.bk_host_id)
        self.assertEqual(process_status.status, constants.ProcStateType.RUNNING)

    @override_settings(GSE_VERSION=GseVersion.V2.value)
    @patch(
        "apps.node_man.periodic_tasks.sync_agent_status_task.GseApiHelper",
        gse.get_gse_api_helper_class(GseVersion.V2.value)(
            GseVersion.V2.value,
            GseApiMockClient(v2_cluster_list_agent_state_return=GseApiMockClient.GET_AGENT_NOT_ALIVE_STATE_LIST_RETURN),
        ),
    )
    def test_update_or_create_host_agent_status_not_alive_gse_v2(self):
        host = Host.objects.create(**HOST_MODEL_DATA)
        # 测试创建ProcessStatus对象
        update_or_create_host_agent_status(None, 0, 1)
        process_status = ProcessStatus.objects.get(bk_host_id=host.bk_host_id)
        self.assertEqual(process_status.status, constants.ProcStateType.NOT_INSTALLED)
