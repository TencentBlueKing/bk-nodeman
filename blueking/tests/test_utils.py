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
from django.test import TestCase

from blueking.component.utils import get_signature


class TestUtils(TestCase):
    def test_get_signature(self):
        params = {
            "method": "GET",
            "path": "/blueking/component/",
            "app_secret": "test",
            "params": {"p1": 1, "p2": "abc"},
        }
        signature = get_signature(**params)
        self.assertEqual(signature, "S73XVZx3HvPRcak1z3k7jUkA7FM=")

        params = {
            "method": "POST",
            "path": "/blueking/component/",
            "app_secret": "test",
            "data": {"p1": 1, "p2": "abc"},
        }
        # python3 could sort the dict
        signature = get_signature(**params)
        self.assertIn(signature, ["qTzporCDYXqaWKuk/MNUXPT3A5U=", "PnmqLk/8PVpsLHDFkolCQoi5lmg="])
