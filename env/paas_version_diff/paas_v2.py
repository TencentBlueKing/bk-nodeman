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

from apps.utils.env import get_type_env

APP_CODE = get_type_env(key="APP_ID", default="", _type=str)

BK_PAAS_HOST = get_type_env(key="BK_PAAS_HOST", default="", _type=str)

BK_PAAS_INNER_HOST = get_type_env(key="BK_PAAS_INNER_HOST", default=BK_PAAS_HOST, _type=str)

PAAS_V2_ENVIRONMENT = get_type_env(key="BK_ENV", default="development", _type=str)

# define envs

# PaaS 部署环境
ENVIRONMENT = {"development": "dev", "testing": "stag", "production": "prod"}.get(PAAS_V2_ENVIRONMENT)

# 是否启用后台配置
BK_BACKEND_CONFIG = get_type_env(key="BK_BACKEND_CONFIG", default=False, _type=bool)

BKAPP_IS_PAAS_DEPLOY = False

# esb 访问地址
BK_COMPONENT_API_URL = BK_PAAS_INNER_HOST or BK_PAAS_HOST or ""

# 节点管理 default 模块地址
BK_NODEMAN_HOST = get_type_env(key="BK_NODEMAN_URL", default=f"{BK_PAAS_INNER_HOST}/o/{APP_CODE}", _type=str)

# 节点管理后台地址
BK_NODEMAN_BACKEND_HOST = get_type_env(key="BKAPP_BACKEND_HOST", default="", _type=str)

BK_IAM_APP_CODE = get_type_env(key="BK_IAM_V3_APP_CODE", default="bk_iam", _type=str)

BK_IAM_SAAS_HOST = get_type_env(key="BK_IAM_V3_SAAS_HOST", default=f"{BK_PAAS_HOST}/o/{BK_IAM_APP_CODE}/", _type=str)

BK_IAM_RESOURCE_API_HOST = get_type_env(
    key="BKAPP_IAM_RESOURCE_API_HOST", default=f"{BK_PAAS_INNER_HOST}/o/{APP_CODE}/", _type=str
)
