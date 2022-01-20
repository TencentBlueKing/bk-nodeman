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
import json

from django.test import RequestFactory, TestCase

from blueking.component.shortcuts import get_client_by_request, get_client_by_user
from blueking.tests.utils.utils import get_user_model
from blueking.tests.utils.utils import tests_settings as TS  # noqa


class TestShortcuts(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user_model = get_user_model()

    def test_get_client_by_request(self):
        request = self.factory.get("/")
        request.user = self.user_model(username=TS["bk_user"]["bk_username"])
        request.COOKIES = {"bk_token": TS["bk_user"]["bk_token"]}

        client = get_client_by_request(request)
        result = client.bk_login.get_user()
        self.assertTrue(result["result"], json.dumps(result))
        self.assertEqual(result["data"]["bk_username"], TS["bk_user"]["bk_username"])

    def test_get_client_by_user(self):
        user = self.user_model(username=TS["bk_user"]["bk_username"])
        client = get_client_by_user(user)
        result = client.bk_login.get_user()
        self.assertTrue(result["result"], json.dumps(result))
        self.assertEqual(result["data"]["bk_username"], TS["bk_user"]["bk_username"])

        client = get_client_by_user(TS["bk_user"]["bk_username"])
        result = client.bk_login.get_user()
        self.assertTrue(result["result"], json.dumps(result))
        self.assertEqual(result["data"]["bk_username"], TS["bk_user"]["bk_username"])
