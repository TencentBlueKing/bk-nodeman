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
import os
import platform
import shutil
import tarfile
import uuid
from collections import ChainMap
from enum import Enum
from typing import Dict, List, Tuple

import mock
from django.conf import settings

from apps.backend.plugin import tasks
from apps.core.files import storage
from apps.node_man import constants, models
from apps.utils import files

# 测试文件根路径
from apps.utils.enum import EnhanceEnum
from apps.utils.unittest.testcase import CustomAPITestCase

TEST_ROOT = ("/tmp", "c:/")[platform.system().upper() == constants.OsType.WINDOWS]

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
config_templates:
- plugin_version: "{package_version}"
  name: test_plugin.conf
  version: {package_version}
  file_path: etc
  format: {config_format}
  source_path: etc/{plugin_name}.conf.tpl
  is_main_config: 1
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

# 插件名称
PLUGIN_NAME = "test_plugin"

# 插件包版本
PACKAGE_VERSION = "1.0.1"

# 是否为第三方插件
IS_EXTERNAL = False

# models.GsePluginDesc 创建参数
GSE_PLUGIN_DESC_PARAMS = {
    "name": PLUGIN_NAME,
    "description": "单元测试插件",
    "description_en": "plugin for unittest",
    "scenario": "单元测试插件",
    "scenario_en": "plugin for unittest",
    "category": constants.CategoryType.official,
    "launch_node": "all",
    "config_file": "test_plugin.conf",
    "config_format": "yaml",
    "use_db": 0,
    "is_binary": 1,
    "auto_launch": 0,
}

# models.Packages 创建参数
PKG_PARAMS = {
    "id": 1,
    "pkg_name": f"{PLUGIN_NAME}-{PACKAGE_VERSION}.tgz",
    "version": PACKAGE_VERSION,
    "module": "gse_plugin",
    "project": PLUGIN_NAME,
    "pkg_size": 0,
    "pkg_path": "",
    "md5": "",
    "pkg_mtime": "",
    "pkg_ctime": "",
    "location": "",
    "os": constants.OsType.LINUX.lower(),
    "cpu_arch": constants.CpuType.x86_64,
    "is_release_version": True,
    "is_ready": True,
}


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
