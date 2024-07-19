# -*- coding: utf-8 -*-
"""
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-蓝鲸 PaaS 平台(BlueKing-PaaS) available.
 * Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at http://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
"""
import logging
from collections import namedtuple
from typing import ClassVar, Type

from django.conf import settings
from django.contrib import auth
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import AnonymousUser
from django.utils.module_loading import import_string

from apigw_manager.apigw.providers import CachePublicKeyProvider, PublicKeyProvider, SettingsPublicKeyProvider
from apigw_manager.apigw.utils import get_configuration

logger = logging.getLogger(__name__)


class JWTTokenInvalid(Exception):
    pass


class ApiGatewayJWTMiddleware:
    """
    The middleware reads the JWT header information transmitted by the API gateway,
    obtains the corresponding public key which to decrypt,
    decrypt the result to assign the value to the request.jwt.

    The algorithm that can be set by settings.APIGW_JWT_ALGORITHM,
    otherwise use the default value of the class definition

    By default, read the API gateway public key by settings.APIGW_PUBLIC_KEY.
    """

    JWT_KEY_NAME = "HTTP_X_BKAPI_JWT"
    ALGORITHM = "RS512"
    PUBLIC_KEY_PROVIDER_CLS: ClassVar[Type[PublicKeyProvider]] = SettingsPublicKeyProvider

    def __init__(self, get_response):
        self.get_response = get_response

        configuration = get_configuration()
        jwt_provider_cls = import_string(
            configuration.jwt_provider_cls or "apigw_manager.apigw.providers.DefaultJWTProvider"
        )
        self.provider = jwt_provider_cls(
            jwt_key_name=self.JWT_KEY_NAME,
            default_api_name=configuration.api_name,
            algorithm=getattr(settings, "APIGW_JWT_ALGORITHM", self.ALGORITHM),
            allow_invalid_jwt_token=getattr(settings, "APIGW_ALLOW_INVALID_JWT_TOKEN", False),
            public_key_provider=self.PUBLIC_KEY_PROVIDER_CLS(default_api_name=configuration.api_name),
        )

    def __call__(self, request):

        jwt = self.provider.provide(request)
        logger.info("apigw_manager_test:meta:{}".format(request.META))
        if not jwt:
            return self.get_response(request)

        request.jwt = jwt
        request._dont_enforce_csrf_checks = True

        return self.get_response(request)


class ApiGatewayJWTGenericMiddleware(ApiGatewayJWTMiddleware):
    """
    This middleware is similar to ApiGatewayJWTMiddleware,
    but gets the API gateway public key from Context Model.
    """

    PUBLIC_KEY_PROVIDER_CLS = CachePublicKeyProvider


class ApiGatewayJWTAppMiddleware:
    """Read the JWT information to set the request.app attribute"""

    App = namedtuple("App", ["bk_app_code", "verified"])

    def __init__(self, get_response):
        self.get_response = get_response

    def make_app(self, bk_app_code=None, verified=False, **jwt_app):
        return self.App(
            bk_app_code=bk_app_code,
            verified=verified,
        )

    def __call__(self, request):
        jwt_info = getattr(request, "jwt", None)
        if not jwt_info:
            return self.get_response(request)

        jwt_app = (jwt_info.payload.get("app") or {}).copy()
        jwt_app.setdefault("bk_app_code", jwt_app.pop("app_code", None))

        request.app = self.make_app(**jwt_app)

        return self.get_response(request)


class ApiGatewayJWTUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def get_user(self, request, api_name=None, bk_username=None, verified=False, **credentials):
        # 传递 api_name 参数的用途：
        # 1. 来明确标识这个请求来自于网关
        # 2. 用户已经过认证，后端无需再认证
        # 3. 避免非预期调用激活对应后端使得用户认证被绕过
        return auth.authenticate(request, api_name=api_name, bk_username=bk_username, verified=verified, **credentials)

    def __call__(self, request):
        jwt_info = getattr(request, "jwt", None)
        if not jwt_info:
            return self.get_response(request)

        # skip when authenticated
        if hasattr(request, "user") and request.user.is_authenticated:
            return self.get_response(request)

        jwt_user = (jwt_info.payload.get("user") or {}).copy()
        jwt_user.setdefault("bk_username", jwt_user.pop("username", None))

        request.user = self.get_user(request, api_name=jwt_info.api_name, **jwt_user)
        return self.get_response(request)


class UserModelBackend(ModelBackend):
    """Get users by username"""

    def __init__(self):
        super().__init__()

        user_model = get_user_model()

        if hasattr(user_model.objects, "get_by_natural_key"):
            self.user_maker = user_model.objects.get_by_natural_key  # type: ignore
        else:
            self.user_maker = lambda x: user_model.objects.filter(username=x).last()

    def make_anonymous_user(self, bk_username=None):
        user = AnonymousUser()
        user.username = bk_username  # type: ignore
        return user

    def authenticate(self, request, api_name, bk_username, verified, **credentials):
        if not verified:
            return self.make_anonymous_user(bk_username=bk_username)
        return self.user_maker(bk_username)
