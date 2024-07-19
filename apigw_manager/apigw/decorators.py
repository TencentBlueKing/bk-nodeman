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
from functools import wraps

from django.conf import settings
from django.http import HttpResponse

logger = logging.getLogger(__name__)


def apigw_require(view_func):
    def wrapper(request, *args, **kwargs):

        exempt = getattr(settings, "BK_APIGW_REQUIRE_EXEMPT", False)
        if exempt:
            return view_func(request, *args, **kwargs)

        if not hasattr(request, "jwt"):
            logger.warning(
                "can not found jwt in request, "
                "make sure ApiGatewayJWTGenericMiddleware is config in middlewares or receive jwt is valid"
            )
            return HttpResponse(status=403, content="This API can only be accessed through API gateway")

        return view_func(request, *args, **kwargs)

    return wraps(view_func)(wrapper)
