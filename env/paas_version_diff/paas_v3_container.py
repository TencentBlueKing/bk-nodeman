# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import base64
import json
import os
from collections import defaultdict
from typing import Dict, List

from apps.utils.env import get_type_env

DEFAULT_MODULE_NAME = "default"

APP_CODE = get_type_env(key="BKPAAS_APP_ID", default="", _type=str)

ENVIRONMENT = get_type_env(key="BKPAAS_ENVIRONMENT", default="dev", _type=str)

BKPAAS_SERVICE_ADDRESSES_BKSAAS = os.getenv("BKPAAS_SERVICE_ADDRESSES_BKSAAS")
BKPAAS_SERVICE_ADDRESSES_BKSAAS_LIST: List[Dict[str, Dict[str, str]]] = (
    json.loads(base64.b64decode(BKPAAS_SERVICE_ADDRESSES_BKSAAS).decode("utf-8"))
    if BKPAAS_SERVICE_ADDRESSES_BKSAAS
    else {}
)

APP_CODE__SAAS_MODULE_HOST_MAP: Dict[str, Dict[str, str]] = defaultdict(lambda: defaultdict(str))

for item in BKPAAS_SERVICE_ADDRESSES_BKSAAS_LIST:
    module_info = item["key"]
    bk_app_code = module_info.get("bk_app_code")
    module_name = module_info.get("module_name")

    if not bk_app_code:
        continue
    if not module_name or module_name == "None":
        module_name = DEFAULT_MODULE_NAME

    APP_CODE__SAAS_MODULE_HOST_MAP[bk_app_code][module_name] = item["value"].get(ENVIRONMENT)

# define envs

# 是否启用后台配置
BK_BACKEND_CONFIG = get_type_env(key="BACKEND_CONFIG", default=False, _type=bool)

BKAPP_IS_PAAS_DEPLOY = get_type_env(key="BKAPP_IS_PAAS_DEPLOY", default=False, _type=bool)

# esb 访问地址
BK_COMPONENT_API_URL = get_type_env(key="BK_COMPONENT_API_URL", _type=str)

# 节点管理 default 模块地址
BK_NODEMAN_HOST = APP_CODE__SAAS_MODULE_HOST_MAP[APP_CODE][DEFAULT_MODULE_NAME]

# 节点管理后台地址
BK_NODEMAN_BACKEND_HOST = get_type_env(
    key="BKAPP_BACKEND_HOST", default=APP_CODE__SAAS_MODULE_HOST_MAP[APP_CODE]["backend"], _type=str
)

BK_IAM_APP_CODE = get_type_env(key="BK_IAM_V3_APP_CODE", default="bk_iam", _type=str)

BK_IAM_SAAS_HOST = get_type_env(
    key="BK_IAM_V3_SAAS_HOST", default=APP_CODE__SAAS_MODULE_HOST_MAP[BK_IAM_APP_CODE][DEFAULT_MODULE_NAME], _type=str
)

BK_IAM_RESOURCE_API_HOST = get_type_env(key="BKAPP_IAM_RESOURCE_API_HOST", default=BK_NODEMAN_HOST, _type=str)
