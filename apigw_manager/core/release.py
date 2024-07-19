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


class Releaser(Handler):
    """API gateway release manager"""

    def create_resource_version(self, *args, **kwargs):
        """create a version"""

        result = self._call(self.client.api.create_resource_version, *args, **kwargs)
        return self._parse_result(result, itemgetter("data"))

    def release(self, *args, **kwargs):
        """release a version"""

        result = self._call(self.client.api.release, *args, **kwargs)
        return self._parse_result(result, itemgetter("data"))

    def generate_sdks(self, *args, **kwargs):
        """generate sdks"""

        result = self._call(self.client.api.generate_sdk, *args, **kwargs)
        return self._parse_result(result, itemgetter("data"))
