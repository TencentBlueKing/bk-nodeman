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
    "BKAPP_ENABLE_DHCP",
    "BKAPP_IS_PAAS_DEPLOY",
    "BK_BACKEND_CONFIG",
    "LOG_TYPE",
    "LOG_LEVEL",
    "BK_LOG_DIR",
    "GSE_VERSION",
    "BKAPP_ENABLE_OTEL_TRACE",
    "BKAPP_OTEL_INSTRUMENT_DB_API",
    "BKAPP_OTEL_SAMPLER",
    "BKAPP_OTEL_BK_DATA_TOKEN",
    "BKAPP_OTEL_GRPC_URL",
    "BKAPP_NAV_OPEN_SOURCE_URL",
    "BKAPP_NAV_HELPER_URL",
    "BK_CC_HOST",
    "BK_API_URL_TMPL",
    "ENVIRONMENT",
    "BKPAAS_MAJOR_VERSION",
    # esb 访问地址
    "BK_COMPONENT_API_URL",
    # esb 访问外网地址
    "BK_COMPONENT_API_OUTER_URL",
    # 节点管理SaaS访问地址
    "BK_NODEMAN_HOST",
    # 节点管理后台访问地址
    "BK_NODEMAN_BACKEND_HOST",
    # 权限中心 SaaS 地址
    "BK_IAM_SAAS_HOST",
    # 提供给权限中心的资源回调地址
    "BK_IAM_RESOURCE_API_HOST",
    "BK_DOMAIN",
]

# ===============================================================================
# 运行时，用于区分环境差异
# ===============================================================================
# 运行环境，ce / ee / ieod，设置为 ce 将会改变 gse 端口的默认配置
BKAPP_RUN_ENV = get_type_env(key="BKAPP_RUN_ENV", default="ee", _type=str)
# 后台是否为 PaaS 部署
BKAPP_IS_PAAS_DEPLOY = BKAPP_IS_PAAS_DEPLOY
# 是否开启动态主机配置协议适配
BKAPP_ENABLE_DHCP = get_type_env(key="BKAPP_ENABLE_DHCP", default=False, _type=bool)
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


# ===============================================================================
# 蓝鲸管控平台
# ===============================================================================
# 平台版本
GSE_VERSION = get_type_env(key="GSE_VERSION", default=constants.GseVersion.V1.value, _type=str)

GSE_CERT_PATH = get_type_env(key="GSE_CERT_PATH", default="/data/bkce/cert", _type=str)

# 是否启用推送 GSE 环境变量文件，如果启用，将在 Agent `安装`/`重装`/`重载配置`/`灰度` 操作成功后，进行如下操作：
# Windows：推送 `environ.sh` & `environ.bat` 到目标机器的 `GSE_ENVIRON_WIN_DIR` 路径
# Linux：推送 `environ.sh` 到目标机器的 `GSE_ENVIRON_DIR` 路径
GSE_ENABLE_PUSH_ENVIRON_FILE = get_type_env(key="GSE_ENABLE_PUSH_ENVIRON_FILE", default=False, _type=bool)

# GSE 环境变量目录
GSE_ENVIRON_DIR = get_type_env(key="GSE_ENVIRON_DIR", default="", _type=str)

# GSE 环境变量目录（Windows）
GSE_ENVIRON_WIN_DIR = get_type_env(key="GSE_ENVIRON_WIN_DIR", default="", _type=str)

# ===============================================================================
# 可观测
# ===============================================================================
# 是否开启 Trace
BKAPP_ENABLE_OTEL_TRACE = get_type_env(key="BKAPP_ENABLE_OTEL_TRACE", default=False, _type=bool)
# BKAPP_OTEL_SERVICE_NAME 隐藏配置，框架生成默认值，helm 部署默认生成 -saas / -backend
# 是否开启 DB 访问 trace（开启后 span 数量会明显增多）
BKAPP_OTEL_INSTRUMENT_DB_API = get_type_env(key="BKAPP_OTEL_INSTRUMENT_DB_API", default=False, _type=bool)
# 配置采样策略，默认值为 `parentbased_always_off`，可选值 `always_on`，`always_off`, `parentbased_always_on`,
# `parentbased_always_off`, `traceidratio`, `parentbased_traceidratio`
BKAPP_OTEL_SAMPLER = get_type_env(key="BKAPP_OTEL_SAMPLER", default="parentbased_always_on", _type=str)
# 监控上报配置项
BKAPP_OTEL_BK_DATA_TOKEN = get_type_env(key="BKAPP_OTEL_BK_DATA_TOKEN", _type=str)
BKAPP_OTEL_GRPC_URL = get_type_env(key="BKAPP_OTEL_GRPC_URL", _type=str)

# ===============================================================================
# 第三方依赖
# ===============================================================================
BK_CC_HOST = get_type_env(key="BK_CC_HOST", default="", _type=str)

# APIGW API 地址模板，在 PaaS 3.0 部署的应用，可从环境变量中获取 BK_API_URL_TMPL
BK_API_URL_TMPL = get_type_env(key="BK_API_URL_TMPL", default=BK_COMPONENT_API_URL + "/api/{api_name}", _type=str)

# esb 外网域名, Helm 部署时从环境变量中获取 BK_PAAS_OUTER_HOST , 二进制部署时使用 BK_PAAS_HOST
BK_COMPONENT_API_OUTER_URL = get_type_env(key="BK_PAAS_OUTER_HOST", default="", _type=str) or get_type_env(
    key="BK_PAAS_HOST", default=BK_COMPONENT_API_URL, _type=str
)

# 蓝鲸根域名
BK_DOMAIN = get_type_env(key="BK_DOMAIN", default="", _type=str)

# 导航栏开源社区地址
BKAPP_NAV_OPEN_SOURCE_URL = get_type_env(
    key="BKAPP_NAV_OPEN_SOURCE_URL", default="https://github.com/TencentBlueKing/bk-nodeman", _type=str
)
# 导航栏技术支持地址
BKAPP_NAV_HELPER_URL = get_type_env(
    key="BKAPP_NAV_HELPER_URL", default="https://wpa1.qq.com/KziXGWJs?_type=wpa&qidian=true", _type=str
)
