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

from .. import constants, handlers
from . import utils


class RSAViewSetTestCase(testcase.CustomAPITestCase):
    def test_fetch_public_keys(self):
        external_rsa_name = "EXTERNAL"
        fetch_names = [constants.InternalRSAKeyNameEnum.DEFAULT.value, external_rsa_name]
        handlers.RSAHandler.get_or_generate_rsa_in_db(external_rsa_name, description="外部密钥")
        public_keys = self.client.post(path="/core/api/encrypt_rsa/fetch_public_keys/", data={"names": fetch_names})[
            "data"
        ]
        self.assertEqual(len(public_keys), len(fetch_names))

        key_name__item_map = {public_key["name"]: public_key for public_key in public_keys}
        default_public_key_content = key_name__item_map[constants.InternalRSAKeyNameEnum.DEFAULT.value]["content"]

        # 验证取得的密钥可正常加解密
        result = handlers.RSAHandler.get_or_generate_rsa_in_db(name=constants.InternalRSAKeyNameEnum.DEFAULT.value)
        self.assertEqual(result["rsa_public_key"].content, default_public_key_content)
        utils.validate_rsa_util(rsa_util=result["rsa_util"])
