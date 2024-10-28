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
    @staticmethod
    def init_db():
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

        # 验证主机信息是否删除成功/proxy主机信息先保留
        self.assertEqual(Host.objects.filter(bk_host_id=-1).count(), 1)


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


class TestSyncCMDBMultiOuterIPHost(CustomBaseTestCase):
    @staticmethod
    def init_db():
        host_data = copy.deepcopy(MOCK_HOST)
        host_list = []
        for index in range(1, MOCK_HOST_NUM):
            host_data["node_type"] = constants.NodeType.PROXY if index % 2 else constants.NodeType.AGENT
            host_data["inner_ip"] = f"127.0.0.{index}"
            host_data["bk_host_id"] = index
            host_list.append(Host(**host_data))

        Host.objects.bulk_create(host_list)

    @staticmethod
    def list_biz_hosts(*args, **kwargs):
        return_value = MockClient.cc.list_resource_pool_hosts(*args, **kwargs)
        host_info = return_value["info"]
        for host in host_info:
            host["bk_host_outerip"] += ",1.2.3.4"
        return return_value

    def start_patch(self):
        MockClient.cc.list_biz_hosts = self.list_biz_hosts

    @patch("apps.node_man.periodic_tasks.sync_cmdb_host.client_v2", MockClient)
    def test_sync_multi_outer_ip_host(self):
        self.init_db()
        self.start_patch()
        sync_cmdb_host_periodic_task(bk_biz_id=2)
        # 验证proxy多外网IP将数据存至extra_data中
        proxy_extra_data = Host.objects.filter(node_type=constants.NodeType.PROXY).values("extra_data")
        for extra_data in proxy_extra_data:
            bk_host_multi_outerip = extra_data["extra_data"]["bk_host_multi_outerip"]
            self.assertEqual(len(bk_host_multi_outerip.split(",")), 2)
        # 验证不影响Agent存在多外网IP的情况
        agent_extra_data = Host.objects.filter(node_type=constants.NodeType.AGENT).values("extra_data")
        for data in agent_extra_data:
            extra_data = data["extra_data"]
            self.assertEqual(extra_data.get("bk_host_multi_outerip"), None)


class TestProxyTransferModule(CustomBaseTestCase):
    @staticmethod
    def init_db():
        host_data = copy.deepcopy(MOCK_HOST)
        host_list = []
        for index in range(1, MOCK_HOST_NUM):
            host_data["node_type"] = constants.NodeType.PROXY if index % 2 else constants.NodeType.AGENT
            host_data["inner_ip"] = f"127.0.0.{index}"
            host_data["bk_host_id"] = index
            host_list.append(Host(**host_data))
        host_data["bk_host_id"] = 100
        host_list.append(Host(**host_data))

        Host.objects.bulk_create(host_list)

    @staticmethod
    def list_hosts_without_biz(*args, **kwargs):
        return {
            "count": 1,
            "info": [
                {"bk_host_id": 100},
            ],
        }

    def start_patch(self):
        MockClient.cc.list_hosts_without_biz = self.list_hosts_without_biz

    @patch("apps.node_man.periodic_tasks.sync_cmdb_host.client_v2", MockClient)
    def test_transfer_module_proxy(self):
        self.init_db()
        sync_cmdb_host_periodic_task(bk_biz_id=MOCK_BK_BIZ_ID)
        # 验证需要删除的proxy主机暂存
        self.assertEqual(Host.objects.filter(bk_host_id=100, node_type=constants.NodeType.PROXY).count(), 1)
        self.start_patch()
        clear_need_delete_host_ids_task()
        # 验证转移业务/模块的proxy主未被删除
        self.assertEqual(Host.objects.filter(bk_host_id=100, node_type=constants.NodeType.PROXY).count(), 1)
