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

from apigw_manager.apigw.management.commands.fetch_apigw_public_key import Command as BaseCommand


class Command(BaseCommand):
    """Get the esb public key and store it into the database"""

    def handle(self, api_name, *args, **kwargs):
        for name in ["bk-esb", "apigw"]:
            super(Command, self).handle(api_name=name, *args, **kwargs)
