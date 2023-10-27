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

import importlib

import mock
from django.conf import settings

from apps.mock_data.api_mkd.gse.unit import GSE_PROCESS_NAME
from apps.mock_data.api_mkd.gse.utils import GseApiMockClient, get_gse_api_helper
from apps.mock_data.common_unit.host import (
    HOST_MODEL_DATA,
    HOST_MODEL_DATA_WITH_AGENT_ID,
)
from apps.node_man import constants
from apps.node_man.models import Host, ProcessStatus
from apps.node_man.periodic_tasks import sync_proc_status_task
from apps.node_man.tests.test_pericdic_tasks.utils import MockClient
from apps.node_man.tests.utils import create_host
from apps.utils import concurrent
from apps.utils.basic import chunk_lists
from apps.utils.unittest.testcase import CustomBaseTestCase


class TestSyncProcStatus(CustomBaseTestCase):
    @classmethod
    def setUpClass(cls):
        mock.patch("apps.utils.concurrent.batch_call", concurrent.batch_call_serial).start()
        super().setUpClass()

    def setUp(self) -> None:
        importlib.reload(sync_proc_status_task)
        super().setUp()

    @mock.patch("apps.node_man.periodic_tasks.utils.client_v2", MockClient)
    def test_sync_proc_status_periodic_task(self):
        Host.objects.create(**HOST_MODEL_DATA)
        sync_proc_status_task.sync_proc_status_periodic_task()

    @mock.patch(
        "apps.node_man.periodic_tasks.sync_proc_status_task.get_gse_api_helper",
        get_gse_api_helper(settings.GSE_VERSION, GseApiMockClient()),
    )
    def test_update_or_create_proc_status(self, *args, **kwargs):
        host = Host.objects.create(**HOST_MODEL_DATA)
        # 测试新建proc_status
        sync_proc_status_task.update_or_create_proc_status(None, Host.objects.all(), [GSE_PROCESS_NAME])
        mock_proc = ProcessStatus.objects.get(bk_host_id=host.bk_host_id, name=GSE_PROCESS_NAME)
        self.assertEqual(
            [mock_proc.status, mock_proc.bk_host_id, mock_proc.name],
            [constants.ProcStateType.TERMINATED, host.bk_host_id, GSE_PROCESS_NAME],
        )

        # 测试update_proc_status
        mock_proc = ProcessStatus.objects.get(bk_host_id=host.bk_host_id, name=GSE_PROCESS_NAME)
        mock_proc.status = constants.ProcStateType.MANUAL_STOP
        mock_proc.save()
        sync_proc_status_task.update_or_create_proc_status(None, Host.objects.all(), [GSE_PROCESS_NAME])
        self.assertEqual(
            [mock_proc.status, mock_proc.bk_host_id, mock_proc.name],
            [constants.ProcStateType.MANUAL_STOP, host.bk_host_id, GSE_PROCESS_NAME],
        )

    @mock.patch(
        "apps.node_man.periodic_tasks.sync_proc_status_task.get_gse_api_helper",
        get_gse_api_helper(settings.GSE_VERSION, GseApiMockClient()),
    )
    def test_update_or_create_proc_status_with_agent_id(self, *args, **kwargs):
        Host.objects.create(**HOST_MODEL_DATA_WITH_AGENT_ID)
        sync_proc_status_task.update_or_create_proc_status(None, Host.objects.all(), [GSE_PROCESS_NAME])

    @mock.patch(
        "apps.node_man.periodic_tasks.sync_proc_status_task.query_bk_biz_ids",
        mock.MagicMock(return_value=list(range(2, 41))),
    )
    @mock.patch("apps.node_man.constants.QUERY_PROC_STATUS_BIZ_SHARDING_SIZE", 5)
    def test_sync_proc_status_periodic_task_by_sharding(self):
        create_host(1000)

        host_queryset = Host.objects.all()
        host_count = host_queryset.count()
        biz_host_count = 25
        i = 1
        all_host_ids = Host.objects.values_list("bk_host_id", flat=True)
        for host_id_list in list(chunk_lists(all_host_ids, biz_host_count)):
            host_list = Host.objects.filter(bk_host_id__in=host_id_list)
            host_list.update(bk_biz_id=i)
            i += 1

        with mock.patch("apps.node_man.periodic_tasks.sync_proc_status_task.update_or_create_proc_status") as mock_func:
            sync_proc_status_task.sync_proc_status_periodic_task()
            self.assertEqual(mock_func.apply_async.call_count, host_count / biz_host_count / 5)
