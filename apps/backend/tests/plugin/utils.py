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
import copy
import json

from django.test import Client, TestCase
from django.test.client import MULTIPART_CONTENT

from apps.node_man import models

DEFAULT_PLUGIN_NAME = "test_plugin"

PKG_PARAMS = {
    "id": 1,
    "pkg_name": "test_plugin-1.0.0.tgz",
    "version": "1.0.0",
    "module": "gse_plugin",
    "project": DEFAULT_PLUGIN_NAME,
    "pkg_size": 0,
    "pkg_path": "",
    "md5": "",
    "pkg_mtime": "",
    "pkg_ctime": "",
    "location": "",
    "os": "linux",
    "cpu_arch": "x86_64",
    "is_release_version": True,
    "is_ready": True,
}

GSE_PLUGIN_DESC = {
    "name": DEFAULT_PLUGIN_NAME,
    "description": "测试插件啊",
    "scenario": "测试",
    "category": "external",
    "launch_node": "all",
    "config_file": "config.yaml",
    "config_format": "yaml",
    "use_db": False,
}


class PluginTestObjFactory:
    @classmethod
    def replace_obj_attr_values(cls, obj, obj_attr_values):
        # 原地修改
        if obj_attr_values is None:
            return obj
        for attr, value in obj_attr_values.items():
            if attr not in obj:
                continue
            obj[attr] = value

    @classmethod
    def get_obj(cls, init_params, model, obj_attr_values, is_obj):
        params = copy.deepcopy(init_params)
        cls.replace_obj_attr_values(params, obj_attr_values)
        if not is_obj:
            params.pop("id", None)
        return model(**params) if is_obj else params

    @classmethod
    def bulk_create(cls, params_group, model):
        return model.objects.bulk_create([model(**params) for params in params_group])

    @classmethod
    def pkg_obj(cls, obj_attr_values=None, is_obj=False):
        return cls.get_obj(PKG_PARAMS, models.Packages, obj_attr_values, is_obj)

    @classmethod
    def gse_plugin_desc_obj(cls, obj_attr_values=None, is_obj=False):
        return cls.get_obj(GSE_PLUGIN_DESC, models.GsePluginDesc, obj_attr_values, is_obj)

    @classmethod
    def batch_create_pkg(cls, packages):
        return cls.bulk_create(packages, models.Packages)

    @classmethod
    def batch_create_plugin_desc(cls, plugin_descs):
        return cls.bulk_create(plugin_descs, models.GsePluginDesc)


class UtilsClient(Client, TestCase):
    def success_assert(self, response):
        response_data = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response_data["result"])
        return response_data

    def get(self, path, data=None, follow=False, secure=False, **extra):
        response = super().get(path, data, follow, secure, **extra)
        return self.success_assert(response)

    def post(self, path, data=None, content_type=MULTIPART_CONTENT, follow=False, secure=False, **extra):
        response = super().post(path, data, content_type, follow, secure, **extra)
        return self.success_assert(response)
