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
from typing import Optional, Tuple, Union

from Cryptodome.Cipher import PKCS1_v1_5 as PKCS1_v1_5_cipher
from Cryptodome.Hash import SHA
from Cryptodome.PublicKey import RSA
from Cryptodome.PublicKey.RSA import RsaKey
from Cryptodome.Signature import PKCS1_v1_5


def generate_keys() -> Tuple[str, str]:
    private_key_obj = RSA.generate(2048)
    private_key = private_key_obj.exportKey()
    public_key = private_key_obj.publickey().exportKey()
    return private_key.decode("utf-8"), public_key.decode("utf-8")


class RSAUtil:
    public_key_obj: RsaKey = None
    private_key_obj: RsaKey = None

    @staticmethod
    def load_key(extern_key: Optional[Union[str, bytes]] = None, extern_key_file: Optional[str] = None) -> RsaKey:
        if not (extern_key or extern_key_file):
            raise ValueError("key or key_file need to provide at least one.")

        if extern_key_file:
            try:
                with open(file=extern_key_file, mode="r") as extern_key_fs:
                    extern_key = extern_key_fs.read()
            except OSError as e:
                raise OSError(f"can't not read / open extern_key_file -> {extern_key_file}") from e

        return RSA.importKey(extern_key)

    def __init__(
        self,
        public_extern_key: Optional[Union[str, bytes]] = None,
        private_extern_key: Optional[Union[str, bytes]] = None,
        public_extern_key_file: Optional[str] = None,
        private_extern_key_file: Optional[str] = None,
    ):
        self.public_key_obj = self.load_key(public_extern_key, public_extern_key_file)
        self.private_key_obj = self.load_key(private_extern_key, private_extern_key_file)

    def encrypt(self, message: str):
        cipher = PKCS1_v1_5_cipher.new(self.public_key_obj)
        encrypt_message = base64.b64encode(cipher.encrypt(message.encode("utf-8")))
        return encrypt_message.decode("utf-8")

    def decrypt(self, encrypt_message: str) -> str:
        cipher = PKCS1_v1_5_cipher.new(self.private_key_obj)
        decrypt_message = cipher.decrypt(base64.b64decode(encrypt_message), "")
        return decrypt_message.decode("utf-8")

    def sign(self, message: str) -> bytes:
        cipher = PKCS1_v1_5.new(self.private_key_obj)
        sha = SHA.new(message)
        signature = cipher.sign(sha)
        return base64.b64encode(signature)

    def verify(self, message: str, signature: bytes):
        signature = base64.b64decode(signature)
        cipher = PKCS1_v1_5.new(self.public_key_obj)
        sha = SHA.new(message)
        return cipher.verify(sha, signature)
