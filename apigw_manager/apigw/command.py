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
import os
import typing

from django.conf import settings
from django.core.management.base import BaseCommand

from apigw_manager.apigw.helper import Definition
from apigw_manager.apigw.utils import get_configuration, parse_value_list
from apigw_manager.core.fetch import Fetcher
from apigw_manager.core.permission import Manager as PermissionManager
from apigw_manager.core.sync import Synchronizer


class ApiCommand(BaseCommand):

    manager_class: typing.Callable

    def add_arguments(self, parser):
        parser.add_argument("--api-name", help="api name")
        parser.add_argument("--host", help="apigateway host with stage of admin api `bk-apigateway`")

    def get_configuration(self, **kwargs):
        return get_configuration(**{k: v for k, v in kwargs.items() if v is not None})


class DefinitionCommand(ApiCommand):
    default_namespace = ""

    def add_arguments(self, parser):
        super(DefinitionCommand, self).add_arguments(parser)
        parser.add_argument("-d", "--define", nargs="+", default=[], help="define context data")
        parser.add_argument("-f", "--file", required=True, help="definition file")
        parser.add_argument("-n", "--namespace", default=self.default_namespace, help="definition namespace")

    def get_context(self, define, **kwargs):
        data = parse_value_list(*define)
        kwargs.update(
            {
                "data": data,
                "settings": settings,
                "environ": os.environ,
            }
        )
        return kwargs

    def load_definition(self, define, file, **kwargs):
        if not file:
            return None

        context = self.get_context(define)
        return Definition.load_from(file, context)

    def get_definition(self, define, file, namespace, **kwargs):
        definition = self.load_definition(define, file, **kwargs)
        if definition is None:
            return {}

        return definition.get(namespace, {})

    def do(self, manager, definition, *args, **kwargs):
        pass

    def handle(self, *args, **kwargs):
        configuration = self.get_configuration(**kwargs)

        manager = self.manager_class(configuration)
        definition = self.get_definition(**kwargs)

        self.do(manager=manager, definition=definition, configuration=configuration, *args, **kwargs)


class FetchCommand(ApiCommand):
    manager_class = Fetcher


class SyncCommand(DefinitionCommand):
    manager_class = Synchronizer


class PermissionCommand(DefinitionCommand):
    manager_class = PermissionManager
