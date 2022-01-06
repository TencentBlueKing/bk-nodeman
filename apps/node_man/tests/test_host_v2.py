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

from apps.node_man.models import Host
from apps.node_man.tests.utils import create_host
from apps.node_man.tools.host_v2 import HostV2Tools
from apps.utils.unittest.testcase import CustomBaseTestCase


class TestHostV2Tools(CustomBaseTestCase):
    def test_list_host_ids_by_topo_node(self):
        host, *_ = create_host(number=10)
        Host.objects.all().update(bk_biz_id=30)
        topo_node = {"bk_biz_id": 30, "bk_obj_id": "biz", "bk_inst_id": 30}

        result = HostV2Tools().list_host_ids_by_topo_node(topo_node)
        self.assertEqual(len(result), 10)
