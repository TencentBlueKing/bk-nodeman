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

try:
    get_app_access_token = None
    get_access_token = None
    refresh_token = None
    get_access_token_by_user = None
except Exception:
    pass


def _init_function():
    from . import signals  # noqa
    from .client import oauth_client

    global oauth_client
    global get_app_access_token
    global get_access_token
    global refresh_token
    global get_access_token_by_user

    get_app_access_token = oauth_client.get_app_access_token
    get_access_token = oauth_client.get_access_token
    refresh_token = oauth_client.refresh_token
    get_access_token_by_user = oauth_client.get_access_token_by_user


try:
    from django.apps import AppConfig

    default_app_config = "bkoauth.BkoauthConfig"

    class BkoauthConfig(AppConfig):
        name = "bkoauth"

        def ready(self):
            _init_function()


except Exception:
    _init_function()
