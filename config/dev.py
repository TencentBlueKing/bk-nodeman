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

from config import APP_CODE, RUN_VER

if RUN_VER == "open":
    from blueapps.patch.settings_open_saas import *  # noqa
else:
    from blueapps.patch.settings_paas_services import *  # noqa

BK_IAM_INNER_HOST = os.getenv("BK_IAM_V3_INNER_HOST")
BK_IAM_MIGRATION_JSON_PATH = os.path.join(PROJECT_ROOT, "support-files/bkiam")
BK_IAM_RESOURCE_API_HOST = os.getenv("BKAPP_IAM_RESOURCE_API_HOST", "{}{}".format(BK_PAAS_INNER_HOST, SITE_URL))
BK_IAM_SKIP = True

# 本地开发环境
RUN_MODE = "DEVELOP"

# APP本地静态资源目录
STATIC_URL = "/static/"

# APP静态资源目录url
# REMOTE_STATIC_URL = '%sremote/' % STATIC_URL

# Celery 消息队列设置 RabbitMQ
# BROKER_URL = 'amqp://guest:guest@localhost:5672//'
# Celery 消息队列设置 Redis
BROKER_URL = "redis://localhost:6379/0"

DEBUG = True

# 本地开发数据库设置
# USE FOLLOWING SQL TO CREATE THE DATABASE NAMED APP_CODE
# SQL: CREATE DATABASE `log-search-v2` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci; # noqa: E501
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": APP_CODE,
        "USER": "root",
        "PASSWORD": "",
        "HOST": "127.0.0.1",
        "PORT": "3306",
    },
}

# ==============================================================================
# REDIS
# ==============================================================================
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = os.environ.get("REDIS_PORT", 6379)
REDIS_PASS = os.environ.get("REDIS_PASS", "")

REDIS = {
    "host": REDIS_HOST,
    "port": REDIS_PORT,
    "password": REDIS_PASS,
}


# 多人开发时，无法共享的本地配置可以放到新建的 local_settings.py 文件中
# 并且把 local_settings.py 加入版本管理忽略文件中
try:
    from config.local_settings import *  # noqa
except ImportError:
    pass


# 本地开发后台不启用用户校验，并默认用超级管理员作为用户
BK_BACKEND_CONFIG = bool(os.getenv("BK_BACKEND_CONFIG", None))
if BK_BACKEND_CONFIG:

    # 移除登录模块，添加超级管理员中间件
    LOGIN_MIDDLEWARE = "blueapps.account.middlewares.LoginRequiredMiddleware"
    if LOGIN_MIDDLEWARE in MIDDLEWARE:
        MIDDLEWARE = (
            MIDDLEWARE[0 : MIDDLEWARE.index(LOGIN_MIDDLEWARE)]
            + ("apps.middlewares.LocalDevSuperuserMiddleware",)
            + MIDDLEWARE[MIDDLEWARE.index(LOGIN_MIDDLEWARE) + 1 :]
        )
