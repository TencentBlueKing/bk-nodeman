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
from typing import Any, Dict, List, Optional, Set, Union

from bkcrypto.asymmetric.ciphers.base import BaseAsymmetricCipher
from bkcrypto.contrib.django.ciphers import get_asymmetric_cipher
from bkcrypto.contrib.django.settings import crypto_settings
from django.db import transaction

from . import constants, models


class AsymmetricHandler:
    @classmethod
    def get_or_generate_key_pair_in_db(
        cls, name: str, description: Optional[str] = None
    ) -> Dict[str, Union[models.RSAKey, BaseAsymmetricCipher]]:
        """
        获取或生成非对称加密的私钥/密钥到DB
        :param name: 密钥名称
        :param description: 密钥描述
        :return:
        """

        # 优先使用常量中定义的密钥描述
        description = constants.InternalAsymmetricKeyNameEnum.get_member_value__alias_map().get(name) or description
        # description = None 视为不更新该字段
        base_info = {"description": description} if description else {}

        try:
            private_key = models.RSAKey.objects.get(
                name=name,
                type=constants.AsymmetricKeyType.PRIVATE_KEY.value,
                cipher_type=crypto_settings.ASYMMETRIC_CIPHER_TYPE,
            )

            cipher: BaseAsymmetricCipher = get_asymmetric_cipher(common={"private_key_string": private_key.content})

            # 如果获取到了私钥，此时根据私钥生成或更新公钥
            public_key, __ = models.RSAKey.objects.update_or_create(
                name=name,
                type=constants.AsymmetricKeyType.PUBLIC_KEY.value,
                cipher_type=crypto_settings.ASYMMETRIC_CIPHER_TYPE,
                defaults={**base_info, "content": cipher.export_public_key()},
            )

        except models.RSAKey.DoesNotExist:
            # 私钥不存在的情况下，重新生成
            cipher: BaseAsymmetricCipher = get_asymmetric_cipher()
            # 公私钥的更新需保证原子性
            with transaction.atomic():
                private_key = models.RSAKey.objects.create(
                    name=name,
                    type=constants.AsymmetricKeyType.PRIVATE_KEY.value,
                    cipher_type=crypto_settings.ASYMMETRIC_CIPHER_TYPE,
                    description=description,
                    content=cipher.export_private_key(),
                )
                public_key, __ = models.RSAKey.objects.update_or_create(
                    name=name,
                    type=constants.AsymmetricKeyType.PUBLIC_KEY.value,
                    cipher_type=crypto_settings.ASYMMETRIC_CIPHER_TYPE,
                    defaults={**base_info, "content": cipher.export_public_key()},
                )

        return {"cipher": cipher, "private_key": private_key, "public_key": public_key}

    @classmethod
    def fetch_public_keys(cls, names: List[str]) -> List[Dict[str, Any]]:
        """
        获取公钥列表，不支持模糊查询
        :param names: 公钥名称列表
        :return:
        """
        public_key_details: List[Dict[str, Any]] = models.RSAKey.objects.filter(
            type=constants.AsymmetricKeyType.PUBLIC_KEY.value,
            name__in=set(names),
            cipher_type=crypto_settings.ASYMMETRIC_CIPHER_TYPE,
        ).values("name", "description", "content", "cipher_type")

        hit_internal_key_names: Set[str] = set()
        public_key_infos: List[Dict[str, Any]] = []
        for public_key_detail in public_key_details:
            public_key_infos.append(public_key_detail)
            hit_internal_key_names.add(public_key_detail["name"])

        # 如果请求的内部密钥不存在，生成后返回
        query_internal_key_names = {
            name for name in names if name in constants.InternalAsymmetricKeyNameEnum.list_member_values()
        }
        internal_key_names_to_be_created = query_internal_key_names - hit_internal_key_names

        for name in internal_key_names_to_be_created:

            generate_result = cls.get_or_generate_key_pair_in_db(name=name)

            cipher: BaseAsymmetricCipher = generate_result["cipher"]
            public_key: models.RSAKey = cls.get_or_generate_key_pair_in_db(name=name)["public_key"]
            public_key_infos.append(
                {
                    "name": public_key.name,
                    "description": public_key.description,
                    "content": public_key.content,
                    "cipher_type": public_key.cipher_type,
                    "block_size": cipher.get_block_size(cipher.config.public_key, is_encrypt=True),
                }
            )

        for public_key_info in public_key_infos:
            if "block_size" not in public_key_info:
                cipher: BaseAsymmetricCipher = get_asymmetric_cipher(
                    common={"public_key_string": public_key_info["content"]}
                )
                public_key_info["block_size"] = cipher.get_block_size(cipher.config.public_key, is_encrypt=True)
        return public_key_infos
