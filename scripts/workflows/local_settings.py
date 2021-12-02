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
            "NAME": os.getenv("MYSQL_TEST_NAME"),
            "CHARSET": "utf8mb4",
            "COLLATION": "utf8mb4_general_ci",
        },
    },
}

DEBUG = True
BK_IAM_SKIP = True
USE_IAM = False
