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
import yaml

from apigw_manager.core.handler import Handler
from apigw_manager.core.utils import itemgetter


class Synchronizer(Handler):
    """Synchronous API gateway configuration"""

    def sync_basic_config(self, *args, **kwargs):
        result = self._call(self.client.api.sync_api, *args, **kwargs)
        return self._parse_result(result, itemgetter("data"))

    def sync_stage_config(self, *args, **kwargs):
        result = self._call(self.client.api.sync_stage, *args, **kwargs)
        return self._parse_result(result, itemgetter("data"))

    def sync_access_strategies(self, *args, **kwargs):
        result = self._call(self.client.api.sync_access_strategy, *args, **kwargs)
        return self._parse_result(result, itemgetter("data"))

    def sync_resources_config(self, content, *args, **kwargs):
        kwargs["content"] = yaml.dump(dict(content))

        result = self._call(self.client.api.sync_resources, *args, **kwargs)
        return self._parse_result(result, itemgetter("data"))

    def sync_resource_docs_by_archive(self, *args, **kwargs):
        result = self._call(self.client.api.import_resource_docs_by_archive, *args, **kwargs)
        return self._parse_result(result, itemgetter("data"))
