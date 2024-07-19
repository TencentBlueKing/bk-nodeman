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


class Fetcher(Handler):
    """Get API gateway information"""

    def public_key(self, *args, **kwargs):
        """Get the API gateway public key according to the name"""
        result = self._call_with_cache(self.client.api.get_apigw_public_key, *args, **kwargs)
        return self._parse_result(result, itemgetter("data"))

    def latest_resource_version(self, *args, **kwargs):
        """Get the latest resource version"""
        result = self._call(self.client.api.get_latest_resource_version, *args, **kwargs)
        return self._parse_result(result, itemgetter("data"))
