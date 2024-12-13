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
import copy
import os
import shutil
import tarfile
import uuid
from collections import ChainMap
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import mock
from django.conf import settings

from apps.backend.plugin import tasks
from apps.core.files import base, core_files_constants, storage
from apps.mock_data import common_unit
from apps.node_man import constants, models
from apps.utils import files

# 测试文件根路径
from apps.utils.enum import EnhanceEnum
from apps.utils.unittest.testcase import CustomAPITestCase

# 插件包yaml配置
PROJECT_YAML_CONTENT = """
name: "{plugin_name}"
version: "{package_version}"
description: "{description}"
description_en: "{description_en}"
scenario: "{scenario}"
scenario_en: "{scenario_en}"
category: {category}
config_format: {config_format}
config_file: {config_file}
use_db: {use_db}
is_binary: {is_binary}
launch_node: {launch_node}
auto_launch: {auto_launch}
auto_type: {auto_type}
config_templates:
- plugin_version: "{package_version}"
  name: test_plugin.conf
  version: {package_version}
  file_path: etc
  format: {config_format}
  source_path: etc/{plugin_name}.conf.tpl
  is_main_config: 1
  variables:
    title: variables
    type: object
    required: True
    properties:
      token:
        title: token
        type: string
        required: True
      logVerbosity:
        title: logVerbosity
        type: number
        default: 5
        required: False
      tempDir:
        title: tempDir
        type: string
        required: False
      uid:
        title: uid
        type: string
        required: False
      labels:
        title: labels
        type: array
        items:
          title: label
          type: object
          required: False
          properties:
            key:
              title: 键
              type: string
            value:
              title: 值
              type: string
      apps:
        title: apps
        type: array
        items:
          title: named_label
          type: object
          properties:
            name:
              title: name
              type: string
              required: True
            uid:
              title: uid
              type: string
              required: False
            labels:
              title: labels
              type: array
              required: False
              items:
                title: label
                type: object
                required: False
                properties:
                  key:
                    title: 键
                    type: string
                  value:
                    title: 值
                    type: string
- plugin_version: "{package_version}"
  name: child.conf
  version: {package_version}
  file_path: etc/{plugin_name}
  format: {config_format}
  source_path: etc/child.conf.tpl
control:
  start: "./start.sh {plugin_name}"
  stop: "./stop.sh {plugin_name}"
  restart: "./restart.sh {plugin_name}"
  version: "./{plugin_name} -v"
  reload: "./{plugin_name} -s reload"
  health_check: "./{plugin_name} -z"
node_manage_control:
  package_update: false
  package_remove: false
  plugin_install: false
  plugin_update: false
  plugin_uninstall: false
  plugin_upgrade: false
  plugin_remove: false
  plugin_restart: false
"""

PROJECT_YAML_CONTENT_CONFIG_TEMPLATE_VARIABLES = {
    "title": "variables",
    "type": "object",
    "required": True,
    "properties": {
        "token": {"title": "token", "type": "string", "required": True},
        "logVerbosity": {"title": "logVerbosity", "type": "number", "required": False, "default": 5},
        "tempDir": {"title": "tempDir", "type": "string", "required": False},
        "uid": {"title": "uid", "type": "string", "required": False},
        "labels": {
            "title": "labels",
            "type": "array",
            "items": {
                "title": "label",
                "type": "object",
                "required": False,
                "properties": {"key": {"title": "键", "type": "string"}, "value": {"title": "值", "type": "string"}},
            },
        },
        "apps": {
            "title": "apps",
            "type": "array",
            "items": {
                "title": "named_label",
                "type": "object",
                "properties": {
                    "name": {"title": "name", "type": "string", "required": True},
                    "uid": {"title": "uid", "type": "string", "required": False},
                    "labels": {
                        "title": "labels",
                        "type": "array",
                        "required": False,
                        "items": {
                            "title": "label",
                            "type": "object",
                            "required": False,
                            "properties": {
                                "key": {"title": "键", "type": "string"},
                                "value": {"title": "值", "type": "string"},
                            },
                        },
                    },
                },
            },
        },
    },
}

# 插件名称
PLUGIN_NAME = common_unit.plugin.PLUGIN_NAME

# 插件包版本
PACKAGE_VERSION = common_unit.plugin.PACKAGE_VERSION

# 是否为第三方插件
IS_EXTERNAL = False

# models.GsePluginDesc 创建参数
GSE_PLUGIN_DESC_PARAMS = common_unit.plugin.GSE_PLUGIN_DESC_MODEL_DATA

# models.Packages 创建参数
PKG_PARAMS = common_unit.plugin.PACKAGES_MODEL_DATA


class PathSettingOverwrite(EnhanceEnum):
    EXPORT_PATH = "EXPORT_PATH"
    UPLOAD_PATH = "UPLOAD_PATH"
    DOWNLOAD_PATH = "DOWNLOAD_PATH"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        raise NotImplementedError()

    @classmethod
    def get_setting_name__path_suffix_map(cls) -> Dict[str, str]:
        return {cls.EXPORT_PATH.value: "export", cls.UPLOAD_PATH.value: "upload", cls.DOWNLOAD_PATH.value: "download"}


class PluginTestObjFactory:
    @classmethod
    def get_project_yaml_content(cls, **kwargs):
        return PROJECT_YAML_CONTENT.format(
            **dict(
                ChainMap(
                    kwargs, GSE_PLUGIN_DESC_PARAMS, {"plugin_name": PLUGIN_NAME, "package_version": PACKAGE_VERSION}
                )
            )
        )

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
        return cls.get_obj(GSE_PLUGIN_DESC_PARAMS, models.GsePluginDesc, obj_attr_values, is_obj)

    @classmethod
    def batch_create_pkg(cls, packages):
        return cls.bulk_create(packages, models.Packages)

    @classmethod
    def batch_create_plugin_desc(cls, plugin_desc):
        return cls.bulk_create(plugin_desc, models.GsePluginDesc)


class PluginBaseTestCase(CustomAPITestCase):
    TMP_DIR: str = None
    PLUGIN_ARCHIVE_NAME: str = None
    PLUGIN_ARCHIVE_PATH: str = None
    PLUGIN_ARCHIVE_MD5: str = None
    OS_CPU_CHOICES = [
        (constants.OsType.LINUX.lower(), constants.CpuType.x86_64),
        (constants.OsType.WINDOWS.lower(), constants.CpuType.x86),
    ]

    PLUGIN_CHILD_DIR_NAME: str = (constants.PluginChildDir.OFFICIAL.value, constants.PluginChildDir.EXTERNAL.value)[
        IS_EXTERNAL
    ]

    FILE_OVERWRITE = True

    OVERWRITE_OBJ__KV_MAP = {
        settings: {
            "FILE_OVERWRITE": FILE_OVERWRITE,
            "STORAGE_TYPE": core_files_constants.StorageType.FILE_SYSTEM.value,
        },
        base.StorageFileOverwriteMixin: {"file_overwrite": FILE_OVERWRITE},
    }

    @classmethod
    def setUpClass(cls):

        mock.patch("apps.backend.plugin.tasks.package_task.delay", tasks.package_task).start()
        mock.patch("apps.backend.plugin.tasks.export_plugin.delay", tasks.export_plugin).start()

        cls.TMP_DIR = files.mk_and_return_tmpdir()
        cls.PLUGIN_ARCHIVE_NAME = f"{PLUGIN_NAME}-{PACKAGE_VERSION}.tgz"
        cls.PLUGIN_ARCHIVE_PATH = os.path.join(cls.TMP_DIR, cls.PLUGIN_ARCHIVE_NAME)

        setting_name__path_map = {
            setting_name: os.path.join(
                cls.TMP_DIR, PathSettingOverwrite.get_setting_name__path_suffix_map()[setting_name]
            )
            for setting_name in PathSettingOverwrite.list_member_values()
        }
        cls.OVERWRITE_OBJ__KV_MAP = cls.OVERWRITE_OBJ__KV_MAP or {}
        cls.OVERWRITE_OBJ__KV_MAP[settings] = {**cls.OVERWRITE_OBJ__KV_MAP.get(settings, {}), **setting_name__path_map}

        super().setUpClass()

    @classmethod
    def setUpTestData(cls):
        storage._STORAGE_OBJ_CACHE = {}
        super().setUpTestData()

    def setUp(self):
        # 设置请求附加参数
        self.client.common_request_data = {
            "bk_app_code": settings.APP_CODE,
            "bk_username": settings.SYSTEM_USE_API_ACCOUNT,
        }

        for setting_name in PathSettingOverwrite.list_member_values():
            overwrite_path = os.path.join(
                self.TMP_DIR, PathSettingOverwrite.get_setting_name__path_suffix_map()[setting_name]
            )
            # exist_ok 目录存在直接跳过，不抛出 FileExistsError
            os.makedirs(overwrite_path, exist_ok=True)

        product_tmp_dir = self.gen_test_plugin_files(
            project_yaml_content=PluginTestObjFactory.get_project_yaml_content(), os_cpu_choices=self.OS_CPU_CHOICES
        )
        self.pack_plugin(product_tmp_dir=product_tmp_dir)
        self.PLUGIN_ARCHIVE_MD5 = files.md5sum(name=self.PLUGIN_ARCHIVE_PATH)
        super().setUp()

    @classmethod
    def gen_test_plugin_files(cls, project_yaml_content: str, os_cpu_choices: List[Tuple[str, str]]):
        product_tmp_dir = os.path.join(cls.TMP_DIR, uuid.uuid4().hex)
        for package_os, cpu_arch in os_cpu_choices:
            pkg_info_dir_path = os.path.join(product_tmp_dir, f"{cls.PLUGIN_CHILD_DIR_NAME}_{package_os}_{cpu_arch}")
            pkg_dir_path = os.path.join(pkg_info_dir_path, PLUGIN_NAME)
            pkg_config_dir_path = os.path.join(pkg_dir_path, "etc")
            pkg_executable_dir_path = os.path.join(pkg_dir_path, "bin")

            # 创建可执行文件 / 配置模板 目录
            os.makedirs(pkg_config_dir_path)
            os.makedirs(pkg_executable_dir_path)

            # 创建可执行文件
            with open(os.path.join(pkg_executable_dir_path, PLUGIN_NAME), "w"):
                pass

            # 写入 project.yaml
            with open(os.path.join(pkg_dir_path, "project.yaml"), "w", encoding="utf-8") as project_yaml_fs:
                project_yaml_fs.write(project_yaml_content)

            # 创建配置模板
            with open(os.path.join(pkg_config_dir_path, f"{PLUGIN_NAME}.conf.tpl"), "w"):
                pass
            with open(os.path.join(pkg_config_dir_path, f"{PLUGIN_NAME}.conf"), "w"):
                pass
            with open(os.path.join(pkg_config_dir_path, "child.conf.tpl"), "w"):
                pass

        return product_tmp_dir

    @classmethod
    def pack_plugin(cls, product_tmp_dir: str):
        # 插件打包
        with tarfile.open(cls.PLUGIN_ARCHIVE_PATH, "w:gz") as tf:
            tf.add(product_tmp_dir, arcname=".", recursive=True)

    def tearDown(self):
        if os.path.exists(self.TMP_DIR):
            shutil.rmtree(self.TMP_DIR)
        super().tearDown()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.TMP_DIR):
            shutil.rmtree(cls.TMP_DIR)

        super().tearDownClass()

    def upload_plugin(self, file_local_path: Optional[str] = None) -> Dict[str, Any]:
        file_local_path = file_local_path or self.PLUGIN_ARCHIVE_PATH
        md5 = files.md5sum(file_local_path)
        upload_result = self.client.post(
            path="/backend/package/upload/",
            data={
                "module": "gse_plugin",
                "md5": md5,
                # nginx 计算并回调的额外参数
                "file_name": self.PLUGIN_ARCHIVE_NAME,
                "file_local_md5": md5,
                "file_local_path": file_local_path,
            },
            format=None,
        )["data"]
        file_name = upload_result["name"]
        # 插件会保存到 UPLOAD_PATH
        self.assertTrue(
            models.UploadPackage.objects.filter(
                file_name=file_name, file_path=os.path.join(settings.UPLOAD_PATH, file_name)
            ).exists()
        )
        return upload_result

    def register_plugin(self, file_name: str, select_pkg_relative_paths: Optional[List[str]] = None):
        base_query_params = {
            "file_name": file_name,
            "is_release": True,
            "is_template_load": True,
        }
        if select_pkg_relative_paths is not None:
            base_query_params["select_pkg_relative_paths"]: select_pkg_relative_paths

        self.client.post(path="/backend/api/plugin/create_register_task/", data=base_query_params)


class CustomBKRepoMockStorage(storage.CustomBKRepoStorage):
    mock_storage: storage.AdminFileSystemStorage = None

    def __init__(
        self,
        root_path=None,
        username=None,
        password=None,
        project_id=None,
        bucket=None,
        endpoint_url=None,
        file_overwrite=None,
    ):
        self.mock_storage = storage.AdminFileSystemStorage(file_overwrite=file_overwrite)
        super().__init__(
            root_path=root_path,
            username=username,
            password=password,
            project_id=project_id,
            bucket=bucket,
            endpoint_url=endpoint_url,
            file_overwrite=file_overwrite,
        )

    def path(self, name):
        return self.mock_storage.path(name)

    def _open(self, name, mode="rb"):
        return self.mock_storage._open(name, mode)

    def _save(self, name, content):
        return self.mock_storage._save(name, content)

    def exists(self, name):
        return self.mock_storage.exists(name)

    def size(self, name):
        return self.mock_storage.size(name)

    def url(self, name):
        return self.mock_storage.url(name)

    def delete(self, name):
        return self.mock_storage.delete(name)

    def listdir(self, path):
        return self.mock_storage.listdir(path)


OVERWRITE_OBJ__KV_MAP = {
    settings: {
        "FILE_OVERWRITE": True,
        "STORAGE_TYPE": core_files_constants.StorageType.BLUEKING_ARTIFACTORY.value,
        "BKREPO_USERNAME": "username",
        "BKREPO_PASSWORD": "blueking",
        "BKREPO_PROJECT": "project",
        "BKREPO_BUCKET": "private",
        "BKREPO_PUBLIC_BUCKET": "public",
        "BKREPO_ENDPOINT_URL": "http://127.0.0.1",
    },
    CustomBKRepoMockStorage: {"file_overwrite": True},
    base.StorageFileOverwriteMixin: {"file_overwrite": True},
}
