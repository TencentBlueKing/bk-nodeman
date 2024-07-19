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
from apigw_manager.apigw.command import PermissionCommand


class Command(PermissionCommand):
    """Grant API gateway permissions for applications"""

    default_namespace = "grant_permissions"

    def do(self, manager, definition, *args, **kwargs):
        if not definition:
            print("no permission grant definition found, skip")
            return

        for permission in definition:
            permission.setdefault("target_app_code", permission.pop("bk_app_code", None))
            permission.setdefault("grant_dimension", "api")

            manager.grant_permission(**permission)
            print(
                "Granted API gateway %s permission for app code %s, dimension %s"
                % (
                    manager.config.api_name,
                    permission["target_app_code"],
                    permission["grant_dimension"],
                )
            )
