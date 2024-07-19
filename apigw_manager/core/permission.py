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
from apigw_manager.core.handler import Handler
from apigw_manager.core.utils import itemgetter


class Manager(Handler):
    """Manage API Gateway Permissions"""

    def apply_permission(self, *args, **kwargs):
        """Apply for API Gateway Permissions"""
        result = self._call(self.client.api.apply_permissions, *args, **kwargs)
        return self._parse_result(result, itemgetter("data"))

    def grant_permission(self, *args, **kwargs):
        """Grant API gateway permissions for applications"""
        result = self._call(self.client.api.grant_permissions, *args, **kwargs)
        return self._parse_result(result, itemgetter("data"))
