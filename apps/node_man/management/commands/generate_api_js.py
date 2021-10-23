# coding: utf-8
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import json
import os
from collections import defaultdict

import yaml
from django.core.management.base import BaseCommand

from apps.utils.generate_api_js import main


def esb_json2apigw_yaml(esb_json_file_path: str, apigw_yaml_save_path: str):
    with open(file=esb_json_file_path, encoding="utf-8") as esb_json_file_stream:
        esb_json = json.loads(esb_json_file_stream.read())

    # 对相同api路径进行聚合
    api_info_gby_path = defaultdict(list)
    for api_info in esb_json:
        api_info_gby_path[api_info["path"]].append(api_info)

    apigw_json = {
        "swagger": "2.0",
        "basePath": "/",
        "info": {"version": "0.1", "title": "API Gateway Resources"},
        "schemes": ["http"],
        "paths": {},
    }

    for api_path, api_infos in api_info_gby_path.items():
        http_method_api_info_map = {}
        for api_info in api_infos:
            http_method_api_info_map[api_info["registed_http_method"].lower()] = {
                "operationId": f"{api_info['resource_classification'].lower()}_{api_info['resource_name']}",
                "description": api_info["description"],
                "tags": [api_info["resource_classification"]],
                "x-bk-apigateway-resource": {
                    "isPublic": True,
                    "allowApplyPermission": True,
                    "matchSubpath": False,
                    "backend": {
                        "type": "HTTP",
                        "method": api_info["registed_http_method"].lower(),
                        "path": api_info["path"],
                        "matchSubpath": False,
                        "timeout": api_info.get("timeout", 0),
                        "upstreams": {},
                        "transformHeaders": {},
                    },
                    "authConfig": {"userVerifiedRequired": False},
                    "disabledStages": [],
                },
            }
        apigw_json["paths"][api_path] = http_method_api_info_map

    with open(apigw_yaml_save_path, encoding="utf-8", mode="w") as f:
        yaml.dump(apigw_json, f, encoding="utf-8", allow_unicode=True)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("-g", "--is_apigw", action="store_true", help="whether for api_gateway")
        parser.add_argument("--is_apigw_yaml", action="store_true", help="convert esb json to apigw yaml")
        parser.add_argument("-f", type=str, help="apigw yaml save path")

    def handle(self, **kwargs):

        if kwargs["is_apigw_yaml"]:
            esb_json_file_path = main(is_apigw=True)
            esb_json2apigw_yaml(esb_json_file_path=esb_json_file_path, apigw_yaml_save_path=kwargs["f"])
            os.remove(esb_json_file_path)
        else:
            main(kwargs["is_apigw"])
