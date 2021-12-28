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

from django.core.cache import cache

from apps.node_man.periodic_tasks.sync_cmdb_biz_topo_task import (
    get_and_cache_format_biz_topo,
)
from apps.utils.unittest.testcase import CustomBaseTestCase

from .mock_data import MOCK_BK_BIZ_ID
from .utils import MockClient


class TestSyncCMDBBizTopo(CustomBaseTestCase):
    def get_topo_path(self, topo__id_path_map, now_topo):
        topo__id_path_map[now_topo["biz_inst_id"]] = now_topo["path"]

        for children_topo in now_topo["children"]:
            self.get_topo_path(topo__id_path_map, children_topo)

    @patch("apps.node_man.periodic_tasks.sync_cmdb_biz_topo_task.client_v2", MockClient)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_get_and_cache_format_biz_topo(self):
        get_and_cache_format_biz_topo(MOCK_BK_BIZ_ID)
        topo_cache = cache.get(f"{MOCK_BK_BIZ_ID}_topo_cache")
        topo_nodes = cache.get(f"{MOCK_BK_BIZ_ID}_topo_nodes")

        # 这里做一个{biz_inst_id: path}的路径验证，判断topo_cache与topo_nodes生成一致
        topo_nodes__id_path_map = {item["biz_inst_id"]: item["path"] for item in topo_nodes}
        topo_cache__id_path_map = {}
        self.get_topo_path(topo_cache__id_path_map, topo_cache)

        self.assertEqual(topo_cache__id_path_map, topo_nodes__id_path_map)
