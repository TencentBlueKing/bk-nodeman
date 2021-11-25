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
from typing import Any, Dict, List, Optional, Set, Union

from django.db import transaction

from apps.utils.encrypt import rsa

from . import constants, models


class RSAHandler:
    @classmethod
    def get_or_generate_rsa_in_db(
        cls, name: str, description: Optional[str] = None, return_rsa_util: bool = True
    ) -> Dict[str, Union[models.RSAKey, Optional[rsa.RSAUtil]]]:
        """
        获取或生成非对称加密的私钥/密钥到DB
        :param name: 密钥名称
        :param description: 密钥描述
        :param return_rsa_util: 是否返回工具对象
        :return:
        """

        # 优先使用常量中定义的密钥描述
        description = constants.InternalRSAKeyNameEnum.get_member_value__alias_map().get(name) or description
        # description = None 视为不更新该字段
        base_info = {"description": description} if description else {}

        try:
            rsa_private_key = models.RSAKey.objects.get(name=name, type=constants.RSAKeyType.PRIVATE_KEY.value)

            # 如果获取到了私钥，此时根据私钥生成或更新公钥
            private_key_obj = rsa.RSAUtil.load_key(extern_key=rsa_private_key.content)
            rsa_public_key, __ = models.RSAKey.objects.update_or_create(
                name=name,
                type=constants.RSAKeyType.PUBLIC_KEY.value,
                defaults={**base_info, "content": private_key_obj.publickey().exportKey().decode("utf-8")},
            )

        except models.RSAKey.DoesNotExist:
            private_key, public_key = rsa.generate_keys()
            # 公私钥的更新需保证原子性
            with transaction.atomic():
                rsa_private_key = models.RSAKey.objects.create(
                    name=name, type=constants.RSAKeyType.PRIVATE_KEY.value, description=description, content=private_key
                )
                rsa_public_key, __ = models.RSAKey.objects.update_or_create(
                    name=name, type=constants.RSAKeyType.PUBLIC_KEY.value, defaults={**base_info, "content": public_key}
                )

        rsa_util = None
        if return_rsa_util:
            rsa_util = rsa.RSAUtil(public_extern_key=rsa_public_key.content, private_extern_key=rsa_private_key.content)

        return {"rsa_util": rsa_util, "rsa_private_key": rsa_private_key, "rsa_public_key": rsa_public_key}

    @classmethod
    def fetch_public_keys(cls, names: List[str]) -> List[Dict[str, Any]]:
        """
        获取公钥列表，不支持模糊查询
        :param names: 公钥名称列表
        :return:
        """
        rsa_public_key_details: List[Dict[str, Any]] = models.RSAKey.objects.filter(
            type=constants.RSAKeyType.PUBLIC_KEY.value, name__in=set(names)
        ).values("name", "description", "content")

        hit_internal_rsa_key_names: Set[str] = set()
        public_key_infos: List[Dict[str, Any]] = []
        for rsa_public_key_detail in rsa_public_key_details:
            public_key_infos.append(rsa_public_key_detail)
            hit_internal_rsa_key_names.add(rsa_public_key_detail["name"])

        # 如果请求的内部密钥不存在，生成后返回
        query_internal_rsa_key_names = {
            name for name in names if name in constants.InternalRSAKeyNameEnum.list_member_values()
        }
        internal_rsa_key_names_to_be_created = query_internal_rsa_key_names - hit_internal_rsa_key_names

        for name in internal_rsa_key_names_to_be_created:
            rsa_public_key = cls.get_or_generate_rsa_in_db(name=name, return_rsa_util=False)["rsa_public_key"]
            public_key_infos.append(
                {
                    "name": rsa_public_key.name,
                    "description": rsa_public_key.description,
                    "content": rsa_public_key.content,
                }
            )

        for public_key_info in public_key_infos:
            public_key_obj = rsa.RSAUtil.load_key(public_key_info["content"])
            public_key_info["block_size"] = rsa.RSAUtil.get_block_size(public_key_obj)
        return public_key_infos
