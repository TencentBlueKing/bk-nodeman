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
import json
import sys

import requests
from django.conf import settings

from apps.utils import build_auth_args
from apps.utils.local import get_request, get_tenant_id
from common.api.domains import USER_APIGATEWAY_ROOT_V3


def get_virtual_username(tenant_id):
    """
    调用蓝鲸用户管理 API 获取虚拟用户 bk_username
    """
    from apps.node_man import models

    tenant_bk_username_map = models.GlobalSettings.get_config(
        key=models.GlobalSettings.KeyEnum.TENANT_BK_USERNAME_MAP.value, default={}
    )
    if tenant_id in tenant_bk_username_map:
        return tenant_bk_username_map[tenant_id]

    auth_data = {"bk_app_code": settings.APP_CODE, "bk_app_secret": settings.SECRET_KEY}
    response = requests.get(
        USER_APIGATEWAY_ROOT_V3 + "open/tenant/virtual-users/-/lookup/",
        headers={"X-Bkapi-Authorization": json.dumps(auth_data), "X-Bk-Tenant-Id": tenant_id},
        params={"lookup_field": "login_name", "lookups": "bk_admin"},
    )
    if response.status_code == 200:
        result = response.json()
        data_list = result.get("data", [])
        if data_list and data_list[0].get("bk_username"):
            bk_username = data_list[0]["bk_username"]
            tenant_bk_username_map[tenant_id] = bk_username
            models.GlobalSettings.update_config(
                key=models.GlobalSettings.KeyEnum.TENANT_BK_USERNAME_MAP.value, value=tenant_bk_username_map
            )
            return bk_username
    return "bk_admin"


def _clean_auth_info_uin(auth_info):
    if "uin" in auth_info:
        # 混合云uin去掉第一位
        if auth_info["uin"].startswith("o"):
            auth_info["uin"] = auth_info["uin"][1:]
    return auth_info


IS_BACKEND = False
for argv in sys.argv:
    if "celery" in argv:
        IS_BACKEND = True
        break
    if "manage.py" in argv and "runserver" not in sys.argv:
        IS_BACKEND = True

# 后台任务 & 测试任务调用 ESB 接口不需要用户权限控制
if IS_BACKEND:

    def add_esb_info_before_request(params):
        # 默认填充当前环境的app code和secret，部分场景需调用另外一套蓝鲸环境的API，则在参数中指定
        if "bk_app_code" not in params:
            params["bk_app_code"] = settings.APP_CODE
        if "bk_app_secret" not in params:
            params["bk_app_secret"] = settings.SECRET_KEY

        if "bk_username" not in params:
            if settings.ENABLE_MULTI_TENANT_MODE:
                params["bk_username"] = get_virtual_username(get_tenant_id())
            else:
                params["bk_username"] = "admin"

        params.pop("_request", None)
        return params


# 正常 WEB 请求所使用的函数
else:

    def add_esb_info_before_request(params):
        """
        通过 params 参数控制是否检查 request

        @param {Boolean} [params.no_request] 是否需要带上 request 标识
        """
        if "bk_app_code" not in params:
            params["bk_app_code"] = settings.APP_CODE
        if "bk_app_secret" not in params:
            params["bk_app_secret"] = settings.SECRET_KEY

        if "no_request" in params and params["no_request"]:
            if settings.ENABLE_MULTI_TENANT_MODE:
                params["bk_username"] = get_virtual_username(get_tenant_id())
            else:
                params["bk_username"] = "admin"
        else:
            # _request，用于并发请求的场景
            _request = params.get("_request")
            req = _request or get_request()
            # 补充请求凭证，如bk_token
            auth_info = build_auth_args(req)
            params.update(auth_info)

            bk_username = req.user.bk_username if hasattr(req.user, "bk_username") else req.user.username
            params["bk_username"] = bk_username

        params.pop("_request", None)
        return params
