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
import os
import random
import shutil
import tarfile
import uuid
from typing import Any, Dict, List, Optional

import mock
from django.conf import settings

from apps.backend.tests.plugin import utils
from apps.core.files import base, core_files_constants
from apps.node_man import constants, models
from apps.node_man.models import Packages, ProcControl
from apps.utils import files


class FileSystemTestCase(utils.PluginBaseTestCase):
    FILE_OVERWRITE = True

    OVERWRITE_OBJ__KV_MAP = {
        settings: {
            "FILE_OVERWRITE": FILE_OVERWRITE,
            "STORAGE_TYPE": core_files_constants.StorageType.FILE_SYSTEM.value,
        },
        base.StorageFileOverwriteMixin: {"file_overwrite": FILE_OVERWRITE},
    }

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

    def parse_plugin(self, file_name: str) -> List[Dict[str, Any]]:
        pkg_parse_results = self.client.post(
            path="/backend/api/plugin/parse/",
            data={"file_name": file_name},
        )["data"]
        return pkg_parse_results

    def check_pkg_structure(self, project: str, pkg_path: str):
        # 第三方插件归档的插件包路径包含 project(插件名称)层级

        pkg_path_shims = [self.PLUGIN_CHILD_DIR_NAME]
        if utils.IS_EXTERNAL:
            pkg_path_shims.append(project)

        with tarfile.open(pkg_path) as tf:
            # get or raise KeyError
            tf.getmember(os.path.join(*pkg_path_shims, "etc", f"{project}.conf"))
            tf.getmember(os.path.join(*pkg_path_shims, "project.yaml"))
            tf.getmember(os.path.join(*pkg_path_shims, "bin", project))

            # 验证写入DB的配置模板在归档插件包中被删除
            self.assertRaises(KeyError, tf.getmember, os.path.join(*pkg_path_shims, "etc", f"{project}.conf.tpl"))
            self.assertRaises(KeyError, tf.getmember, os.path.join(*pkg_path_shims, "etc", "child.conf.tpl"))

    def check_and_fetch_parse_results(self, file_name: str, except_message_list: List[str]) -> List[Dict[str, Any]]:
        pkg_parse_results = self.parse_plugin(file_name=file_name)
        parse_message_list = [pkg_parse_result["message"] for pkg_parse_result in pkg_parse_results]
        self.assertListEqual(parse_message_list, except_message_list, is_sort=True)
        return pkg_parse_results

    # cases

    def test_upload__file_overwrite(self):

        save_file_name_set = set()
        upload_count = random.randint(2, 10)
        file_local_dir_path = os.path.join(self.TMP_DIR, uuid.uuid4().hex)
        os.makedirs(file_local_dir_path, exist_ok=True)
        for __ in range(upload_count):
            file_local_path = os.path.join(file_local_dir_path, self.PLUGIN_ARCHIVE_NAME)
            # 验证该文件上传后已被删除
            self.assertFalse(os.path.exists(file_local_path))

            # 上传文件默认将文件移动到 UPLOAD_PATH 并删除原路径的文件，所以采取拷贝到临时目录的方式变更文件上传文件
            shutil.copy(src=self.PLUGIN_ARCHIVE_PATH, dst=file_local_path)
            save_file_name_set.add(self.upload_plugin(file_local_path=file_local_path)["name"])

        if settings.FILE_OVERWRITE:
            self.assertEqual(len(save_file_name_set), 1)
        else:
            self.assertEqual(len(save_file_name_set), upload_count)

    def test_create_register_task(self):
        upload_result = self.upload_plugin()
        self.register_plugin(upload_result["name"])
        plugin_obj = models.GsePluginDesc.objects.get(name=utils.PLUGIN_NAME)
        for package_os, cpu_arch in self.OS_CPU_CHOICES:
            pkg_obj = Packages.objects.get(
                pkg_name=self.PLUGIN_ARCHIVE_NAME, version=utils.PACKAGE_VERSION, os=package_os, cpu_arch=cpu_arch
            )
            self.check_pkg_structure(project=plugin_obj.name, pkg_path=os.path.join(pkg_obj.pkg_path, pkg_obj.pkg_name))

        self.assertEqual(ProcControl.objects.all().count(), len(self.OS_CPU_CHOICES))

    def test_create_register_task__select_pkgs(self):
        upload_result = self.upload_plugin()
        cpu_arch = constants.CpuType.x86_64
        package_os = constants.OsType.LINUX.lower()
        self.register_plugin(
            file_name=upload_result["name"],
            select_pkg_relative_paths=[
                os.path.join(f"{self.PLUGIN_CHILD_DIR_NAME}_{package_os}_{cpu_arch}", utils.PLUGIN_NAME)
            ],
        )

        plugin_obj = models.GsePluginDesc.objects.get(name=utils.PLUGIN_NAME)
        pkg_obj = Packages.objects.get(
            pkg_name=self.PLUGIN_ARCHIVE_NAME, version=utils.PACKAGE_VERSION, os=package_os, cpu_arch=cpu_arch
        )
        self.check_pkg_structure(project=plugin_obj.name, pkg_path=os.path.join(pkg_obj.pkg_path, pkg_obj.pkg_name))

    def test_create_export_task(self):
        self.test_create_register_task()
        export_result = self.client.post(
            path="/backend/api/plugin/create_export_task/",
            data={
                "category": "gse_plugin",
                "creator": "admin",
                "query_params": {"project": utils.PLUGIN_NAME, "version": utils.PACKAGE_VERSION},
            },
        )["data"]
        record_obj = models.DownloadRecord.objects.get(id=export_result["job_id"])
        self.assertTrue(os.path.exists(record_obj.file_path))

    def test_create_export_task__with_os(self):
        self.test_create_register_task()
        export_result = self.client.post(
            path="/backend/api/plugin/create_export_task/",
            data={
                "category": "gse_plugin",
                "creator": "admin",
                "query_params": {
                    "project": utils.PLUGIN_NAME,
                    "version": utils.PACKAGE_VERSION,
                    "os": constants.OsType.LINUX.lower(),
                },
            },
        )["data"]
        record_obj = models.DownloadRecord.objects.get(id=export_result["job_id"])
        self.assertTrue(os.path.exists(record_obj.file_path))

    def test_create_export_task__with_os_cpu_arch(self):
        self.test_create_register_task()
        export_result = self.client.post(
            path="/backend/api/plugin/create_export_task/",
            data={
                "category": "gse_plugin",
                "creator": "admin",
                "query_params": {
                    "project": utils.PLUGIN_NAME,
                    "version": utils.PACKAGE_VERSION,
                    "os": constants.OsType.LINUX.lower(),
                    "cpu_arch": constants.CpuType.x86_64,
                },
            },
        )["data"]
        record_obj = models.DownloadRecord.objects.get(id=export_result["job_id"])
        self.assertTrue(os.path.exists(record_obj.file_path))

    def test_parse(self):
        self.check_and_fetch_parse_results(file_name=self.upload_plugin()["name"], except_message_list=["新增插件"] * 2)

    def test_parse__yaml_file_not_find_or_unread(self):
        os.remove(self.PLUGIN_ARCHIVE_PATH)
        product_tmp_dir = self.gen_test_plugin_files(
            project_yaml_content="Invalid project yaml content", os_cpu_choices=self.OS_CPU_CHOICES
        )
        linux_yaml_path = os.path.join(product_tmp_dir, "plugins_linux_x86_64", utils.PLUGIN_NAME, "project.yaml")
        os.remove(linux_yaml_path)
        self.pack_plugin(product_tmp_dir=product_tmp_dir)

        self.check_and_fetch_parse_results(
            file_name=self.upload_plugin()["name"], except_message_list=["缺少project.yaml文件", "project.yaml文件解析读取失败"]
        )

    def test_parse__yaml_file_lack_attr_or_category_error(self):
        os.remove(self.PLUGIN_ARCHIVE_PATH)
        project_yaml_content = utils.PluginTestObjFactory.get_project_yaml_content()
        product_tmp_dir = self.gen_test_plugin_files(
            project_yaml_content=project_yaml_content, os_cpu_choices=self.OS_CPU_CHOICES
        )
        linux_yaml_path = os.path.join(product_tmp_dir, "plugins_linux_x86_64", utils.PLUGIN_NAME, "project.yaml")
        windows_yaml_path = os.path.join(product_tmp_dir, "plugins_windows_x86", utils.PLUGIN_NAME, "project.yaml")
        with open(linux_yaml_path, "w+", encoding="utf-8") as fs:
            lack_of_plugin_name_content = project_yaml_content.replace(f'name: "{utils.PLUGIN_NAME}"', "")
            fs.write(lack_of_plugin_name_content)
        with open(windows_yaml_path, "w+", encoding="utf-8") as fs:
            invalid_category_content = project_yaml_content.replace(
                f"category: {utils.GSE_PLUGIN_DESC_PARAMS['category']}", "category: invalid_category"
            )
            fs.write(invalid_category_content)
        self.pack_plugin(product_tmp_dir=product_tmp_dir)
        self.check_and_fetch_parse_results(
            file_name=self.upload_plugin()["name"],
            except_message_list=["project.yaml 文件信息缺失", "project.yaml 中 category 配置异常，请确认后重试"],
        )

    def test_parse__not_template_and_version_update(self):
        os.remove(self.PLUGIN_ARCHIVE_PATH)
        project_yaml_content = utils.PluginTestObjFactory.get_project_yaml_content()
        product_tmp_dir = self.gen_test_plugin_files(
            project_yaml_content=project_yaml_content, os_cpu_choices=self.OS_CPU_CHOICES
        )

        # 移除windows的主配置模板
        windows_tpl_file_path = os.path.join(
            product_tmp_dir, "plugins_windows_x86", utils.PLUGIN_NAME, "etc", f"{utils.PLUGIN_NAME}.conf.tpl"
        )
        os.remove(windows_tpl_file_path)

        low_version_pkg_obj = utils.PluginTestObjFactory.pkg_obj(
            {"version": "1.0.0", "os": constants.OsType.LINUX.lower(), "cpu_arch": constants.CpuType.x86_64},
            is_obj=True,
        )
        low_version_pkg_obj.save()

        self.pack_plugin(product_tmp_dir=product_tmp_dir)
        self.check_and_fetch_parse_results(
            file_name=self.upload_plugin()["name"],
            except_message_list=["找不到需要导入的配置模板文件 -> etc/test_plugin.conf.tpl", "更新插件版本"],
        )

    def test_parse__low_or_same_version(self):
        utils.PluginTestObjFactory.batch_create_pkg(
            [
                utils.PluginTestObjFactory.pkg_obj(
                    {"os": constants.OsType.LINUX.lower(), "cpu_arch": constants.CpuType.x86_64}
                ),
                utils.PluginTestObjFactory.pkg_obj(
                    {"version": "2.0.0", "os": constants.OsType.WINDOWS.lower(), "cpu_arch": constants.CpuType.x86}
                ),
            ]
        )
        self.check_and_fetch_parse_results(
            file_name=self.upload_plugin()["name"], except_message_list=["低版本插件仅支持导入", "已有版本插件更新"]
        )


class BkRepoTestCase(FileSystemTestCase):
    FILE_OVERWRITE = True
    OVERWRITE_OBJ__KV_MAP = {
        settings: {
            "FILE_OVERWRITE": FILE_OVERWRITE,
            "STORAGE_TYPE": core_files_constants.StorageType.BLUEKING_ARTIFACTORY.value,
            "BKREPO_USERNAME": "username",
            "BKREPO_PASSWORD": "blueking",
            "BKREPO_PROJECT": "project",
            "BKREPO_BUCKET": "private",
            "BKREPO_ENDPOINT_URL": "http://127.0.0.1",
        },
        utils.CustomBKRepoMockStorage: {"file_overwrite": FILE_OVERWRITE},
        base.StorageFileOverwriteMixin: {"file_overwrite": FILE_OVERWRITE},
    }

    @classmethod
    def setUpClass(cls):
        mock.patch("apps.core.files.storage.CustomBKRepoStorage", utils.CustomBKRepoMockStorage).start()
        super().setUpClass()

    def upload_plugin(self, file_local_path: Optional[str] = None) -> Dict[str, Any]:
        file_local_path = file_local_path or self.PLUGIN_ARCHIVE_PATH
        upload_result = self.client.post(
            path="/backend/package/upload_cos/",
            data={
                "module": "gse_plugin",
                "md5": files.md5sum(file_local_path),
                # nginx 计算并回调的额外参数
                "file_name": self.PLUGIN_ARCHIVE_NAME,
                "file_path": file_local_path,
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


class FileNotOverwriteTestCase(FileSystemTestCase):
    FILE_OVERWRITE = False
