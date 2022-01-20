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
import os

import yaml
from django.conf import settings


class BaseInfoHandler:
    @staticmethod
    def version():
        version_info = {
            "app_code": settings.APP_CODE,
            "module": ("default", "backend")[settings.BK_BACKEND_CONFIG is True],
        }
        app_yaml_path = os.path.join(settings.PROJECT_ROOT, "app.yml")
        # 获取版本信息
        with open(file=app_yaml_path, encoding="utf-8") as dev_yaml_fs:
            app_yaml = yaml.safe_load(dev_yaml_fs)
        version_info["version"] = app_yaml["version"]
        return version_info
