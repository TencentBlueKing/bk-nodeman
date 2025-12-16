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
from django.utils.translation import gettext_lazy as _

from ..base import BaseApi, DataAPI
from ..domains import LOGIN_APIGATEWAY_ROOT_V3


class _LoginApi(BaseApi):
    MODULE = _("登录")
    SIMPLE_MODULE = "LOGIN"

    def __init__(self):
        self.get_bk_token_userinfo = DataAPI(
            method="GET",
            url=LOGIN_APIGATEWAY_ROOT_V3 + "open/bk-tokens/userinfo/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询 bk_token 对应的用户信息",
            api_name="get_bk_token_userinfo",
        )
