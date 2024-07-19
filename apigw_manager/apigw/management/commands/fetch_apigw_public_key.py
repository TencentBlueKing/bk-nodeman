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
from apigw_manager.apigw import helper
from apigw_manager.apigw.command import FetchCommand


class Command(FetchCommand):
    """Get the public key of the specified API gateway and store it into the database"""

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)

        parser.add_argument(
            "-p", "--print", dest="print_", default=False, action="store_true", help="print the public key"
        )
        parser.add_argument("--bk-app-code", dest="bk_app_code", help="app code")
        parser.add_argument("--bk-app-secret", dest="bk_app_secret", help="app secret")
        parser.add_argument("--no-save", default=False, action="store_true", help="do not save the public key")

    def handle(self, print_, no_save, *args, **kwargs):
        configuration = self.get_configuration(**kwargs)
        manager = self.manager_class(configuration)
        result = manager.public_key()

        if print_:
            print(result["public_key"])

        if no_save:
            return

        public_key_manager = helper.make_default_public_key_manager()
        public_key_manager.set(configuration.api_name, result["public_key"], result.get("issuer"))
