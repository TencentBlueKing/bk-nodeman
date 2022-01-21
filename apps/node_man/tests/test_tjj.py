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
import base64
import typing
from unittest.mock import patch

from Crypto.Cipher import AES

from apps.node_man.handlers import password
from apps.utils.unittest.testcase import CustomBaseTestCase

# 保证salt为8字符且msg为16字符整数倍
salt = b"superman"
msg = b"I am so happy!!" + bytes(chr(1).encode())


def get_cipher_text():
    key, iv = password.DefaultPasswordHandler().get_key_and_iv(salt)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    # 构造加密文本
    cipher_text = cipher.encrypt(msg)
    cipher_text = b"Salted__" + salt + cipher_text
    cipher_text = base64.b64encode(cipher_text)

    return cipher_text


DEFAULT_MOCK_DATA = {
    "result": True,
    "data": {
        "HasError": 0,
        "ResponseItems": {"IpList": {"127.0.0.1": {"Code": 0, "Password": get_cipher_text()}}},
    },
}

TJJ_MOCK_DATA = {
    "Result": {
        "HasError": False,
        "ResponseItems": {"IpList": {"127.0.0.1": {"Code": 0, "Password": get_cipher_text()}}},
    }
}


def get_mock_requests(mock_data: typing.Dict[str, typing.Any]):
    class requests:
        class post:
            def __init__(self, url, data, headers=None):
                self.url = url
                self.data = data
                self.headers = headers

            def json(self):
                return mock_data

    return requests


class TestDefaultPasswordHandler(CustomBaseTestCase):
    @patch("apps.node_man.handlers.password.requests", get_mock_requests(DEFAULT_MOCK_DATA))
    def test_fetch_pwd(self):
        # 第一个分支
        result = password.DefaultPasswordHandler().fetch_pwd("admin", ["127.0.0.1"], ticket="ticket")
        self.assertEqual(result["code"], 0)


class TestTjjPasswordHandler(CustomBaseTestCase):
    @patch("apps.node_man.handlers.password.requests", get_mock_requests(TJJ_MOCK_DATA))
    def test_get_password(self):
        # 第一个分支
        is_ok, success_ips, failed_ips, err_msg = password.TjjPasswordHandler().get_password("admin", ["0-127.0.0.1"])
        self.assertTrue(is_ok)
        self.assertEqual(failed_ips, {})
        self.assertTrue(len(success_ips.items()))

    @patch("apps.node_man.handlers.password.requests", get_mock_requests(TJJ_MOCK_DATA))
    def test_fetch_pwd(self):
        # 第一个分支
        result = password.TjjPasswordHandler().fetch_pwd("admin", ["127.0.0.1"])
        self.assertEqual(result["code"], 0)
