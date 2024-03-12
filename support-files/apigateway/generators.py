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
import typing
from dataclasses import dataclass

from drf_spectacular.plumbing import normalize_result_object, sanitize_result_object
from drf_spectacular.renderers import OpenApiYamlRenderer
from drf_yasg.generators import SchemaGenerator
from drf_yasg.renderers import SwaggerJSONRenderer


@dataclass
class SchemeType:
    name: str
    format: str
    extra_msg: str
    version: str


class SchemeEnum:
    Swagger = "Swagger"


class SwaggerRender(OpenApiYamlRenderer):
    pass


class SwaggerGenerator(SchemaGenerator):
    def __init__(self, type: SchemeType):
        self.type = type

    def custom_build_root_object(self, *args, **kwargs):
        from drf_spectacular.plumbing import build_root_object

        root = build_root_object(*args, **kwargs)
        root["openapi"] = "swagger"
        return root

    def get_schema(self):
        from drf_spectacular.settings import spectacular_settings

        """ Generate a swagger schema. """
        # reset_generator_stats()
        result = self.custom_build_root_object(
            paths=self.parse(),
            components=self.registry.build(spectacular_settings.APPEND_COMPONENTS),
            version=self.version,
        )
        for hook in spectacular_settings.POSTPROCESSING_HOOKS:
            # 这里 public 强制为 True， 否则有权限问题
            result = hook(result=result, generator=self, public=True)

        return sanitize_result_object(normalize_result_object(result))

    def render(self, scheme, renderer_context):
        render = get_renderer(type=type)
        return render.render(scheme, renderer_context)


def get_renderer(scheme_type: SchemeType):
    renderer_cls = {
        SchemeEnum.Swagger: SwaggerRender,
    }[scheme_type]
    return renderer_cls() or SwaggerRender()


def get_apigtw_generator():
    from django.conf import settings

    generator_map = {}
