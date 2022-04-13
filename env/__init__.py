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

from apps.utils.env import get_type_env

from . import constants
from .paas_version_diff import *  # noqa

__all__ = [
    "BKAPP_RUN_ENV",
    "BKAPP_IS_PAAS_DEPLOY",
    "BK_BACKEND_CONFIG",
    "LOG_TYPE",
    "LOG_LEVEL",
    "BK_LOG_DIR",
    "ENVIRONMENT",
    # esb 访问地址
    "BK_COMPONENT_API_URL",
    # 节点管理SaaS访问地址
    "BK_NODEMAN_HOST",
    # 节点管理后台访问地址
    "BK_NODEMAN_BACKEND_HOST",
    # 权限中心 SaaS 地址
    "BK_IAM_SAAS_HOST",
    # 提供给权限中心的资源回调地址
    "BK_IAM_RESOURCE_API_HOST",
]

# ===============================================================================
# 运行时，用于区分环境差异
# ===============================================================================
# 运行环境，ce / ee / ieod，设置为 ce 将会改变 gse 端口的默认配置
BKAPP_RUN_ENV = get_type_env(key="BKAPP_RUN_ENV", default="ee", _type=str)
# 后台是否为 PaaS 部署
BKAPP_IS_PAAS_DEPLOY = BKAPP_IS_PAAS_DEPLOY
# # 是否为后台配置
BK_BACKEND_CONFIG = BK_BACKEND_CONFIG

# ===============================================================================
# 日志
# ===============================================================================
# 日志类别
LOG_TYPE = get_type_env(key="LOG_TYPE", default=constants.LogType.DEFAULT, _type=str)
# 日志级别
LOG_LEVEL = get_type_env(key="LOG_LEVEL", default="INFO", _type=str)
# 日志所在目录
BK_LOG_DIR = get_type_env(key="BK_LOG_DIR", default="./../bk_nodeman/logs", _type=str)
