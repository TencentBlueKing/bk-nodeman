# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import logging
import os
import typing
from dataclasses import dataclass

from django.conf import settings
from django.core.management.base import BaseCommand
from drf_spectacular.generators import EndpointEnumerator

from apps.node_man.management.commands.generate_api_js import esb_json2apigw_yaml
from env import BK_NDOEMAN_APIGTW_TIMEOUT

logger = logging.getLogger("app")


class EndPointIndex:
    PATH = 0
    PATTERN = 1
    METHOD = 2
    ACTION_FUNC = 3


class ActionFuncIndex:
    # action指定url_path时方法名称不为path
    FUNC_NAME = 0
    FUNC = 1


@dataclass
class Action:
    request_method: str
    action_name: str
    request_path: str
    tags: typing.List[str]
    description: str
    api_name: str = ""

    def __str__(self):
        return (
            f"<{self.tags[0]} | {self.action_name}: {self.request_method}>"
            f"- {self.request_path} - {self.description}"
        )


class Command(BaseCommand):
    def handle(self, *args, **options):
        action_list: typing.List[Action] = []
        invalid_list: typing.List[str] = []
        for endpoint in EndpointEnumerator().get_api_endpoints():
            method_lower = endpoint[EndPointIndex.METHOD].lower()
            action_name = endpoint[EndPointIndex.ACTION_FUNC].actions[method_lower]
            action_func = endpoint[EndPointIndex.ACTION_FUNC]
            # TODO 接口的元数据（tags、描述等）统一从  swagger_auto_schema 获取，如果需要更多的元数据，也应该补充到 swagger_auto_schema 上
            swagger_auto_schema = getattr(action_func, "_swagger_auto_schema", None) or (
                getattr(getattr(action_func.cls, action_name), "_swagger_auto_schema", None)
            )

            if not swagger_auto_schema:
                invalid_list.append(f"{action_func} / {action_name} need [swagger_auto_schema]")
                continue
            need_registe_apigtw = swagger_auto_schema.get("registe_apigtw", False) or swagger_auto_schema.get(
                method_lower, {}
            ).get("registe_apigtw", False)

            if not need_registe_apigtw:
                continue

            try:
                swagger_auto_schema = swagger_auto_schema[method_lower]
            except Exception:
                pass

            is_check_paas: bool = True
            for required_key in ["tags", "operation_summary"]:
                try:
                    swagger_auto_schema[required_key]
                except KeyError:
                    invalid_list.append(f"{action_func} / {action_name} need [{required_key}]")
                    is_check_paas = False
                    break

            if not is_check_paas:
                continue

            action: Action = Action(
                request_path=endpoint[EndPointIndex.PATH],
                request_method=method_lower,
                action_name=action_name,
                tags=swagger_auto_schema["tags"],
                description=swagger_auto_schema["operation_summary"],
                api_name=swagger_auto_schema.get("api_name"),
            )
            action_list.append(action)

        for action in action_list:
            logger.debug(f"action -> {action}")
        logger.debug("\n".join(invalid_list))

        logger.info(f"action -> {len(action_list)}, invalid_list -> {len(invalid_list)}")
        output = []

        for action in action_list:
            data = {
                "path": action.request_path,
                "resource_name": action.api_name or action.action_name,
                "registed_http_method": action.request_method,
                "description": f"{action.description}",
                "dest_url": f"{settings.BK_NODEMAN_API_URL}/{action.request_path}",
                "timeout": BK_NDOEMAN_APIGTW_TIMEOUT,
                "headers": "{}",
                "resource_classification": action.tags[0],
            }
            output.append(data)

        save_file_path: str = os.path.join(settings.PROJECT_ROOT, "support-files/apigateway/bk-nodeman.yaml")
        logger.info(f"Save yaml file to {save_file_path}")

        esb_json2apigw_yaml(
            apigw_yaml_save_path=save_file_path,
            json_content=output,
        )
        logger.info(f"Save endpoint to yaml file -> [{save_file_path}] success")
