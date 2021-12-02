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
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from ..base import BaseApi, DataAPI
from ..domains import ESB_APIGATEWAY_ROOT_V2


def add_params_before_request(params):
    params["bk_app_code"] = settings.APP_CODE
    params["bk_app_secret"] = settings.SECRET_KEY
    params["bk_username"] = "admin"
    return params


class _ESBApi(BaseApi):

    MODULE = _("ESB")

    def __init__(self):
        self.get_api_public_key = DataAPI(
            method="POST",
            url=ESB_APIGATEWAY_ROOT_V2 + "get_api_public_key",
            module=self.MODULE,
            description="get api public key",
            default_return_value=None,
            before_request=add_params_before_request,
            after_request=None,
        )


ESBApi = _ESBApi()
