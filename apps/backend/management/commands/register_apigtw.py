# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making 蓝鲸智云PaaS平台社区版 (BlueKing PaaS Community
Edition) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at
http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import os
import traceback

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        definition_file_path = os.path.join(settings.PROJECT_ROOT, "support-files/apigateway/definition.yaml")
        resources_file_path = os.path.join(settings.PROJECT_ROOT, "support-files/apigateway/bk-nodeman.yaml")

        print("[bk-nodeman]call sync_apigw_config with definition: %s" % definition_file_path)
        call_command("sync_apigw_config", file=definition_file_path)

        print("[bk-nodeman]call sync_apigw_stage with definition: %s" % definition_file_path)
        call_command("sync_apigw_stage", file=definition_file_path)

        print("[bk-nodeman]call sync_apigw_resources with resources: %s" % resources_file_path)
        call_command("sync_apigw_resources", "--delete", file=resources_file_path)

        print("[bk-nodeman]call sync_resource_docs_by_archive with definition: %s" % definition_file_path)
        call_command("sync_resource_docs_by_archive", f"--file={definition_file_path}")

        print("[bk-nodeman]call create_version_and_release_apigw with definition: %s" % definition_file_path)
        call_command("create_version_and_release_apigw", "--generate-sdks", file=definition_file_path)

        print("[bk-nodeman]call fetch_apigw_public_key")
        call_command("fetch_apigw_public_key")

        print("[bk-nodeman]call fetch_esb_public_key")
        try:
            call_command("fetch_esb_public_key")
        except Exception:
            print("[bk-nodeman]this env has not bk-nodeman esb api,skip fetch_esb_public_key ")
            traceback.print_exc()
