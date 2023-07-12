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
from typing import Type

from bkcrypto.asymmetric.ciphers import BaseAsymmetricCipher
from django.utils.translation import ugettext_lazy as _

from apps.core.encrypt import constants as core_encrypt_constants
from apps.core.encrypt import handlers as core_encrypt_handlers


class HostTools:
    ASYMMETRIC_KEY_NAME: str = core_encrypt_constants.InternalAsymmetricKeyNameEnum.DEFAULT.value
    USE_ASYMMETRIC_PREFIX: str = base64.b64encode(ASYMMETRIC_KEY_NAME.encode()).decode()

    @classmethod
    def get_asymmetric_cipher(cls) -> BaseAsymmetricCipher:
        """
        获取用于处理Agent、主机等敏感信息的非对称加密工具类
        此处作用主要是固定指定数据源所使用的密钥名称，减少多处加解密导致密钥使用分散
        :return:
        """

        return core_encrypt_handlers.AsymmetricHandler.get_or_generate_key_pair_in_db(
            name=core_encrypt_constants.InternalAsymmetricKeyNameEnum.DEFAULT.value
        )["cipher"]

    @classmethod
    def decrypt_with_friendly_exc_handle(
        cls, cipher: BaseAsymmetricCipher, encrypt_message: str, raise_exec: Type[Exception]
    ) -> str:
        """
        解密友好提示处理
        :param cipher: 密码器
        :param encrypt_message:
        :param raise_exec:
        :return:
        """

        # 如果不存在加密标识前缀，识别为明文密码并直接传递
        if not encrypt_message.startswith(cls.USE_ASYMMETRIC_PREFIX):
            return encrypt_message

        encrypt_message: str = encrypt_message[len(cls.USE_ASYMMETRIC_PREFIX) :]
        try:
            decrypt_message: str = cipher.decrypt(encrypt_message)
        except ValueError as e:
            raise raise_exec(_("密文无法解密，请检查是否按规则使用密钥加密：{err_msg}").format(err_msg=e))
        except Exception as e:
            raise raise_exec(_("密文解密失败：{err_msg").format(err_msg=e))

        # 递归解密
        return cls.decrypt_with_friendly_exc_handle(
            cipher=cipher, encrypt_message=decrypt_message, raise_exec=raise_exec
        )
