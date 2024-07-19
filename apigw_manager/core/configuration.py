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


class Configuration(object):
    """Configuration information"""

    def __init__(
        self,
        host=None,
        stage=None,
        bk_app_code=None,
        bk_app_secret=None,
        api_name=None,
        api_cache=None,
        access_token=None,
        jwt_provider_cls=None,
        *args,
        **kwargs,
    ):
        self.host = host
        self.stage = stage
        self.bk_app_code = bk_app_code
        self.bk_app_secret = bk_app_secret
        self.api_name = api_name
        self.api_cache = api_cache
        self.access_token = access_token
        self.jwt_provider_cls = jwt_provider_cls
