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
from apigw_manager.apigw.command import SyncCommand


class Command(SyncCommand):
    """Synchronous API Gateway strategies configuration"""

    default_namespace = "strategies"

    def add_arguments(self, parser):
        super().add_arguments(parser)

        parser.add_argument(
            "--scope-type",
            default="stage",
            help="strategy scope type",
        )

    def do(self, manager, definition, scope_type, *args, **kwargs):
        if not definition:
            print("no strategy definition found, skip")
            return

        for strategy in definition:
            strategy.setdefault("scopes", [])
            strategy[strategy["type"]] = strategy.pop("config")
            strategy.setdefault(
                "name",
                "%s_%s"
                % (
                    strategy["type"],
                    strategy.setdefault("scope_type", scope_type),
                ),
            )

            result = manager.sync_access_strategies(**strategy)
            print("API gateway strategy synchronization completed, id %s, name %s" % (result["id"], result["name"]))
