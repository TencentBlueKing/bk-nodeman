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
import os

from django.conf import settings

# 默认过期时间, 24小时
DEFAULT_EXPIRES_SECONDS = 60 * 60 * 24

APP_CODE = getattr(settings, "APP_CODE", None)
SECRET_KEY = getattr(settings, "SECRET_KEY", None)
RUN_MODE = getattr(settings, "RUN_MODE", "DEVELOP")
APIGW_PUBLIC_KEY = getattr(settings, "APIGW_PUBLIC_KEY", "")
# 过期时间
EXPIRES_SECONDS = getattr(settings, "EXPIRES_SECONDS", DEFAULT_EXPIRES_SECONDS)

# env
ENV_NAME = "prod" if RUN_MODE == "PRODUCT" else "test"

# OAuth API地址
# 从环境变量中获取
__OAUTH_API_URL_ENV = os.environ.get("OAUTH_API_URL", "")
# 从Django配置项中获取
__OAUTH_API_URL_DJ = getattr(settings, "OAUTH_API_URL", "")
OAUTH_API_URL = __OAUTH_API_URL_ENV or __OAUTH_API_URL_DJ

# OAuth从cookies获得参数
# 从环境变量中获取
try:
    __OAUTH_COOKIES_PARAMS_ENV = json.loads(os.environ.get("OAUTH_COOKIES_PARAMS", "{}"))
except Exception:
    __OAUTH_COOKIES_PARAMS_ENV = {}
# 从Django配置项中获取
__OAUTH_COOKIES_PARAMS_DJ = getattr(settings, "OAUTH_COOKIES_PARAMS", {})
OAUTH_COOKIES_PARAMS = __OAUTH_COOKIES_PARAMS_ENV or __OAUTH_COOKIES_PARAMS_DJ

# OAuth其他参数
# 从环境变量中获取
try:
    __OAUTH_OAUTH_PARAMS_ENV = json.loads(os.environ.get("OAUTH_PARAMS", "{}"))
except Exception:
    __OAUTH_OAUTH_PARAMS_ENV = {}
# 从Django配置项中获取
__OAUTH_OAUTH_PARAMS_DJ = getattr(settings, "OAUTH_PARAMS", {})
OAUTH_PARAMS = __OAUTH_OAUTH_PARAMS_ENV or __OAUTH_OAUTH_PARAMS_DJ

IS_BKOAUTH_IN_INSTALLED_APPS = "bkoauth" in settings.INSTALLED_APPS

# OAuth 申请或刷新 token 时，是否需要新的 token
OAUTH_NEED_NEW_TOKEN = getattr(settings, "OAUTH_NEED_NEW_TOKEN", True)
