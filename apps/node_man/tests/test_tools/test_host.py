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
from unittest import TestCase

from apps.node_man.tests.utils import random_ip
from apps.node_man.tools import HostTools


class HostToolsTestCase(TestCase):
    CIPHER = HostTools.get_asymmetric_cipher()

    def test_decrypt_without_encrypt_passwd(self):
        base_encrypt_message = random_ip()
        self.assertEqual(
            base_encrypt_message,
            HostTools.decrypt_with_friendly_exc_handle(
                cipher=self.CIPHER, encrypt_message=base_encrypt_message, raise_exec=Exception
            ),
        )

    def test_decrypt_encrypt_passwd_failed(self):
        base_encrypt_message = HostTools.USE_ASYMMETRIC_PREFIX + random_ip()
        self.assertRaises(
            Exception, HostTools.decrypt_with_friendly_exc_handle, self.CIPHER, base_encrypt_message, Exception
        )

    def test_recursion_decrypt_passwd(self):
        base_encrypt_message = random_ip()
        pre_encrypt_message = self.CIPHER.encrypt(base_encrypt_message)

        for _ in range(4):
            encrypt_message = self.CIPHER.encrypt(HostTools.USE_ASYMMETRIC_PREFIX + pre_encrypt_message)
            pre_encrypt_message = encrypt_message

        recursion_encrypt_message = HostTools.USE_ASYMMETRIC_PREFIX + pre_encrypt_message

        decrypt_message = HostTools.decrypt_with_friendly_exc_handle(
            cipher=self.CIPHER, encrypt_message=recursion_encrypt_message, raise_exec=Exception
        )

        self.assertEqual(base_encrypt_message, decrypt_message)

    def test_recursion_decrypt_passwd_failed(self):
        base_encrypt_message = random_ip()
        pre_encrypt_message = base_encrypt_message

        for _ in range(10):
            encrypt_message = self.CIPHER.encrypt(HostTools.USE_ASYMMETRIC_PREFIX + pre_encrypt_message)
            pre_encrypt_message = encrypt_message

        recursion_encrypt_message = HostTools.USE_ASYMMETRIC_PREFIX + pre_encrypt_message

        self.assertRaises(
            Exception, HostTools.decrypt_with_friendly_exc_handle, self.CIPHER, recursion_encrypt_message, Exception
        )
