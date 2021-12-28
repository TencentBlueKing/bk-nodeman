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

import contextlib
from unittest.mock import patch

from apps.node_man import constants
from apps.node_man.models import Host, ProcessStatus
from apps.node_man.periodic_tasks.sync_proc_status_task import (
    update_or_create_proc_status,
)
from apps.node_man.tests.test_pericdic_tasks.mock_data import (
    MOCK_HOST,
    MOCK_PROC_NAME,
    MOCK_PROC_STATUS,
)
from apps.node_man.tests.test_pericdic_tasks.utils import MockClient
from apps.utils.unittest.testcase import CustomBaseTestCase


class TestSyncProcStatus(CustomBaseTestCase):
    @contextlib.contextmanager
    def init_db(self):
        # 创造一个虚拟主机和虚拟进程信息
        mock_host, _ = Host.objects.get_or_create(**MOCK_HOST)
        mock_proc, _ = ProcessStatus.objects.get_or_create(**MOCK_PROC_STATUS)

        yield mock_host

        # 清除相关数据
        Host.objects.get(bk_host_id=MOCK_HOST["bk_host_id"]).delete()
        ProcessStatus.objects.get(bk_host_id=MOCK_HOST["bk_host_id"], name=MOCK_PROC_STATUS["name"]).delete()

    @patch("apps.node_man.periodic_tasks.sync_proc_status_task.client_v2", MockClient)
    def test_update_or_create_proc_status(self, *args, **kwargs):
        with self.init_db() as mock_host:
            # 测试update_proc_status
            # result = query_proc_status("test_proc", [{"ip": "127.0.0.1", "bk_cloud_id": 0}])
            update_or_create_proc_status(None, [mock_host], [MOCK_PROC_NAME], 0)
            mock_proc = ProcessStatus.objects.get(bk_host_id=MOCK_HOST["bk_host_id"], name=MOCK_PROC_NAME)
            self.assertEqual(
                [mock_proc.status, mock_proc.bk_host_id, mock_proc.name],
                [constants.ProcStateType.RUNNING, MOCK_HOST["bk_host_id"], MOCK_PROC_NAME],
            )

            # 测试create_proc_status 先删掉存在的proc_status
            ProcessStatus.objects.get(bk_host_id=MOCK_HOST["bk_host_id"], name=MOCK_PROC_NAME).delete()
            update_or_create_proc_status(None, [mock_host], [MOCK_PROC_NAME], 0)
            mock_proc = ProcessStatus.objects.get(bk_host_id=MOCK_HOST["bk_host_id"], name=MOCK_PROC_NAME)
            self.assertEqual(
                [mock_proc.status, mock_proc.bk_host_id, mock_proc.name],
                [constants.ProcStateType.RUNNING, MOCK_HOST["bk_host_id"], MOCK_PROC_NAME],
            )
