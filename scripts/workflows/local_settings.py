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

# 本地开发数据库设置
# USE FOLLOWING SQL TO CREATE THE DATABASE NAMED APP_CODE
# SQL: CREATE DATABASE `log-search-v2` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci; # noqa: E501
import os

import requests

from config import BASE_DIR

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        # 新版插件管理数据库
        "NAME": os.getenv("MYSQL_NAME"),
        "USER": os.getenv("MYSQL_USER"),  # 本地数据库账号
        "PASSWORD": os.getenv("MYSQL_PASSWORD"),  # 本地数据库密码
        "HOST": os.getenv("MYSQL_HOST"),
        "PORT": os.getenv("MYSQL_PORT"),
        "OPTIONS": {
            # Tell MySQLdb to connect with 'utf8mb4' character set
            "charset": "utf8mb4",
        },
        "COLLATION": "utf8mb4_general_ci",
        "TEST": {
            "NAME": "bk_nodeman_test",
            "CHARSET": "utf8mb4",
            "COLLATION": "utf8mb4_general_ci",
        },
    },
}

DEBUG = True
# MIDDLEWARE = (
#     # request instance provider
#     'blueapps.middleware.request_provider.RequestProvider',
#     'django.contrib.sessions.middleware.SessionMiddleware',
#     'django.middleware.common.CommonMiddleware',
#     'django.contrib.auth.middleware.AuthenticationMiddleware',
#     'django.contrib.messages.middleware.MessageMiddleware',
#     'blueapps.middleware.xss.middlewares.CheckXssMiddleware',
#     # 跨域检测中间件， 默认关闭
#     # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
#     'django.middleware.security.SecurityMiddleware',
#     # 蓝鲸静态资源服务
#     'whitenoise.middleware.WhiteNoiseMiddleware',
#     # Auth middleware
#     # 'blueapps.account.middlewares.BkJwtLoginRequiredMiddleware',
#     # 'blueapps.account.middlewares.WeixinLoginRequiredMiddleware',
#     'blueapps.account.middlewares.LoginRequiredMiddleware',
#     # exception middleware
#     'blueapps.core.exceptions.middleware.AppExceptionMiddleware',
#
#     # 自定义中间件
#     'django.middleware.locale.LocaleMiddleware',
#     'apps.middlewares.CommonMid',
#     'apps.middlewares.UserLocalMiddleware',
# )
# ENGINE_ZOMBIE_PROCESS_DOCTORS = [
#     {
#         'class': 'pipeline.engine.health.zombie.doctors.RunningNodeZombieDoctor',
#         'config': {
#             'max_stuck_time': 10,
#             'detect_wait_callback_proc': True
#         }
#     }
# ]
# ENGINE_ZOMBIE_PROCESS_HEAL_CRON = {'minute': '*/1'}
BK_OFFICIAL_PLUGINS_INIT_PATH = os.path.join(BASE_DIR, "official_plugin")
# UPLOAD_PATH = '/tmp'
# NGINX_DOWNLOAD_PATH = '/tmp/download'

BROKER_URL = os.getenv("BROKER_URL")

if __name__ == "__main__":
    task_id = "7e32ca3a1aa431599e30696bc536df22"
    for i in range(5):
        requests.post(
            "http://127.0.0.1:8000/backend/report_log/",
            {
                "task_id": task_id,
                "logs": [
                    {
                        "timestamp": "1576826749",
                        "level": "INFO",
                        "step": "check_deploy_result",
                        "log": i,
                        "status": "DONE",
                    },
                ],
            },
        )


# celery redbeat config
REDBEAT_REDIS_URL = os.getenv("BROKER_URL")
REDIS = {
    "host": os.getenv("REDIS_HOST"),
    "port": os.getenv("REDIS_PORT"),
    "password": os.getenv("REDIS_PASSWORD"),
    "service_name": "master",
    "mode": "single",  # 哨兵模式，可选 single, cluster, replication
}

REDBEAT_KEY_PREFIX = "nodeman"
