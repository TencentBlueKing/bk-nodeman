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

from bkcrypto.symmetric import interceptors
from bkcrypto.symmetric.ciphers.base import BaseSymmetricCipher, EncryptionMetadata


class Interceptor(interceptors.BaseSymmetricInterceptor):
    @staticmethod
    def _pad(s):
        bs = 3
        return s + (bs - len(s) % bs) * chr(bs - len(s) % bs)

    @staticmethod
    def _unpad(s):
        return s[: -ord(s[len(s) - 1 :])]

    @classmethod
    def before_encrypt(cls, plaintext: str, **kwargs) -> str:
        return cls._pad(plaintext)

    @classmethod
    def after_decrypt(cls, plaintext: str, **kwargs) -> str:
        return cls._unpad(plaintext)

    @classmethod
    def after_encrypt(cls, ciphertext: str, **kwargs) -> str:
        cipher: BaseSymmetricCipher = kwargs["cipher"]
        ciphertext_bytes, __ = cipher.extract_encryption_metadata(ciphertext)
        return cipher.config.convertor.to_string(ciphertext_bytes)

    @classmethod
    def before_decrypt(cls, ciphertext: str, **kwargs) -> str:
        cipher: BaseSymmetricCipher = kwargs["cipher"]
        return cipher.combine_encryption_metadata(
            cipher.config.convertor.from_string(ciphertext), EncryptionMetadata(cipher.config.iv)
        )
