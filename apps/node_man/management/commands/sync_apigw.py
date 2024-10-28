# coding: utf-8
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        if not settings.SYNC_APIGATEWAY_ENABLED:
            return

        # 待同步网关名，需修改为实际网关名；直接指定网关名，则不需要配置 Django settings BK_APIGW_NAME
        gateway_name = settings.BK_APIGW_NAME

        # 待同步网关、资源定义文件，需调整为实际的配置文件地址
        definition_path = "support-files/apigw/definition.yaml"
        resources_path = "support-files/apigw/resources.yaml"

        call_command("sync_apigw_config", f"--api-name={gateway_name}", f"--file={definition_path}")
        call_command("sync_apigw_stage", f"--api-name={gateway_name}", f"--file={definition_path}")
        call_command("sync_apigw_resources", f"--api-name={gateway_name}", "--delete", f"--file={resources_path}")
        # call_command("sync_resource_docs_by_archive", f"--api-name={gateway_name}", f"--file={definition_path}")
        call_command(
            "create_version_and_release_apigw",
            f"--api-name={gateway_name}",
            f"--file={definition_path}",
            f"-s {settings.ENVIRONMENT}",
        )
        call_command("grant_apigw_permissions", f"--api-name={gateway_name}", f"--file={definition_path}")
        call_command("fetch_apigw_public_key", f"--api-name={gateway_name}")
