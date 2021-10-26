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
from apps.core.encrypt import constants as core_encrypt_constants
from apps.core.encrypt import handlers as core_encrypt_handlers
from apps.utils.encrypt import rsa


class HostTools:
    @classmethod
    def get_rsa_util(cls) -> rsa.RSAUtil:
        """
        获取用于处理Agent、主机等敏感信息的非对称加密工具类
        此处作用主要是固定指定数据源所使用的密钥名称，减少多处加解密导致密钥使用分散
        :return:
        """
        return core_encrypt_handlers.RSAHandler.get_or_generate_rsa_in_db(
            name=core_encrypt_constants.InternalRSAKeyNameEnum.DEFAULT.value
        )["rsa_util"]
