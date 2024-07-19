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
import hashlib
import json

from apigw_manager.apigw.command import SyncCommand
from apigw_manager.apigw.helper import ResourceSignatureManager


class Command(SyncCommand):
    """Synchronous API Gateway resources"""

    ResourceSignatureManager = ResourceSignatureManager

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)

        parser.add_argument(
            "--delete",
            default=False,
            action="store_true",
            help="delete extraneous resources from existing resources",
        )

    def update_signature(self, api_name, definition, added, deleted):
        signature = hashlib.md5(json.dumps(definition, sort_keys=True).encode("utf-8")).hexdigest()

        manager = self.ResourceSignatureManager()
        manager.update_signature(api_name, signature)

        # 管理端明确报告有资源的增删，可能有人工手动修改的原因，签名不一定能发现问题，所以需要显式标记
        if added > 0 or deleted > 0:
            manager.mark_dirty(api_name)

    def do(self, manager, definition, configuration, *args, **kwargs):
        result = manager.sync_resources_config(content=definition, delete=kwargs["delete"])

        added_count = len(result["added"])
        deleted_count = len(result["deleted"])
        updated_count = len(result["updated"])

        print(
            "API gateway resources synchronization completed, added %s, updated %s, deleted %s"
            % (added_count, updated_count, deleted_count)
        )

        self.update_signature(configuration.api_name, definition, added_count, deleted_count)
