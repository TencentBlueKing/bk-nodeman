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
from ..domains import APIGATEWAY_ROOT


class _GatewayApi(BaseApi):
    MODULE = _("网关")
    SIMPLE_MODULE = "GATEWAY"

    def __init__(self):
        self.get_apigw_public_key = DataAPI(
            method="GET",
            url=APIGATEWAY_ROOT + "api/v1/apis/{api_name}/public_key/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="获取网关公钥",
            api_name="get_apigw_public_key",
        )
