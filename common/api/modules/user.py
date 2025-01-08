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
from ..domains import USER_APIGATEWAY_ROOT_V3


class _UserApi(BaseApi):
    MODULE = _("用户管理")
    SIMPLE_MODULE = "USER"

    def __init__(self):
        self.list_tenant = DataAPI(
            method="GET",
            url=USER_APIGATEWAY_ROOT_V3 + "open/tenants/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询租户列表",
            api_name="list_tenant",
        )
        self.batch_query_user_display_name = DataAPI(
            method="GET",
            url=USER_APIGATEWAY_ROOT_V3 + "open/tenant/users/-/display_name/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="批量查询用户展示名",
            api_name="batch_query_user_display_name",
        )
