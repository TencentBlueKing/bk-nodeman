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

from django.test import TestCase

from blueking.component import collections
from blueking.component.client import BaseComponentClient, ComponentClientWithSignature
from blueking.tests.utils.utils import tests_settings as TS  # noqa


class TestBaseComponentClient(TestCase):
    @classmethod
    def setUpTestData(cls):  # noqa
        cls.ComponentClient = BaseComponentClient
        cls.ComponentClient.setup_components(collections.AVAILABLE_COLLECTIONS)

    def test_api_get(self):
        client = self.ComponentClient(
            TS["valid_app"]["bk_app_code"],
            TS["valid_app"]["bk_app_secret"],
            common_args={
                "bk_username": TS["bk_user"]["bk_username"],
            },
        )
        result = client.bk_login.get_user()
        self.assertTrue(result["result"], json.dumps(result))
        self.assertTrue(result["data"]["bk_username"], TS["bk_user"]["bk_username"])

    def test_api_post(self):
        client = self.ComponentClient(
            TS["valid_app"]["bk_app_code"],
            TS["valid_app"]["bk_app_secret"],
            common_args={
                "bk_username": TS["bk_user"]["bk_username"],
            },
        )
        result = client.bk_login.get_batch_users({"bk_username_list": [TS["bk_user"]["bk_username"]]})
        self.assertTrue(result["result"], json.dumps(result))
        self.assertTrue(result["data"][TS["bk_user"]["bk_username"]]["bk_username"], TS["bk_user"]["bk_username"])

    def test_set_bk_api_ver(self):
        client = self.ComponentClient(
            TS["valid_app"]["bk_app_code"],
            TS["valid_app"]["bk_app_secret"],
            common_args={
                "bk_username": TS["bk_user"]["bk_username"],
            },
        )
        client.set_bk_api_ver("")
        result = client.bk_login.get_user({"username": TS["bk_user"]["bk_username"]})
        self.assertTrue(result["result"], json.dumps(result))
        self.assertTrue(result["data"]["username"], TS["bk_user"]["bk_username"])


class TestComponentClientWithSignature(TestCase):
    @classmethod
    def setUpTestData(cls):  # noqa
        cls.ComponentClient = ComponentClientWithSignature
        cls.ComponentClient.setup_components(collections.AVAILABLE_COLLECTIONS)

    def test_api(self):
        client = self.ComponentClient(
            TS["valid_app"]["bk_app_code"],
            TS["valid_app"]["bk_app_secret"],
            common_args={
                "bk_username": TS["bk_user"]["bk_username"],
            },
        )
        result = client.bk_login.get_user()
        self.assertTrue(result["result"], json.dumps(result))
        self.assertTrue(result["data"]["bk_username"], TS["bk_user"]["bk_username"])

    def test_api_post(self):
        client = self.ComponentClient(
            TS["valid_app"]["bk_app_code"],
            TS["valid_app"]["bk_app_secret"],
            common_args={
                "bk_username": TS["bk_user"]["bk_username"],
            },
        )
        result = client.bk_login.get_batch_users({"bk_username_list": [TS["bk_user"]["bk_username"]]})
        self.assertTrue(result["result"], json.dumps(result))
        self.assertTrue(result["data"][TS["bk_user"]["bk_username"]]["bk_username"], TS["bk_user"]["bk_username"])
