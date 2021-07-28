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

BK_PAAS_HOST = settings.BK_PAAS_INNER_HOST or settings.BK_PAAS_HOST or ""
ESB_PREFIX_V2 = os.getenv("ESB_PREFIX_V2") or "/api/c/compapi/v2/"


def gen_api_root(api_gw_env_key: str, suffix: str) -> str:
    """生成API根路径，首先从环境变量获取，若环境变量没有，则按默认规则拼接"""
    return os.getenv(api_gw_env_key) or f"{BK_PAAS_HOST}/{ESB_PREFIX_V2}/{suffix}/"


# 蓝鲸平台模块域名
CC_APIGATEWAY_ROOT_V2 = gen_api_root("BKAPP_BK_CC_APIGATEWAY", "cc")
GSE_APIGATEWAY_ROOT_V2 = gen_api_root("BKAPP_BK_GSE_APIGATEWAY", "gse")
ESB_APIGATEWAY_ROOT_V2 = gen_api_root("BKAPP_BK_ESB_APIGATEWAY", "esb")
JOB_APIGATEWAY_ROOT_V3 = gen_api_root("BKAPP_BK_JOB_APIGATEWAY", "jobv3")
BK_NODE_APIGATEWAY_ROOT = gen_api_root("BKAPP_BK_NODE_APIGATEWAY", "nodeman")
