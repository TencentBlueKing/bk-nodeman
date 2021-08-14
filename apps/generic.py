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
import json

from django.conf import settings
from django.http import Http404, JsonResponse
from django.utils.translation import ugettext as _
from rest_framework import exceptions, filters, status
from rest_framework.authentication import BasicAuthentication
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.viewsets import ModelViewSet as _ModelViewSet

from apps.exceptions import AppBaseException, ErrorCode
from apps.utils.drf import (
    CsrfExemptSessionAuthentication,
    DataPageNumberPagination,
    GeneralSerializer,
    custom_params_valid,
)
from common.log import logger


class ApiMixin(GenericViewSet):
    """
    封装 APIViewSet 修改 ModelViewSet 默认返回内容，固定格式为
        {result: True, data: {}, code: 00, message: ''}
    """

    if settings.RUN_MODE in ["DEVELOP", "STAGING"]:
        authentication_classes = (BasicAuthentication, CsrfExemptSessionAuthentication)

    def initialize_request(self, request, *args, **kwargs):
        # 实体是为文件时body省略
        body = "File" if "multipart/form-data" in request.headers.get("Content-Type", "") else request.body
        logger.info(
            "[receive request], path: {}, header: {}, body: {}".format(
                request.path, request.headers.get("X-Bkapi-App"), body
            )
        )
        return super(ApiMixin, self).initialize_request(request, *args, **kwargs)

    def finalize_response(self, request, response, *args, **kwargs):

        # 目前仅对 Restful Response 进行处理
        if isinstance(response, Response):
            response.data = {"result": True, "data": response.data, "code": 0, "message": ""}
            response.status_code = status.HTTP_200_OK

        # 禁用客户端的 MIME 类型嗅探行为，防止基于"MIME"的攻击
        response._headers["x-content-type-options"] = ("X-Content-Type-Options", "nosniff")
        return super(ApiMixin, self).finalize_response(request, response, *args, **kwargs)


class ValidationMixin(GenericViewSet):
    def params_valid(self, serializer, params=None):
        """
        校验参数是否满足 serializer 规定的格式，支持传入serializer
        """
        # 校验request中的参数
        if not params:
            if self.request.method in ["GET"]:
                params = self.request.query_params
            else:
                params = self.request.data

        return custom_params_valid(serializer=serializer, params=params)

    @property
    def validated_data(self):
        """
        校验的数据
        """
        if self.request.method == "GET":
            data = self.request.query_params
        else:
            data = self.request.data
        serializer = self.serializer_class or self.get_serializer_class()
        return self.params_valid(serializer, data)


class APIViewSet(ApiMixin, ValidationMixin, GenericViewSet):
    pass


class Meta(object):
    pass


class ModelViewSet(ApiMixin, ValidationMixin, _ModelViewSet):
    model = None
    pagination_class = DataPageNumberPagination
    filter_backends = (
        filters.OrderingFilter,
        filters.SearchFilter,
    )
    serializer_meta = type("Meta", (Meta,), {"model": None})

    def __init__(self, *args, **kwargs):
        super(ModelViewSet, self).__init__(**kwargs)
        self.filter_fields = [f.name for f in self.model._meta.get_fields()]
        self.view_set_name = self.get_view_object_name(*args, **kwargs)

    def get_view_name(self, *args, **kwargs):
        return self.model._meta.db_table

    def get_view_description(self, *args, **kwargs):
        return self.model._meta.verbose_name

    def get_view_module(self, *args, **kwargs):
        return getattr(self.model._meta, "module", None)

    def get_view_object_name(self, *args, **kwargs):
        return getattr(self.model._meta, "object_name", None)

    def get_queryset(self):
        return self.model.objects.all()

    def get_serializer_class(self, *args, **kwargs):
        self.serializer_meta.model = self.model
        self.serializer_meta.fields = "__all__"
        if isinstance(self.serializer_class, GeneralSerializer) or self.serializer_class is None:
            return type("GeneralSerializer", (GeneralSerializer,), {"Meta": self.serializer_meta})
        else:
            return self.serializer_class


def custom_exception_handler(exc, context):
    """
    自定义错误处理方式
    """
    logger.exception(getattr(exc, "message", exc))
    request = context["request"]

    if request.method == "GET":
        request_params = request.query_params
    else:
        if "multipart/form-data" in request.headers.get("Content-Type", ""):
            request_params = {"files": str(getattr(request, "FILES"))}
        else:
            request_params = request.data

    logger.error(
        """捕获未处理异常, 请求URL->[%s], 请求方法->[%s] 请求参数->[%s]""" % (request.path, request.method, json.dumps(request_params))
    )
    # 专门处理 404 异常，直接返回前端，前端处理
    if isinstance(exc, Http404):
        return JsonResponse(_error(404, str(exc)))

    # # 专门处理 403 异常，直接返回前端，前端处理
    # if isinstance(exc, exceptions.PermissionDenied):
    #     return HttpResponse(exc.detail, status='403')

    # 特殊处理 rest_framework ValidationError
    if isinstance(exc, exceptions.ValidationError):
        return JsonResponse(_error(100, str(exc)))

    # 处理 rest_framework 的异常
    if isinstance(exc, exceptions.APIException):
        return JsonResponse(_error(exc.status_code, exc.detail))

    # 处理 Data APP 自定义异常
    if isinstance(exc, AppBaseException):
        _msg = _("【APP 自定义异常】{message}, code={code}, args={args}").format(
            message=exc.message, code=exc.code, args=exc.args, data=exc.data, errors=exc.errors
        )
        logger.exception(_msg)
        return JsonResponse(_error(exc.code, exc.message, exc.data, exc.errors))

    # 判断是否在debug模式中,
    # 在这里判断是防止阻止了用户原本主动抛出的异常
    if settings.DEBUG:
        return None

    # 非预期异常
    logger.exception(getattr(exc, "message", exc))
    request = context["request"]
    logger.error(
        """捕获未处理异常, 请求URL->[%s], 请求方法->[%s] 请求参数->[%s]"""
        % (request.path, request.method, json.dumps(request.query_params if request.method == "GET" else request.data))
    )
    return JsonResponse(_error(500, _("系统错误，请联系管理员")))


def _error(code=0, message="", data=None, errors=None):
    if len(str(code)) == 3:
        code = ErrorCode.PLAT_CODE + ErrorCode.WEB_CODE + code
    message = f"{message}（{code}）"
    return {"result": False, "code": code, "data": data, "message": message, "errors": errors}
