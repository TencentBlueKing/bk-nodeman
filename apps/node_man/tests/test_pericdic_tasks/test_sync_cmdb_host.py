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
import copy
from unittest.mock import patch

from apps.backend.views import LPUSH_AND_EXPIRE_FUNC
from apps.mock_data.common_unit.host import PROCESS_STATUS_MODEL_DATA
from apps.node_man import constants
from apps.node_man.models import Host, ProcessStatus
from apps.node_man.periodic_tasks.sync_cmdb_host import (
    clear_need_delete_host_ids_task,
    sync_cmdb_host_periodic_task,
)
from apps.utils.unittest.testcase import CustomBaseTestCase

from .mock_data import MOCK_BK_BIZ_ID, MOCK_HOST, MOCK_HOST_NUM
from .utils import MockClient


class TestSyncCMDBHost(CustomBaseTestCase):
    def init_db(self):
        """
        先在数据库提前构造一些数据
        """
        # 构造待更新数据
        MOCK_HOST_TMP = copy.deepcopy(MOCK_HOST)
        host_list = []
        for index in range(MOCK_HOST_NUM):
            MOCK_HOST_TMP["node_type"] = constants.NodeType.PROXY if index % 2 else constants.NodeType.AGENT
            MOCK_HOST_TMP["inner_ip"] = f"127.0.0.{index}"
            MOCK_HOST_TMP["bk_host_id"] = index
            host_list.append(Host(**MOCK_HOST_TMP))

        # 构造待删除数据
        MOCK_HOST_TMP["bk_host_id"] = -1
        host_list.append(Host(**MOCK_HOST_TMP))

        Host.objects.bulk_create(host_list)

    @patch("apps.node_man.periodic_tasks.sync_cmdb_host.client_v2", MockClient)
    def test_sync_cmdb_host(self):
        self.init_db()
        sync_cmdb_host_periodic_task(bk_biz_id=MOCK_BK_BIZ_ID)

        # 验证主机信息是否创建&更新成功
        itf_results = MockClient.cc.list_resource_pool_hosts()["info"]
        itf_results = [(host["bk_host_id"], host["bk_cloud_id"], host["bk_host_innerip"]) for host in itf_results]
        itf_results__host_ids = [itf_result[0] for itf_result in itf_results]
        db_result = Host.objects.filter(bk_host_id__in=itf_results__host_ids).values_list(
            "bk_host_id", "bk_cloud_id", "inner_ip"
        )
        self.assertEqual(itf_results.sort(key=lambda t: t[0]), list(db_result).sort(key=lambda t: t[0]))

        # 验证主机信息是否删除成功
        self.assertEqual(Host.objects.filter(bk_host_id=-1).count(), 0)


class TestClearNeedDeleteHostIds(CustomBaseTestCase):
    @staticmethod
    def init_db():
        proc_status_data = copy.deepcopy(PROCESS_STATUS_MODEL_DATA)
        proc_status_list = []
        for bk_host_id in range(1, 6):
            proc_status_data["bk_host_id"] = bk_host_id
            proc_status_list.append(ProcessStatus(**proc_status_data))

        ProcessStatus.objects.bulk_create(proc_status_list)

        need_delete_host_ids = range(1, 6)
        name = constants.REDIS_NEED_DELETE_HOST_IDS_KEY_TPL
        LPUSH_AND_EXPIRE_FUNC(keys=[name], args=[constants.TimeUnit.DAY] + list(need_delete_host_ids))

    @staticmethod
    def list_hosts_without_biz(*args, **kwargs):
        return {
            "count": 1,
            "info": [
                {"bk_host_id": 1},
            ],
        }

    def start_patch(self):
        MockClient.cc.list_hosts_without_biz = self.list_hosts_without_biz

    @patch("apps.node_man.periodic_tasks.sync_cmdb_host.client_v2", MockClient)
    def test_clear_need_delete_host_ids(self):
        self.init_db()
        self.start_patch()
        clear_need_delete_host_ids_task()
        # 验证ProcessStatus中信息是否删除成功
        self.assertEqual(ProcessStatus.objects.count(), 1)
