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

from apps.node_man.models import AccessPoint
from apps.node_man.periodic_tasks.gse_svr_discovery import (
    gse_svr_discovery_periodic_task,
)
from apps.utils.unittest.testcase import CustomBaseTestCase

from .mock_data import MOCK_AP_FIELD_MAP
from .utils import MockKazooClient, check_ip_ports_reachable


class TestGseSvrDiscovery(CustomBaseTestCase):
    @patch("apps.node_man.periodic_tasks.gse_svr_discovery.settings.GSE_ENABLE_SVR_DISCOVERY", True)
    @patch("apps.node_man.periodic_tasks.gse_svr_discovery.KazooClient", MockKazooClient)
    @patch("apps.node_man.periodic_tasks.gse_svr_discovery.check_ip_ports_reachable", check_ip_ports_reachable)
    def test_gse_svr_discovery(self):
        gse_svr_discovery_periodic_task()
        ap = AccessPoint.objects.all().first()

        # 检查ap_field是否已经更新。注: 如果gse_svr_discovery的ap_field更改了，单测这里也需要同步更改
        ap_field_list = ["dataserver", "dataserver", "btfileserver"]
        for ap_field in ap_field_list:
            self.assertEqual(getattr(ap, ap_field, []), MOCK_AP_FIELD_MAP)
