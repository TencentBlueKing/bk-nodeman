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

from bkcrypto.symmetric.configs import KeyConfig
from django.conf import settings


def get_key_config(cipher_type: str):
    return KeyConfig(settings.BKCRYPTO_SYMMETRIC_KEY)
    # TODO crayon - 验证这段代码是非必需后删除
    # instance_key = settings.SECRET_KEY
    #
    # if settings.BK_BACKEND_CONFIG:
    #     # 后台只作取操作不进行保存
    #     try:
    #         instance_key = GlobalSettings.objects.get(key="null").v_json
    #     except Exception as e:
    #         logger.error(_("后台获取密钥失败：{e}").format(e=e))
    #         raise QueryGlobalSettingsException()
    # else:
    #     try:
    #         obj, created = GlobalSettings.objects.get_or_create(
    #             # 存储密钥，以便于后台使用同个KEY解密
    #             key="null",
    #             defaults={"v_json": base64.b64encode(instance_key.encode()).decode()},
    #         )
    #     except Exception as e:
    #         # 初次migrate时，GlobalSettings不存在
    #         logger.error(_("SaaS获取密钥失败：{e}").format(e=e))
    #         instance_key = base64.b64encode(instance_key.encode()).decode()
    #     else:
    #         instance_key = obj.v_json
    #
    # return KeyConfig(key=instance_key)
