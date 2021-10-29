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

from apps.utils.unittest import testcase

from .. import constants, handlers, models
from . import utils


class RSAHandlerTestCase(testcase.CustomBaseTestCase):
    def test_get_or_generate_rsa_in_db__del_private(self):
        """
        验证单方面删除私钥的逻辑：会重建公私钥
        :return:
        """
        rsa_name = constants.InternalRSAKeyNameEnum.DEFAULT.value
        original_gen_result = handlers.RSAHandler.get_or_generate_rsa_in_db(rsa_name)
        models.RSAKey.objects.get(name=rsa_name, type=constants.RSAKeyType.PRIVATE_KEY.value).delete()

        current_gen_result = handlers.RSAHandler.get_or_generate_rsa_in_db(rsa_name)
        for rsa_key_name in ["rsa_private_key", "rsa_public_key"]:
            self.assertTrue(current_gen_result[rsa_key_name].content != original_gen_result[rsa_key_name].content)
        utils.validate_rsa_util(current_gen_result["rsa_util"])

    def test_get_or_generate_rsa_in_db__del_public(self):
        """
        验证单方面删除公钥：重建公钥
        :return:
        """
        rsa_name = constants.InternalRSAKeyNameEnum.DEFAULT.value
        original_gen_result = handlers.RSAHandler.get_or_generate_rsa_in_db(rsa_name)
        models.RSAKey.objects.get(name=rsa_name, type=constants.RSAKeyType.PUBLIC_KEY.value).delete()

        current_gen_result = handlers.RSAHandler.get_or_generate_rsa_in_db(rsa_name)
        self.assertTrue(current_gen_result["rsa_private_key"].content == original_gen_result["rsa_private_key"].content)
        self.assertTrue(current_gen_result["rsa_public_key"].id != original_gen_result["rsa_public_key"].id)
        utils.validate_rsa_util(current_gen_result["rsa_util"])
