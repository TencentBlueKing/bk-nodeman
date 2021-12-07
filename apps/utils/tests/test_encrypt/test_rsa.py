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
import random

from ...encrypt import rsa
from ...unittest import testcase


class RsaTestCase(testcase.CustomBaseTestCase):
    @staticmethod
    def get_rsa_util():
        private_key, public_key = rsa.generate_keys()
        return rsa.RSAUtil(public_extern_key=public_key, private_extern_key=private_key)

    def test_rsa_util__encrypt(self):
        rsa_util = self.get_rsa_util()
        passwords = ["测试密码1", "123A", "1" * random.randint(400, 1000), "测" * random.randint(200, 400), ""]
        for password in passwords:
            self.assertEqual(rsa_util.decrypt(rsa_util.encrypt(password)), password)

    def test_rsa_util__verify(self):
        rsa_util = self.get_rsa_util()
        message = "验证私钥签名，如果验证结果为True，表明该消息从私钥拥有方发出，没有被修改"
        signature = rsa_util.sign(message=message)
        self.assertTrue(rsa_util.verify(message=message, signature=signature))

    def test_key_obj_check_failed(self):
        self.assertRaises(ValueError, rsa.RSAUtil().encrypt, "test")
