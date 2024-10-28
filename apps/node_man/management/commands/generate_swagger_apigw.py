# coding: utf-8
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import copy
import logging
import os
from collections import OrderedDict

from coreapi.compat import force_bytes, urlparse
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand
from django.urls import get_script_prefix
from drf_yasg import openapi
from drf_yasg.app_settings import swagger_settings
from drf_yasg.codecs import VALIDATORS, OpenAPICodecJson, OpenAPICodecYaml
from drf_yasg.errors import SwaggerValidationError
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.utils import get_consumes, get_produces
from rest_framework.settings import api_settings
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView


class ApigwOpenAPICodecYaml(OpenAPICodecYaml):
    def encode(self, document):

        spec = self.generate_swagger_object(document)
        errors = {}
        for validator in self.validators:
            try:
                VALIDATORS[validator](copy.deepcopy(spec))
            except SwaggerValidationError as e:
                errors[validator] = str(e)

        if errors:
            raise SwaggerValidationError("spec validation failed: {}".format(errors), errors, spec, self)

        return force_bytes(self._dump_dict(spec))


class PathItem(openapi.PathItem):
    def __init__(self, get=None, put=None, post=None, delete=None, options=None, head=None, patch=None, **extra):
        super().__init__(**extra)
        self.get = get
        self.head = head
        self.post = post
        self.put = put
        self.patch = patch
        self.delete = delete
        self.options = options
        self._insert_extras__()


class ApigwSwagger(openapi.SwaggerDict):
    def __init__(
        self,
        info=None,
        _url=None,
        _prefix=None,
        _version=None,
        consumes=None,
        produces=None,
        security_definitions=None,
        security=None,
        paths=None,
        definitions=None,
        **extra,
    ):
        """Root Swagger object."""
        super(ApigwSwagger, self).__init__(**extra)
        self.swagger = "2.0"
        self.info = info
        self.info.version = _version or info._default_version

        if _url:
            url = urlparse.urlparse(_url)
            assert url.netloc and url.scheme, "if given, url must have both schema and netloc"
            self.host = url.netloc
            self.schemes = [url.scheme]

        self.base_path = self.get_base_path(get_script_prefix(), _prefix)
        self.paths = paths
        self._insert_extras__()

    @classmethod
    def get_base_path(cls, script_prefix, api_prefix):
        # avoid double slash when joining script_name with api_prefix
        if script_prefix and script_prefix.endswith("/"):
            script_prefix = script_prefix[:-1]
        if not api_prefix.startswith("/"):
            api_prefix = "/" + api_prefix

        base_path = script_prefix + api_prefix

        # ensure that the base path has a leading slash and no trailing slash
        if base_path and base_path.endswith("/"):
            base_path = base_path[:-1]
        if not base_path.startswith("/"):
            base_path = "/" + base_path

        return base_path


class ApigwOpenAPISchemaGenerator(OpenAPISchemaGenerator):
    def get_schema(self, request=None, public=False):
        """Generate a :class:`.Swagger` object representing the API schema."""
        endpoints = self.get_endpoints(request)
        components = self.reference_resolver_class(openapi.SCHEMA_DEFINITIONS, force_init=True)
        self.consumes = get_consumes(api_settings.DEFAULT_PARSER_CLASSES)
        self.produces = get_produces(api_settings.DEFAULT_RENDERER_CLASSES)
        paths, prefix = self.get_paths(endpoints, components, request, public)

        security_definitions = self.get_security_definitions()
        if security_definitions:
            security_requirements = self.get_security_requirements(security_definitions)
        else:
            security_requirements = None

        url = self.url
        if url is None and request is not None:
            url = request.build_absolute_uri()

        return ApigwSwagger(
            info=self.info,
            paths=paths,
            consumes=self.consumes or None,
            produces=self.produces or None,
            security_definitions=security_definitions,
            security=security_requirements,
            _url=url,
            _prefix=prefix,
            _version=self.version,
            **dict(components),
        )

    def get_path_item(self, path, view_cls, operations):
        return PathItem(**operations)

    def get_operation(self, view, path, prefix, method, components, request):
        """Get an :class:`.Operation` for the given API endpoint (path, method). This method delegates to"""
        overrides = self.get_overrides(view, method)
        if not overrides.get("extra_overrides", {}).get("is_register_apigw", False):
            return None

        operation = super().get_operation(view, path, prefix, method, components, request)

        apigw_operation = {
            "operationId": operation["operationId"],
            "summary": operation["summary"],
            "tags": operation["tags"],
            "x-bk-apigateway-resource": {
                "isPublic": True,
                "allowApplyPermission": True,
                "matchSubpath": False,
                "backend": {
                    "name": "default",
                    "method": method.lower(),
                    "path": path,
                    "matchSubpath": False,
                    "timeout": 0,
                },
                "authConfig": {
                    "userVerifiedRequired": True,
                    "appVerifiedRequired": True,
                    "resourcePermissionRequired": True,
                },
            },
        }

        return apigw_operation

    def get_paths(self, endpoints, components, request, public):
        if not endpoints:
            return openapi.Paths(paths={}), ""

        prefix = self.determine_path_prefix(list(endpoints.keys())) or ""
        assert "{" not in prefix, "base path cannot be templated in swagger 2.0"

        paths = OrderedDict()
        for path, (view_cls, methods) in sorted(endpoints.items()):
            operations = {}
            for method, view in methods:
                if not self.should_include_endpoint(path, method, view, public):
                    continue

                operation = self.get_operation(view, path, prefix, method, components, request)
                if operation is not None:
                    operations[method.lower()] = operation

            if operations:
                path_suffix = path[len(prefix) :]
                if not path_suffix.startswith("/"):
                    path_suffix = "/" + path_suffix

                open_path = f"/open{path_suffix}"
                paths[open_path] = self.get_path_item(path, view_cls, operations)

                system_path = f"/system{path_suffix}"
                system_operations = {
                    method: self.modify_operation(operation, "system_")
                    for method, operation in copy.deepcopy(operations).items()
                }
                paths[system_path] = self.get_path_item(path, view_cls, system_operations)

        return self.get_paths_object(paths), prefix

    @staticmethod
    def modify_operation(operation, prefix):
        operation["operationId"] = f"{prefix}{operation['operationId']}"
        operation["x-bk-apigateway-resource"]["authConfig"]["userVerifiedRequired"] = False
        operation["x-bk-apigateway-resource"]["allowApplyPermission"] = False
        operation["x-bk-apigateway-resource"]["isPublic"] = False
        return operation


class Command(BaseCommand):
    help = "Write the Swagger schema to disk in JSON or YAML format."

    def add_arguments(self, parser):
        parser.add_argument(
            "output_file",
            metavar="output-file",
            nargs="?",
            default="-",
            type=str,
            help='Output path for generated swagger document, or "-" for stdout.',
        )
        parser.add_argument(
            "-o",
            "--overwrite",
            default=False,
            action="store_true",
            help="Overwrite the output file if it already exists. "
            "Default behavior is to stop if the output file exists.",
        )
        parser.add_argument(
            "-f",
            "--format",
            dest="format",
            default="",
            choices=["json", "yaml"],
            type=str,
            help="Output format. If not given, it is guessed from the output file extension and defaults to json.",
        )
        parser.add_argument(
            "-u",
            "--url",
            dest="api_url",
            default="",
            type=str,
            help="Base API URL - sets the host and scheme attributes of the generated document.",
        )
        parser.add_argument(
            "-m",
            "--mock-request",
            dest="mock",
            default=False,
            action="store_true",
            help="Use a mock request when generating the swagger schema. This is useful if your views or serializers "
            "depend on context from a request in order to function.",
        )
        parser.add_argument(
            "--api-version",
            dest="api_version",
            type=str,
            help="Version to use to generate schema. This option implies --mock-request.",
        )
        parser.add_argument(
            "--user",
            dest="user",
            help="Username of an existing user to use for mocked authentication. This option implies --mock-request.",
        )
        parser.add_argument(
            "-p",
            "--private",
            default=False,
            action="store_true",
            help="Hides endpoints not accesible to the target user. If --user is not given, only shows endpoints that "
            "are accesible to unauthenticated users.\n"
            "This has the same effect as passing public=False to get_schema_view() or "
            "OpenAPISchemaGenerator.get_schema().\n"
            "This option implies --mock-request.",
        )
        parser.add_argument(
            "-g",
            "--generator-class",
            dest="generator_class_name",
            default="",
            help="Import string pointing to an OpenAPISchemaGenerator subclass to use for schema generation.",
        )

    def write_schema(self, schema, stream, format):
        if format == "json":
            codec = OpenAPICodecJson(validators=[], pretty=True)
            swagger_json = codec.encode(schema).decode("utf-8")
            stream.write(swagger_json)
        elif format == "yaml":
            codec = ApigwOpenAPICodecYaml(validators=[])
            swagger_yaml = codec.encode(schema).decode("utf-8")
            # YAML is already pretty!
            stream.write(swagger_yaml)
        else:  # pragma: no cover
            raise ValueError("unknown format %s" % format)

    def get_mock_request(self, url, format, user=None):
        factory = APIRequestFactory()

        request = factory.get(url + "/swagger." + format)
        if user is not None:
            force_authenticate(request, user=user)
        request = APIView().initialize_request(request)
        return request

    def get_schema_generator(self, generator_class_name, api_info, api_version, api_url):
        generator_class = ApigwOpenAPISchemaGenerator

        return generator_class(
            info=api_info,
            version=api_version,
            url=api_url,
        )

    def get_schema(self, generator, request, public):
        return generator.get_schema(request=request, public=public)

    def handle(
        self,
        output_file,
        overwrite,
        format,
        api_url,
        mock,
        api_version,
        user,
        private,
        generator_class_name,
        *args,
        **kwargs,
    ):
        # disable logs of WARNING and below
        logging.disable(logging.WARNING)

        info = getattr(swagger_settings, "DEFAULT_INFO", None)
        if not isinstance(info, openapi.Info):
            raise ImproperlyConfigured(
                'settings.SWAGGER_SETTINGS["DEFAULT_INFO"] should be an '
                "import string pointing to an openapi.Info object"
            )

        if not format:
            if os.path.splitext(output_file)[1] in (".yml", ".yaml"):
                format = "yaml"
        format = format or "json"

        api_url = api_url or swagger_settings.DEFAULT_API_URL

        if user:
            # Only call get_user_model if --user was passed in order to
            # avoid crashing if auth is not configured in the project
            user = get_user_model().objects.get(**{get_user_model().USERNAME_FIELD: user})

        mock = mock or private or (user is not None) or (api_version is not None)
        if mock and not api_url:
            raise ImproperlyConfigured(
                "--mock-request requires an API url; either provide "
                "the --url argument or set the DEFAULT_API_URL setting"
            )

        request = None
        if mock:
            request = self.get_mock_request(api_url, format, user)

        api_version = api_version or api_settings.DEFAULT_VERSION
        if request and api_version:
            request.version = api_version

        generator = self.get_schema_generator(generator_class_name, info, api_version, api_url)
        schema = self.get_schema(generator, request, not private)

        print(output_file)

        if output_file == "-":
            self.write_schema(schema, self.stdout, format)
        else:
            flags = "w" if overwrite else "x"
            with open(output_file, flags) as stream:
                self.write_schema(schema, stream, format)
