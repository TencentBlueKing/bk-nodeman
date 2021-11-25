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

import six
from django.db import models
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.fields import DateTimeField, empty
from rest_framework.pagination import PageNumberPagination
from rest_framework.renderers import BaseRenderer
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer
from rest_framework.utils import model_meta

from apps.exceptions import ValidationError
from apps.utils.cst_method import DjangoJSONEncoderExtend
from apps.utils.local import get_request_username
from apps.utils.time_handler import strftime_local


def format_serializer_errors(errors, fields, params, prefix="", return_all_errors=True):
    """
    格式化序列化器的错误，对前端显示更为友好
    :param errors: serializer_errors
    :param fields: 校验的字段
    :param params: 参数
    :param prefix: 错误消息前缀
    :param return_all_errors: 是否返回所有错误消息
    :return:
    """
    message = ""
    for key, field_errors in list(errors.items()):
        sub_message = ""
        label = key
        if key not in fields:
            sub_message = json.dumps(field_errors)
        else:
            field = fields[key]
            label = f"{field.label}({field.field_name})"
            if (
                hasattr(field, "child")
                and isinstance(field_errors, list)
                and len(field_errors) > 0
                and not isinstance(field_errors[0], str)
            ):
                for index, sub_errors in enumerate(field_errors):
                    if sub_errors:
                        sub_format = format_serializer_errors(sub_errors, field.child.fields, params, prefix=prefix)
                        if not return_all_errors:
                            return f"{label}: {sub_format}"
                        sub_message += f"{prefix}第{index + 1}项:"
                        sub_message += sub_format
            else:
                if isinstance(field_errors, dict):
                    if hasattr(field, "child"):
                        sub_format = format_serializer_errors(field_errors, field.child.fields, params, prefix=prefix)
                    else:
                        sub_format = format_serializer_errors(field_errors, field.fields, params, prefix=prefix)
                    if not return_all_errors:
                        return f"{label}: {sub_format}"
                    sub_message += sub_format
                elif isinstance(field_errors, list):
                    for index, error in enumerate(field_errors):
                        field_errors[index] = field_errors[index].format(**{key: params.get(key, "")})
                        sub_message += "{index}.{error}".format(index=index + 1, error=field_errors[index])
                        if not return_all_errors:
                            return f"{label}: {sub_message}"
                    sub_message += " "
        message += f"{prefix}{label}: {sub_message}"
    return message


def custom_params_valid(serializer, params, many=False):
    _serializer = serializer(data=params, many=many)
    try:
        _serializer.is_valid(raise_exception=True)
    except serializers.ValidationError:
        message = format_serializer_errors(_serializer.errors, _serializer.fields, params)
        raise ValidationError(message)
    if many:
        return list(_serializer.data)
    else:
        return dict(_serializer.data)


class CustomDateTimeField(DateTimeField):
    def to_representation(self, value):
        if not value:
            return None
        return strftime_local(value, fmt="%Y-%m-%d %H:%M:%S%z")


class GeneralSerializer(ModelSerializer):
    def __init__(self, instance=None, data=empty, **kwargs):
        username = get_request_username()
        try:
            if instance:
                data["updated_by"] = username
            else:
                data["created_by"] = username
        except Exception:
            pass
        self.serializer_field_mapping[models.DateTimeField] = CustomDateTimeField
        super(GeneralSerializer, self).__init__(instance=instance, data=data, **kwargs)

    def is_valid(self, raise_exception=False):
        try:
            super(GeneralSerializer, self).is_valid(raise_exception)
        except ValidationError:
            if self._errors and raise_exception:
                raise ValidationError(
                    format_serializer_errors(self.errors, self.fields, self.initial_data),
                )

        return not bool(self._errors)

    def create(self, validated_data):
        ModelClass = self.Meta.model

        info = model_meta.get_field_info(ModelClass)
        many_to_many = {}
        for field_name, relation_info in list(info.relations.items()):
            if relation_info.to_many and (field_name in validated_data):
                many_to_many[field_name] = validated_data.pop(field_name)

        try:
            instance = ModelClass.objects.create(**validated_data)
        except TypeError as exc:
            msg = (
                "Got a `TypeError` when calling `%s.objects.create()`. "
                "This may be because you have a writable field on the "
                "serializer class that is not a valid argument to "
                "`%s.objects.create()`. You may need to make the field "
                "read-only, or override the %s.create() method to handle "
                "this correctly.\nOriginal exception text was: %s."
                % (ModelClass.__name__, ModelClass.__name__, self.__class__.__name__, exc)
            )
            raise TypeError(msg)

        # Save many-to-many relationships after the instance is created.
        if many_to_many:
            for field_name, value in list(many_to_many.items()):
                setattr(instance, field_name, value)

        return instance

    class Meta:
        model = None


class DataPageNumberPagination(PageNumberPagination):
    PAGE_SIZE = 10
    page_query_param = "page"
    page_size_query_param = "pagesize"
    max_page_size = 1000

    def get_paginated_response(self, data):
        return Response({"total": self.page.paginator.count, "list": data})


class GeneralJSONRenderer(BaseRenderer):
    """
    Renderer which serializes to JSON.
    Applies JSON's backslash-u character escaping for non-ascii characters.
    Uses the blazing-fast ujson library for serialization.
    """

    media_type = "application/json"
    format = "json"
    ensure_ascii = True
    charset = None

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if data is None:
            return bytes()
        ret = json.dumps(data, cls=DjangoJSONEncoderExtend)
        # force return value to unicode
        if isinstance(ret, six.text_type):
            return bytes(ret.encode("utf-8"))
        return ret


class MultipleIntField(serializers.Field):
    """
    用于整数多选查询的字段
    """

    def to_internal_value(self, data):
        ret = []
        for value in data.split(","):
            try:
                ret.append(int(value))
            except ValueError:
                raise ValidationError(_("请求参数必须全部为整数"))
        return ret

    def to_representation(self, value):
        return value


class MultipleStrField(serializers.Field):
    """
    用于字符串多选查询的字段
    """

    def to_internal_value(self, data):
        data = [str(value) for value in data.split(",")]
        return data

    def to_representation(self, value):
        return value


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        # To not perform the csrf check previously happening
        return
