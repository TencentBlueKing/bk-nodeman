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
import random

from bkcrypto.asymmetric.ciphers import BaseAsymmetricCipher


def validate_cipher(cipher: BaseAsymmetricCipher):
    passwords = ["测试密码1", "123A", "1" * random.randint(400, 1000), "测" * random.randint(200, 400), ""]
    for password in passwords:
        assert cipher.decrypt(cipher.encrypt(password)) == password
