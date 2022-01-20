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

from apps.node_man.handlers.ap import APHandler
from apps.node_man.models import AccessPoint
from apps.node_man.tests.utils import create_ap, mock_read_remote_file_content


class TestAP(TestCase):
    def test_ap_list(self):
        number = 3
        create_ap(number)
        ap_ids = AccessPoint.objects.all().values_list("id", flat=True)
        result = APHandler().ap_list(ap_ids)
        self.assertEqual(number, len(result))

    @patch("apps.node_man.handlers.ap.read_remote_file_content", mock_read_remote_file_content)
    def test_init_plugin_data(self):
        create_ap(1)
        result = APHandler().init_plugin_data("admin")
        self.assertEqual(result[0]["gseplugindesc"]["name"], "basereport")
        result = APHandler().init_plugin_data("admin", ap_id=1)
        self.assertEqual(result[0]["gseplugindesc"]["name"], "basereport")

    def test_init(self):
        data = {
            "gseplugindesc": {"id": 1, "name": "basereport"},
            "packages": {
                "id": 1,
                "module": "gse_plugin",
                "project": "basereport",
                "version": "latest",
                "os": "linux",
                "cpu_arch": "x86_64",
                "pkg_size": 2,
            },
            "proccontrol": {"id": 1, "module": "gse_plugin", "project": "basereport", "os": "linux"},
        }
        result = APHandler()._init(data)
        self.assertEqual(result["gseplugindesc"]["name"], "basereport")
