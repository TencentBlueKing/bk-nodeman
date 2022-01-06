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
import base64
from unittest.mock import patch

from Crypto.Cipher import AES

from apps.node_man.handlers.tjj import TjjHandler
from apps.utils.unittest.testcase import CustomBaseTestCase

# 保证salt为8字符且msg为16字符整数倍
salt = b"superman"
msg = b"I am so happy!!" + bytes(chr(1).encode())


def get_cipher_text():
    key, iv = TjjHandler().get_key_and_iv(salt)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    # 构造加密文本
    cipher_text = cipher.encrypt(msg)
    cipher_text = b"Salted__" + salt + cipher_text
    cipher_text = base64.b64encode(cipher_text)

    return cipher_text


class requests:
    class post:
        def __init__(self, url, data, headers):
            self.url = url
            self.data = data
            self.headers = headers

        def json(self):
            return_value = {
                "result": True,
                "data": {
                    "HasError": 0,
                    "ResponseItems": {"IpList": {"127.0.0.1": {"Code": 0, "Password": get_cipher_text()}}},
                },
            }
            return return_value


class TestTJJ(CustomBaseTestCase):
    @patch("apps.node_man.handlers.tjj.requests", requests)
    def test_fetch_pwd(self):
        # 第一个分支
        result = TjjHandler().fetch_pwd("admin", ["127.0.0.1"], "ticket")
        self.assertEqual(result["code"], 0)
