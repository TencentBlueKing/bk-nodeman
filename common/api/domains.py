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
import os

from django.conf import settings

ESB_PREFIX_V2 = os.getenv("ESB_PREFIX_V2") or "/api/c/compapi/v2/"


def gen_api_root(api_gw_env_key: str, suffix: str) -> str:
    """生成API根路径，首先从环境变量获取，若环境变量没有，则按默认规则拼接"""
    api_gw_env_val = os.getenv(api_gw_env_key)
    if api_gw_env_val:
        return api_gw_env_val

    api_root = f"{settings.BK_COMPONENT_API_URL}/{ESB_PREFIX_V2}/{suffix}/"
    if api_root.startswith("http://"):
        api_root = api_root[:7] + api_root[7:].replace("//", "/")
    elif api_root.startswith("https://"):
        api_root = api_root[:8] + api_root[8:].replace("//", "/")
    else:
        api_root = api_root.replace("//", "/")
    return api_root


# 蓝鲸平台模块域名
CC_APIGATEWAY_ROOT_V2 = gen_api_root("BKAPP_BK_CC_APIGATEWAY", "cc")
GSE_APIGATEWAY_ROOT_V2 = gen_api_root("BKAPP_BK_GSE_APIGATEWAY", "gse")
ESB_APIGATEWAY_ROOT_V2 = gen_api_root("BKAPP_BK_ESB_APIGATEWAY", "esb")
JOB_APIGATEWAY_ROOT_V3 = gen_api_root("BKAPP_BK_JOB_APIGATEWAY", "jobv3")
BK_NODE_APIGATEWAY_ROOT = gen_api_root("BKAPP_BK_NODE_APIGATEWAY", "nodeman")
