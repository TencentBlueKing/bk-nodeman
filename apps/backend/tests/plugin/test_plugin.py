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
from __future__ import absolute_import, print_function, unicode_literals

import os
import platform
import shutil
import tarfile
import uuid

import mock
from django.conf import settings
from django.core.management import call_command
from django.test import TestCase

from apps.backend.plugin.tasks import export_plugin, package_task, run_pipeline
from apps.backend.tests.plugin import utils
from apps.backend.tests.plugin.test_plugin_status_change import TestApiBase
from apps.node_man.models import (
    DownloadRecord,
    GsePluginDesc,
    Packages,
    PluginConfigTemplate,
    ProcControl,
    UploadPackage,
)

# TODO: 后续分拆该文件

# 全局使用的mock
mock.patch("apps.backend.plugin.tasks.export_plugin", delay=export_plugin).start()
mock.patch("apps.backend.plugin.tasks.package_task", delay=package_task).start()
mock.patch("apps.backend.plugin.tasks.run_pipeline.delay", delay=run_pipeline).start()

TEST_ROOT = "c:/" if platform.system() == "Windows" else "/tmp"


class PluginTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        GsePluginDesc.objects.create(
            **{
                "name": "test1",
                "description": "测试插件啊",
                "scenario": "测试",
                "category": "external",
                "launch_node": "all",
                "config_file": "config.yaml",
                "config_format": "yaml",
                "use_db": False,
            }
        )

        Packages.objects.create(
            pkg_name="test1.tar",
            version="1.0.1",
            module="gse_plugin",
            project="test1",
            pkg_size=10255,
            pkg_path="/data/bkee/miniweb/download/windows/x86_64",
            location="http://127.0.0.1/download/windows/x86_64",
            md5="a95c530a7af5f492a74499e70578d150",
            pkg_ctime="2019-05-05 11:54:28.070771",
            pkg_mtime="2019-05-05 11:54:28.070771",
            os="windows",
            cpu_arch="x86_64",
            is_release_version=False,
            is_ready=True,
        )

    def test_one(self):
        assert GsePluginDesc.objects.all().count() == 1

    def test_two(self):
        pass


class TestPackageFunction(TestApiBase):
    temp_path = os.path.join(TEST_ROOT, uuid.uuid4().hex)
    tarfile_name = "tarfile.tgz"
    tarfile_path = os.path.join(temp_path, tarfile_name)
    export_path = os.path.join(temp_path, "export")
    upload_path = os.path.join(temp_path, "upload")

    plugin_name = "test_plugin"

    config_content = """
  name: "test_plugin"
  version: "1.0.1"
  description: "用于采集主机基础性能数据，包含CPU,内存，磁盘，⽹络等数据"
  description_en: "用于采集主机基础性能数据，包含CPU,内存，磁盘，⽹络等数据"
  scenario: "CMDB上的是实时数据，蓝鲸监控-主机监控中的基础性能数据"
  scenario_en: "CMDB上的是实时数据，蓝鲸监控-主机监控中的基础性能数据"
  category: official
  config_file: basereport.conf
  multi_config: True
  config_file_path: ""
  config_format: yaml
  auto_launch: true
  launch_node: proxy
  upstream:
     bkmetric
  dependences:
     gse_agent: "1.2.0"
     bkmetric: "1.6.0"
  config_templates:
    - plugin_version: "*"
      name: child.conf
      version: 2.0.1
      file_path: etc/child
      format: yaml
      source_path: etc/child.conf.tpl
    - plugin_version: "*"
      name: test_plugin.conf
      version: 1.0.2
      file_path: etc/main
      format: yaml
      source_path: etc/test_plugin.main.conf.tpl
      is_main_config: 1
  control:
     start: "./start.sh %name"
     stop: "./stop.sh %name"
     restart: "./restart.sh %name"
     version: "./%name -v"
     reload: "./%name -s reload"
     health_check: "./%name -z"
  node_manage_control:
     package_update: false
     package_remove: false
     plugin_install: false
     plugin_update: false
     plugin_uninstall: false
     plugin_upgrade: false
     plugin_remove: false
     plugin_restart: false
  process_name: "test_process"
"""

    def setUp(self):
        """测试启动初始化配置"""
        # 1. 准备一个yaml配置文件

        # 2. 创建一个打包文件，包含两层内容，一个linux，一个windows
        temp_file_path = os.path.join(self.temp_path, "temp_folder")
        if not os.path.exists(self.temp_path):
            os.mkdir(self.temp_path)
        if not os.path.exists(temp_file_path):
            os.mkdir(temp_file_path)
        if not os.path.exists(self.export_path):
            os.mkdir(self.export_path)
        if not os.path.exists(self.upload_path):
            os.mkdir(self.upload_path)
        for package_os, cpu_arch in (("linux", "x86_64"), ("windows", "x86")):
            current_path = os.path.join(temp_file_path, "external_plugins_{}_{}".format(package_os, cpu_arch))
            os.mkdir(current_path)

            plugin_path = os.path.join(current_path, self.plugin_name)
            os.mkdir(plugin_path)

            config_path = os.path.join(plugin_path, "etc")
            os.mkdir(config_path)

            f1 = open(os.path.join(plugin_path, "plugin"), "w")
            f1.close()
            f2 = open(os.path.join(plugin_path, "project.yaml"), "w", encoding="utf-8")
            f2.write(self.config_content)
            f2.close()

            main_config = open(os.path.join(config_path, "test_plugin.main.conf.tpl"), "w")
            main_config.close()
            child_config = open(os.path.join(config_path, "child.conf.tpl"), "w")
            child_config.close()

        with tarfile.open(self.tarfile_path, "w:gz") as tfile:
            # self.temp_path/temp_folder下的所有文件放入temp_file_path文件下, arcname表示目标目录的目标路径
            tfile.add(temp_file_path, arcname=".", recursive=True)

        # nginx的模拟路径
        settings.NGINX_DOWNLOAD_PATH = self.temp_path
        settings.UPLOAD_PATH = self.upload_path
        settings.EXPORT_PATH = self.export_path

    def tearDown(self):
        """测试清理配置"""

        shutil.rmtree(self.temp_path)
        # TODO: 文件上传时把包都临时放在了/tmp/ 注册时从tmp读取，但由于文件二级目录由uuid.uuid4().hex生成，无法清除
        # 下列只是清除了注册时的临时打包文件保证测试正常执行，但是上传时的文件并没有删除，有堆积风险
        # 不建议直接清/tmp/，考虑mock `uuid.uuid4().hex`，生成一个可见目录，采用shutil.rmtree(path)清除
        tmp_clear_files = ["/tmp/test_plugin-1.0.1-windows-x86.tgz", "/tmp/test_plugin-1.0.1-linux-x86_64.tgz"]
        for file in tmp_clear_files:
            if os.path.exists(file):
                os.remove(file)

    def test_create_upload_record_and_register(self):
        """测试创建上传包记录功能"""

        # 插件包注册后存放地址
        windows_file_path = os.path.join(settings.NGINX_DOWNLOAD_PATH, "windows", "x86", "test_plugin-1.0.1.tgz")
        linux_file_path = os.path.join(settings.NGINX_DOWNLOAD_PATH, "linux", "x86_64", "test_plugin-1.0.1.tgz")

        # 验证创建前此时文件不存在
        self.assertFalse(os.path.exists(linux_file_path))
        self.assertFalse(os.path.exists(windows_file_path))

        UploadPackage.create_record(
            module="gse_plugin",
            file_path=self.tarfile_path,
            md5="abcefg",
            operator="haha_test",
            source_app_code="bk_nodeman",
            file_name="tarfile.tgz",
        )

        # 判断路径的转移登录等是否符合预期
        self.assertEqual(
            UploadPackage.objects.filter(
                file_name=self.tarfile_name,
                file_path=os.path.join(settings.UPLOAD_PATH, self.tarfile_name),
            ).count(),
            1,
        )
        self.assertTrue(os.path.exists(os.path.join(settings.UPLOAD_PATH, self.tarfile_name)))

        # 测试单独注册插件包功能
        upload_object = UploadPackage.objects.get(file_name=self.tarfile_name)
        package_object_list = upload_object.create_package_records(is_release=True)

        self.assertEqual(
            GsePluginDesc.objects.get(name="test_plugin").node_manage_control,
            {
                "package_update": False,
                "package_remove": False,
                "plugin_install": False,
                "plugin_update": False,
                "plugin_uninstall": False,
                "plugin_upgrade": False,
                "plugin_remove": False,
                "plugin_restart": False,
            },
        )
        # 判断数量正确
        self.assertEqual(len(package_object_list), 2)

        # 判断写入DB数据正确
        # 1. 进程控制信息
        for package in package_object_list:
            process_control = ProcControl.objects.get(plugin_package_id=package.id)
            self.assertEqual(process_control.os, package.os)
            self.assertEqual(process_control.start_cmd, "./start.sh %name")
            self.assertEqual(
                process_control.install_path,
                "/usr/local/gse" if package.os != "windows" else r"C:\gse",
            )
            self.assertEqual(process_control.port_range, "")
            self.assertEqual(process_control.process_name, "test_process")

        # 2. 包记录信息（window， linux及版本号）
        Packages.objects.get(
            pkg_name="test_plugin-1.0.1.tgz", os="windows", version="1.0.1", cpu_arch="x86", creator="admin"
        )
        Packages.objects.get(
            pkg_name="test_plugin-1.0.1.tgz",
            os="linux",
            version="1.0.1",
            cpu_arch="x86_64",
        )

        # 3. 验证已清理临时文件夹
        self.assertFalse(os.path.exists("/tmp/test_plugin-1.0.1-windows-x86.tgz"))
        self.assertFalse(os.path.exists("/tmp/test_plugin-1.0.1-linux-x86_64.tgz"))

        # 4. 验证插件包注册并移动至nginx目录下
        self.assertTrue(os.path.exists(linux_file_path))
        self.assertTrue(os.path.exists(windows_file_path))

        with tarfile.open(windows_file_path) as linux_tar:
            linux_tar.getmember("external_plugins/%s/project.yaml" % self.plugin_name)
            linux_tar.getmember("external_plugins/%s/plugin" % self.plugin_name)

    def _test_upload_api_success(self):
        # 测试上传
        self.post(
            path="/backend/package/upload/",
            data={
                "module": "test_module",
                "md5": "123",
                "bk_username": "admin",
                "bk_app_code": "bk_app_code",
                # nginx追加的内容
                "file_local_path": self.tarfile_path,
                "file_local_md5": "123",
                "file_name": "tarfile.tgz",
            },
            is_json=False,
        )

        # 逻辑校验
        self.assertEqual(
            UploadPackage.objects.filter(
                file_name=self.tarfile_name,
                file_path=os.path.join(settings.UPLOAD_PATH, self.tarfile_name),
            ).count(),
            1,
        )
        self.assertTrue(os.path.exists(os.path.join(settings.UPLOAD_PATH, self.tarfile_name)))

    def _test_register_api_success(self):

        # 插件包注册后存放地址
        windows_file_path = os.path.join(settings.NGINX_DOWNLOAD_PATH, "windows", "x86", "test_plugin-1.0.1.tgz")
        linux_file_path = os.path.join(settings.NGINX_DOWNLOAD_PATH, "linux", "x86_64", "test_plugin-1.0.1.tgz")

        # 验证创建前此时文件不存在
        self.assertFalse(os.path.exists(linux_file_path))
        self.assertFalse(os.path.exists(windows_file_path))

        # 测试注册
        self.post(
            path="/backend/api/plugin/create_register_task/",
            data={
                "file_name": self.tarfile_name,
                "is_release": True,
                "bk_username": "admin",
                "bk_app_code": "bk_app_code",
            },
        )

        # 逻辑校验
        # 1. 进程控制信息
        self.assertEqual(ProcControl.objects.all().count(), 2)

        # 2. 包记录信息（window， linux及版本号）
        Packages.objects.get(
            pkg_name="test_plugin-1.0.1.tgz", os="windows", version="1.0.1", cpu_arch="x86", creator="admin"
        )
        Packages.objects.get(
            pkg_name="test_plugin-1.0.1.tgz", os="linux", version="1.0.1", cpu_arch="x86_64", creator="admin"
        )

        # 3. 验证已清理临时文件夹
        self.assertFalse(os.path.exists("/tmp/test_plugin-1.0.1-windows-x86.tgz"))
        self.assertFalse(os.path.exists("/tmp/test_plugin-1.0.1-linux-x86_64.tgz"))

        # 4. 验证插件包注册并移动至nginx目录下
        self.assertTrue(os.path.exists(linux_file_path))
        self.assertTrue(os.path.exists(windows_file_path))

        with tarfile.open(linux_file_path) as linux_tar:
            linux_tar.getmember("external_plugins/%s/project.yaml" % self.plugin_name)
            linux_tar.getmember("external_plugins/%s/plugin" % self.plugin_name)

        # 只有一条对应的desc
        self.assertEqual(GsePluginDesc.objects.filter(name=self.plugin_name).count(), 1)

    def test_create_task_register_api(self):
        """测试上传文件接口"""
        self._test_upload_api_success()
        self._test_register_api_success()

    def test_create_task_register_optional_api(self):
        """测试上传文件接口"""
        self._test_upload_api_success()

        # 插件包注册后存放地址
        windows_file_path = os.path.join(settings.NGINX_DOWNLOAD_PATH, "windows", "x86", "test_plugin-1.0.1.tgz")
        linux_file_path = os.path.join(settings.NGINX_DOWNLOAD_PATH, "linux", "x86_64", "test_plugin-1.0.1.tgz")

        # 验证创建前此时文件不存在
        self.assertFalse(os.path.exists(linux_file_path))
        self.assertFalse(os.path.exists(windows_file_path))

        # 测试注册
        self.post(
            path="/backend/api/plugin/create_register_task/",
            data={
                "file_name": self.tarfile_name,
                "is_release": True,
                "is_template_overwrite": True,
                "is_template_load": True,
                "select_pkg_abs_paths": ["external_plugins_windows_x86/test_plugin"],
                "bk_username": "admin",
                "bk_app_code": "bk_app_code",
            },
        )

        # 逻辑校验
        # 1. 进程控制信息
        self.assertEqual(ProcControl.objects.all().count(), 1)

        # 2. 包记录信息，windows已选，被导入
        Packages.objects.get(
            pkg_name="test_plugin-1.0.1.tgz", os="windows", version="1.0.1", cpu_arch="x86", creator="admin"
        )
        # 仅指定windows的插件包进行导入，linux插件包不应该被记录
        self.assertFalse(
            Packages.objects.filter(
                pkg_name="test_plugin-1.0.1.tgz", os="linux", version="1.0.1", cpu_arch="x86_64", creator="admin"
            ).exists()
        )

        # 3. 验证已清理临时文件夹
        self.assertFalse(os.path.exists("/tmp/test_plugin-1.0.1-windows-x86.tgz"))
        self.assertFalse(os.path.exists("/tmp/test_plugin-1.0.1-linux-x86_64.tgz"))

        # 4. 验证插件包注册并移动至nginx目录下, 仅指定windows的插件包进行导入，linux插件包不应该被记录
        self.assertFalse(os.path.exists(linux_file_path))
        self.assertTrue(os.path.exists(windows_file_path))

        with tarfile.open(windows_file_path) as linux_tar:
            linux_tar.getmember("external_plugins/%s/project.yaml" % self.plugin_name)
            linux_tar.getmember("external_plugins/%s/plugin" % self.plugin_name)

        # 只有一条对应的desc
        self.assertEqual(GsePluginDesc.objects.filter(name=self.plugin_name).count(), 1)

    def test_create_export_task_api(self):
        self.test_create_task_register_api()
        response = self.post(
            path="/backend/api/plugin/create_export_task/",
            data={
                "category": "gse_plugin",
                "creator": "admin",
                "bk_username": "admin",
                "bk_app_code": "bk_app_code",
                "query_params": {"project": "test_plugin", "version": "1.0.1"},
            },
        )
        record = DownloadRecord.objects.get(id=response["data"]["job_id"])
        file_path = record.file_path
        self.assertTrue(os.path.exists(file_path))
        with tarfile.open(file_path) as download_tar:
            download_tar.getmember(
                "./external_plugins_linux_x86_64/{file_name}/plugin".format(file_name=self.plugin_name)
            )
            download_tar.getmember(
                "./external_plugins_windows_x86/{file_name}/plugin".format(file_name=self.plugin_name)
            )

    def test_export_with_os(self):
        self.test_create_task_register_api()
        response = self.post(
            path="/backend/api/plugin/create_export_task/",
            data={
                "category": "gse_plugin",
                "creator": "admin",
                "bk_username": "admin",
                "bk_app_code": "bk_app_code",
                "query_params": {"project": "test_plugin", "version": "1.0.1", "os": "windows"},
            },
        )
        record = DownloadRecord.objects.get(id=response["data"]["job_id"])
        file_path = record.file_path
        self.assertTrue(os.path.exists(file_path))
        with tarfile.open(file_path) as download_tar:
            download_tar.getmember(
                "./external_plugins_windows_x86/{file_name}/plugin".format(file_name=self.plugin_name)
            )
            try:
                download_tar.getmember(
                    "./external_plugins_linux_x86_64/{file_name}/plugin".format(file_name=self.plugin_name)
                )
                self.assertTrue(False)
            except Exception:
                pass

    def test_export_with_os_cpu_arch(self):
        self.test_create_task_register_api()
        utils.PluginTestObjFactory.batch_create_pkg(
            [
                utils.PluginTestObjFactory.pkg_obj(
                    {
                        "pkg_name": "test_plugin-1.0.1.tgz",
                        "project": self.plugin_name,
                        "version": "1.0.1",
                        "cpu_arch": "x86",
                    }
                ),
            ]
        )
        response = self.post(
            path="/backend/api/plugin/create_export_task/",
            data={
                "category": "gse_plugin",
                "creator": "admin",
                "bk_username": "admin",
                "bk_app_code": "bk_app_code",
                "query_params": {"project": "test_plugin", "version": "1.0.1", "os": "linux", "cpu_arch": "x86_64"},
            },
        )
        record = DownloadRecord.objects.get(id=response["data"]["job_id"])
        file_path = record.file_path
        self.assertTrue(os.path.exists(file_path))
        with tarfile.open(file_path) as download_tar:
            download_tar.getmember(
                "./external_plugins_linux_x86_64/{file_name}/plugin".format(file_name=self.plugin_name)
            )
            try:
                download_tar.getmember(
                    "./external_plugins_linux_x86/{file_name}/plugin".format(file_name=self.plugin_name)
                )
                download_tar.getmember(
                    "./external_plugins_windows_x86/{file_name}/plugin".format(file_name=self.plugin_name)
                )
                self.assertTrue(False)
            except Exception:
                pass

    def _query_parse_api(self):
        # 测试文件解析接口
        response = self.post(
            path="/backend/api/plugin/parse/",
            data={"file_name": self.tarfile_name, "bk_username": "admin", "bk_app_code": "bk_app_code"},
        )
        return response

    def test_parse_api_all_new_add(self):
        self._test_upload_api_success()

        # 测试文件解析接口
        response = self._query_parse_api()
        self.assertEqual(len(response["data"]), 2)
        self.assertEqual(len([item for item in response["data"] if item["result"] and item["message"] == "新增插件"]), 2)

        first_parse_info = response["data"][0]
        self.assertEqual(len(first_parse_info["config_templates"]), 2)

    def test_parse_api_yaml_file_not_find_or_unread(self):
        os.remove(self.tarfile_path)
        linux_yaml_file = os.path.join(
            self.temp_path, "temp_folder", "external_plugins_linux_x86_64", "test_plugin", "project.yaml"
        )
        os.remove(linux_yaml_file)

        windows_yaml_file = os.path.join(
            self.temp_path, "temp_folder", "external_plugins_windows_x86", "test_plugin", "project.yaml"
        )
        os.remove(windows_yaml_file)

        windows_yaml_file_stream = open(windows_yaml_file, "w", encoding="utf-8")
        windows_yaml_file_stream.write("~6574745646")
        windows_yaml_file_stream.close()

        with tarfile.open(self.tarfile_path, "w:gz") as tfile:
            # self.temp_path/temp_folder下的所有文件放入temp_file_path文件下, arcname表示目标目录的目标路径
            tfile.add(os.path.join(self.temp_path, "temp_folder"), arcname=".", recursive=True)

        self._test_upload_api_success()
        response = self._query_parse_api()
        self.assertEqual(len(response["data"]), 2)
        self.assertEqual(
            len([item for item in response["data"] if not item["result"] and item["message"] == "缺少project.yaml文件"]), 1
        )
        self.assertEqual(
            len(
                [item for item in response["data"] if not item["result"] and item["message"] == "project.yaml文件解析读取失败"]
            ),
            1,
        )

    def test_parse_api_yaml_file_lack_attr_or_category_error(self):
        os.remove(self.tarfile_path)
        linux_yaml_file = os.path.join(
            self.temp_path, "temp_folder", "external_plugins_linux_x86_64", "test_plugin", "project.yaml"
        )
        os.remove(linux_yaml_file)
        lack_of_attr_content = self.config_content.replace('name: "test_plugin"', "")
        linux_yaml_file_stream = open(linux_yaml_file, "w", encoding="utf-8")
        linux_yaml_file_stream.write(lack_of_attr_content)
        linux_yaml_file_stream.close()

        windows_yaml_file = os.path.join(
            self.temp_path, "temp_folder", "external_plugins_windows_x86", "test_plugin", "project.yaml"
        )
        os.remove(windows_yaml_file)
        category_error_content = self.config_content.replace("category: official", "category: category_error")
        windows_yaml_file_stream = open(windows_yaml_file, "w", encoding="utf-8")
        windows_yaml_file_stream.write(category_error_content)
        windows_yaml_file_stream.close()

        with tarfile.open(self.tarfile_path, "w:gz") as tfile:
            # self.temp_path/temp_folder下的所有文件放入temp_file_path文件下, arcname表示目标目录的目标路径
            tfile.add(os.path.join(self.temp_path, "temp_folder"), arcname=".", recursive=True)

        self._test_upload_api_success()
        response = self._query_parse_api()
        self.assertEqual(len(response["data"]), 2)

        self.assertEqual(
            len([item for item in response["data"] if not item["result"] and item["message"] == "project.yaml文件信息缺失"]),
            1,
        )
        self.assertEqual(
            len(
                [
                    item
                    for item in response["data"]
                    if not item["result"] and item["message"] == "project.yaml中category配置异常，请确认后重试"
                ]
            ),
            1,
        )

    def test_parse_api_not_template_and_version_update(self):
        windows_template_file = os.path.join(
            self.temp_path,
            "temp_folder",
            "external_plugins_windows_x86",
            "test_plugin",
            "etc",
            "test_plugin.main.conf.tpl",
        )
        os.remove(windows_template_file)
        with tarfile.open(self.tarfile_path, "w:gz") as tfile:
            # self.temp_path/temp_folder下的所有文件放入temp_file_path文件下, arcname表示目标目录的目标路径
            tfile.add(os.path.join(self.temp_path, "temp_folder"), arcname=".", recursive=True)

        Packages.objects.create(
            pkg_name="test_plugin-1.0.0.tgz",
            version="1.0.0",
            module="gse_plugin",
            project="test_plugin",
            pkg_size=0,
            pkg_path="",
            md5="",
            pkg_mtime="",
            pkg_ctime="",
            location="",
            os="linux",
            cpu_arch="x86_64",
            is_release_version=True,
            is_ready=True,
        )

        self._test_upload_api_success()
        response = self._query_parse_api()
        self.assertEqual(len(response["data"]), 2)
        self.assertEqual(
            len(
                [
                    item
                    for item in response["data"]
                    if not item["result"] and item["message"] == "找不到需要导入的配置模板文件[etc/test_plugin.main.conf.tpl]"
                ]
            ),
            1,
        )
        self.assertEqual(len([item for item in response["data"] if item["result"] and item["message"] == "更新插件版本"]), 1)

    def test_parse_api_low_version_or_same_version(self):
        package_params = dict(
            pkg_name="test_plugin-1.0.1.tgz",
            version="1.0.1",
            module="gse_plugin",
            project="test_plugin",
            pkg_size=0,
            pkg_path="",
            md5="",
            pkg_mtime="",
            pkg_ctime="",
            location="",
            os="linux",
            cpu_arch="x86_64",
            is_release_version=True,
            is_ready=True,
        )
        Packages.objects.create(**package_params)
        package_params.update({"version": "2.0.0", "cpu_arch": "x86", "os": "windows"})
        Packages.objects.create(**package_params)

        self._test_upload_api_success()
        response = self._query_parse_api()
        self.assertEqual(len(response["data"]), 2)
        self.assertEqual(
            len([item for item in response["data"] if item["result"] and item["message"] == "已有版本插件更新"]), 1
        )
        self.assertEqual(
            len([item for item in response["data"] if item["result"] and item["message"] == "低版本插件仅支持导入"]), 1
        )


class TestImportCommand(TestCase):
    target_path = os.path.join(TEST_ROOT, uuid.uuid4().hex)

    temp_path = os.path.join(TEST_ROOT, uuid.uuid4().hex)

    tarfile_name = "tarfile.tgz"
    tarfile_path = os.path.join(temp_path, tarfile_name)

    plugin_name = "test_plugin"

    def setUp(self):
        """测试启动初始化配置"""
        # 1. 准备一个yaml配置文件
        config_content = """
  name: "test_plugin"
  version: "1.0.1"
  description: "用于采集主机基础性能数据，包含CPU,内存，磁盘，⽹络等数据"
  description_en: "用于采集主机基础性能数据，包含CPU,内存，磁盘，⽹络等数据"
  scenario: "CMDB上的是实时数据，蓝鲸监控-主机监控中的基础性能数据"
  scenario_en: "CMDB上的是实时数据，蓝鲸监控-主机监控中的基础性能数据"
  category: official
  config_file: basereport.conf
  multi_config: True
  config_file_path: ""
  config_format: yaml
  auto_launch: true
  launch_node: proxy
  upstream:
     bkmetric
  dependences:
     gse_agent: "1.2.0"
     bkmetric: "1.6.0"
  config_templates:
    - plugin_version: "*"
      name: child.conf
      version: 2.0.1
      file_path: etc/child
      format: yaml
      source_path: etc/child.conf.tpl
    - plugin_version: "*"
      name: test_plugin.conf
      version: 1.0.2
      file_path: etc/main
      format: yaml
      source_path: etc/test_plugin.main.conf.tpl
      is_main_config: 1
  control:
     start: "./start.sh %name"
     stop: "./stop.sh %name"
     restart: "./restart.sh %name"
     version: "./%name -v"
     reload: "./%name -s reload"
     health_check: "./%name -z"
  process_name: "test_process"
"""

        # 2. 创建一个打包文件，包含两层内容，一个linux，一个windows
        temp_file_path = os.path.join(self.temp_path, "temp_folder")
        if not os.path.exists(self.temp_path):
            os.mkdir(self.temp_path)
        os.mkdir(temp_file_path)
        for package_os, cpu_arch in (("linux", "x86_64"), ("windows", "x86")):
            current_path = os.path.join(temp_file_path, "external_plugins_{}_{}".format(package_os, cpu_arch))
            os.mkdir(current_path)

            plugin_path = os.path.join(current_path, self.plugin_name)
            os.mkdir(plugin_path)

            config_path = os.path.join(plugin_path, "etc")
            os.mkdir(config_path)

            f1 = open(os.path.join(plugin_path, "plugin"), "w")
            f1.close()
            f2 = open(os.path.join(plugin_path, "project.yaml"), "w", encoding="utf-8")
            f2.write(config_content)
            f2.close()

            main_config = open(os.path.join(config_path, "test_plugin.main.conf.tpl"), "w")
            main_config.close()
            child_config = open(os.path.join(config_path, "child.conf.tpl"), "w")
            child_config.close()

        with tarfile.open(self.tarfile_path, "w:gz") as tfile:
            tfile.add(temp_file_path, arcname=".", recursive=True)

        # nginx的模拟路径
        settings.NGINX_DOWNLOAD_PATH = settings.UPLOAD_PATH = self.target_path

        settings.BK_OFFICIAL_PLUGINS_INIT_PATH = self.temp_path

    def tearDown(self):
        shutil.rmtree(self.temp_path)
        shutil.rmtree(self.target_path)

    def test_import_command(self):
        """测试导入命令"""
        if os.path.exists(settings.BK_OFFICIAL_PLUGINS_INIT_PATH):
            call_command("init_official_plugins")
            self.assertTrue(Packages.objects.all().exists())
            self.assertTrue(UploadPackage.objects.all().exists())
            self.assertTrue(PluginConfigTemplate.objects.all().exists())
