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

from django.apps import AppConfig
from django.utils.functional import SimpleLazyObject
from django.utils.module_loading import import_string

"""
API 统一调用模块，使用方式，举例
>>> from common.api import DataQueryApi
>>> DataQueryApi.query({})
"""


def new_api_module(module_name, api_name, module_dir="modules"):
    mod = "common.api.{modules}.{mod}.{api}".format(modules=module_dir, mod=module_name, api=api_name)
    return import_string(mod)()


# 对请求模块设置懒加载机制，避免项目启动出现循环引用，或者 model 提前加载

# 蓝鲸平台模块域名
JobApi = SimpleLazyObject(lambda: new_api_module("job", "_JobApi"))
GseApi = SimpleLazyObject(lambda: new_api_module("gse", "_GseApi"))
SopsApi = SimpleLazyObject(lambda: new_api_module("sops", "_SopsApi"))
# CMSI
CmsiApi = SimpleLazyObject(lambda: new_api_module("cmsi", "_CmsiApi"))

# 节点管理
NodeApi = SimpleLazyObject(lambda: new_api_module("bk_node", "_BKNodeApi"))

# ESB
EsbApi = SimpleLazyObject(lambda: new_api_module("esb", "_ESBApi"))

__all__ = [
    "JobApi",
    "GseApi",
    "SopsApi",
    "CmsiApi",
    "NodeApi",
]


class ApiConfig(AppConfig):
    name = "common.api"
    verbose_name = "ESB_API"

    def ready(self):
        pass


default_app_config = "common.api.ApiConfig"
