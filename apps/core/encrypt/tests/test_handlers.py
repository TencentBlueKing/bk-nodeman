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
from bkcrypto.constants import AsymmetricCipherType
from bkcrypto.contrib.django.settings import crypto_settings

from apps.utils.unittest import testcase

from .. import constants, handlers, models
from . import utils


class AsymmetricHandlerTestCase(testcase.CustomBaseTestCase):

    OVERWRITE_OBJ__KV_MAP = {crypto_settings: {"ASYMMETRIC_CIPHER_TYPE": AsymmetricCipherType.RSA.value}}

    def test_get_or_generate_rsa_in_db__del_private(self):
        """
        验证单方面删除私钥的逻辑：会重建公私钥
        :return:
        """
        key_name = constants.InternalAsymmetricKeyNameEnum.DEFAULT.value
        original_gen_result = handlers.AsymmetricHandler.get_or_generate_key_pair_in_db(key_name)
        models.AsymmetricKey.objects.get(name=key_name, type=constants.AsymmetricKeyType.PRIVATE_KEY.value).delete()

        current_gen_result = handlers.AsymmetricHandler.get_or_generate_key_pair_in_db(key_name)
        for rsa_key_name in ["private_key", "public_key"]:
            self.assertTrue(current_gen_result[rsa_key_name].content != original_gen_result[rsa_key_name].content)
        utils.validate_cipher(current_gen_result["cipher"])

    def test_get_or_generate_rsa_in_db__del_public(self):
        """
        验证单方面删除公钥：重建公钥
        :return:
        """
        key_name = constants.InternalAsymmetricKeyNameEnum.DEFAULT.value
        original_gen_result = handlers.AsymmetricHandler.get_or_generate_key_pair_in_db(key_name)
        models.AsymmetricKey.objects.get(name=key_name, type=constants.AsymmetricKeyType.PUBLIC_KEY.value).delete()

        current_gen_result = handlers.AsymmetricHandler.get_or_generate_key_pair_in_db(key_name)
        self.assertTrue(current_gen_result["private_key"].content == original_gen_result["private_key"].content)
        self.assertTrue(current_gen_result["public_key"].id != original_gen_result["public_key"].id)
        utils.validate_cipher(current_gen_result["cipher"])


class ShangMiTestCase(AsymmetricHandlerTestCase):

    OVERWRITE_OBJ__KV_MAP = {crypto_settings: {"ASYMMETRIC_CIPHER_TYPE": AsymmetricCipherType.SM2.value}}
