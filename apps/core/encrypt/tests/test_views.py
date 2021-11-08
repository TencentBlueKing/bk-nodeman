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


class RSAViewSetTestCase(testcase.CustomAPITestCase):
    def test_fetch_public_keys(self):
        default_rsa_name = constants.InternalRSAKeyNameEnum.DEFAULT.value
        external_rsa_name = "EXTERNAL"
        fetch_names = [default_rsa_name, external_rsa_name]
        handlers.RSAHandler.get_or_generate_rsa_in_db(external_rsa_name, description="外部密钥")
        public_keys = self.client.post(path="/core/api/encrypt_rsa/fetch_public_keys/", data={"names": fetch_names})[
            "data"
        ]
        self.assertEqual(len(public_keys), len(fetch_names))
