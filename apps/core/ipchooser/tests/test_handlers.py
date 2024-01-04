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

from django.test import TestCase

from apps.core.ipchooser.handlers.host_handler import HostHandler
from apps.node_man import models
from apps.node_man.tests.utils import MockClient, cmdb_or_cache_biz, create_host


class TestHostHandler(TestCase):
    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_check(self):
        create_host(1, bk_host_id=1000, ip="10.0.0.1", bk_cloud_id=0)
        res = HostHandler.check(
            scope_list=[{"scope_type": "biz", "scope_id": f"{i}", "bk_biz_id": i} for i in range(27, 40)],
            limit_host_ids=None,
            ip_list=["0:[10.0.0.1]"],
            ipv6_list=[],
            key_list=[],
        )
        self.assertEqual(res[0]["ip"], "10.0.0.1")
        res = HostHandler.check(
            scope_list=[{"scope_type": "biz", "scope_id": f"{i}", "bk_biz_id": i} for i in range(27, 40)],
            limit_host_ids=None,
            ip_list=["0:10.0.0.1"],
            ipv6_list=[],
            key_list=[],
        )
        self.assertEqual(res[0]["ip"], "10.0.0.1")
        create_host(1, bk_host_id=1001, ip="10.0.0.2", bk_cloud_id=0)
        models.Host.objects.filter(bk_host_id=1001).update(inner_ipv6="0000:0000:0000:0000:0000:ffff:0a00:0002")
        res = HostHandler.check(
            scope_list=[{"scope_type": "biz", "scope_id": f"{i}", "bk_biz_id": i} for i in range(27, 40)],
            limit_host_ids=None,
            ip_list=[],
            ipv6_list=["0000:0000:0000:0000:0000:ffff:0a00:0002"],
            key_list=[],
        )
        self.assertEqual(res[0]["ipv6"], "0000:0000:0000:0000:0000:ffff:0a00:0002")
        res = HostHandler.check(
            scope_list=[{"scope_type": "biz", "scope_id": f"{i}", "bk_biz_id": i} for i in range(27, 40)],
            limit_host_ids=None,
            ip_list=[],
            ipv6_list=["0:[0000:0000:0000:0000:0000:ffff:0a00:0002]"],
            key_list=[],
        )
        self.assertEqual(res[0]["ipv6"], "0000:0000:0000:0000:0000:ffff:0a00:0002")
