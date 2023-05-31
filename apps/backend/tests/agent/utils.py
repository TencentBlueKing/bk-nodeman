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
import shutil
import tarfile
import typing
import uuid
from enum import Enum

import mock
from django.conf import settings

from apps.backend.agent.artifact_builder import agent, proxy
from apps.backend.subscription.steps.agent_adapter import config_templates
from apps.core.files import base, core_files_constants
from apps.core.files import storage as core_files_storage
from apps.core.files.storage import get_storage
from apps.mock_data import common_unit
from apps.node_man import constants
from apps.utils import files

# 测试文件根路径
from apps.utils.enum import EnhanceEnum
from apps.utils.unittest.testcase import CustomAPITestCase

VERSION = common_unit.plugin.PACKAGE_VERSION


class PathSettingOverwrite(EnhanceEnum):
    EXPORT_PATH = "EXPORT_PATH"
    UPLOAD_PATH = "UPLOAD_PATH"
    DOWNLOAD_PATH = "DOWNLOAD_PATH"
    GSE_CERT_PATH = "GSE_CERT_PATH"

    @classmethod
    def _get_member__alias_map(cls) -> typing.Dict[Enum, str]:
        raise NotImplementedError()

    @classmethod
    def get_setting_name__path_suffix_map(cls) -> typing.Dict[str, str]:
        return {
            cls.EXPORT_PATH.value: "export",
            cls.UPLOAD_PATH.value: "upload",
            cls.DOWNLOAD_PATH.value: "download",
            cls.GSE_CERT_PATH.value: "cert",
        }


class AgentBaseTestCase(CustomAPITestCase):
    TMP_DIR: str = None
    PKG_NAME: str = None
    OVERWRITE_VERSION: str = None
    ARCHIVE_NAME: str = f"gse_agent_ce-{VERSION}.tgz"
    ARCHIVE_PATH: str = None
    ARCHIVE_MD5: str = None
    OS_CPU_CHOICES = [
        (constants.OsType.LINUX.lower(), constants.CpuType.x86_64),
        (constants.OsType.WINDOWS.lower(), constants.CpuType.x86),
    ]
    ARTIFACT_BUILDER_CLASS: typing.Type[agent.AgentArtifactBuilder] = agent.AgentArtifactBuilder

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

        cls.TMP_DIR = files.mk_and_return_tmpdir()
        cls.PKG_NAME = f"{cls.ARTIFACT_BUILDER_CLASS.NAME}-{VERSION}.tgz"
        cls.ARCHIVE_PATH = os.path.join(cls.TMP_DIR, cls.ARCHIVE_NAME)

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
        core_files_storage._STORAGE_OBJ_CACHE = {}
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

            if setting_name == PathSettingOverwrite.GSE_CERT_PATH.value:
                self.gen_cert_files(overwrite_path)
            elif setting_name == PathSettingOverwrite.DOWNLOAD_PATH.value:
                shutil.copytree(
                    os.path.join(settings.BK_SCRIPTS_PATH, "gsectl"), os.path.join(overwrite_path, "gsectl")
                )

        artifact_dir = self.gen_base_artifact_files(os_cpu_choices=self.OS_CPU_CHOICES)
        self.pack_pkg(artifact_dir=artifact_dir, arcname=self.ARTIFACT_BUILDER_CLASS.BASE_PKG_DIR)
        self.ARCHIVE_MD5 = files.md5sum(name=self.ARCHIVE_PATH)

        def download(url: str, name: str = None):
            storage = get_storage()
            with storage.open(name=url, mode="rb") as fs:
                with files.FileOpen(name=name, mode="wb") as local_fs:
                    for chunk in iter(lambda: fs.read(4096), b""):
                        if not chunk:
                            continue
                        local_fs.write(chunk)

        mock.patch("apps.backend.agent.artifact_builder.base.files.download_file", download).start()

        super().setUp()

    @classmethod
    def gen_agent_bin(cls, pkg_dir: str, package_os: str):
        pkg_bin_dir = os.path.join(pkg_dir, "bin")
        # 创建可执行文件
        os.makedirs(pkg_bin_dir)
        agent_exes: typing.List[str] = (("gse_agent",), ("gse_agent.exe", "gse_agent_daemon.exe"))[
            package_os == constants.PluginOsType.windows
        ]
        for exe in agent_exes:
            with open(os.path.join(pkg_bin_dir, exe), "w"):
                pass

    @classmethod
    def gen_base_artifact_files(cls, os_cpu_choices: typing.List[typing.Tuple[str, str]]):
        base_artifact_dir = os.path.join(cls.TMP_DIR, uuid.uuid4().hex, cls.ARTIFACT_BUILDER_CLASS.BASE_PKG_DIR)
        for package_os, cpu_arch in os_cpu_choices:
            pkg_dir = os.path.join(
                base_artifact_dir,
                cls.ARTIFACT_BUILDER_CLASS.PKG_PATH_DIR_TEMPL.format(os=package_os, cpu_arch=cpu_arch),
            )
            cls.gen_agent_bin(pkg_dir, package_os)

        # 版本文件
        with open(os.path.join(base_artifact_dir, "VERSION"), "w", encoding="utf-8") as version_fs:
            version_fs.write(VERSION)

        # changelog
        with open(os.path.join(base_artifact_dir, "CHANGELOG.md"), "w", encoding="utf-8") as version_fs:
            version_fs.write(f"### {VERSION}\nchange")

        # support-files
        pkg_conf_env_dir = os.path.join(base_artifact_dir, "support-files", "env")
        pkg_conf_tmpls_dir = os.path.join(base_artifact_dir, "support-files", "templates")

        os.makedirs(pkg_conf_env_dir, exist_ok=True)
        os.makedirs(pkg_conf_tmpls_dir, exist_ok=True)

        # 写入配置模板
        with open(os.path.join(pkg_conf_tmpls_dir, "gse_agent_conf.template"), "w", encoding="utf-8") as templ_fs:
            templ_fs.write(config_templates.GSE_AGENT_CONFIG_TMPL)

        return base_artifact_dir

    @classmethod
    def gen_cert_files(cls, cert_path):
        for cert_filename in constants.GseCert.list_member_values():
            with open(os.path.join(cert_path, cert_filename), "w", encoding="utf-8"):
                pass

    @classmethod
    def pack_pkg(cls, artifact_dir: str, arcname: str = "."):
        # 插件打包
        with tarfile.open(cls.ARCHIVE_PATH, "w:gz") as tf:
            tf.add(artifact_dir, arcname=arcname, recursive=True)

    def tearDown(self):
        if os.path.exists(self.TMP_DIR):
            shutil.rmtree(self.TMP_DIR)
        super().tearDown()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.TMP_DIR):
            shutil.rmtree(cls.TMP_DIR)
        super().tearDownClass()


class ProxyBaseTestCase(AgentBaseTestCase):
    ARCHIVE_NAME: str = f"gse_ce-{VERSION}.tgz"
    OS_CPU_CHOICES = [
        (constants.OsType.LINUX.lower(), constants.CpuType.x86_64),
    ]
    ARTIFACT_BUILDER_CLASS: typing.Type[proxy.ProxyArtifactBuilder] = proxy.ProxyArtifactBuilder

    def setUp(self):
        super().setUp()
        self.gen_base_agent_pkg()

    @classmethod
    def gen_base_artifact_files(cls, os_cpu_choices: typing.List[typing.Tuple[str, str]]):
        base_artifact_dir = os.path.join(cls.TMP_DIR, uuid.uuid4().hex, cls.ARTIFACT_BUILDER_CLASS.BASE_PKG_DIR)
        pkg_bin_dir: str = os.path.join(base_artifact_dir, cls.ARTIFACT_BUILDER_CLASS.SERVER_BIN_DIR)

        # 创建可执行文件
        os.makedirs(pkg_bin_dir, exist_ok=True)
        for svr_exe in cls.ARTIFACT_BUILDER_CLASS.PROXY_SVR_EXES:
            with open(os.path.join(pkg_bin_dir, svr_exe), "w"):
                pass

        # 版本文件
        with open(os.path.join(base_artifact_dir, "VERSION"), "w", encoding="utf-8") as version_fs:
            version_fs.write(VERSION)

        # changelog
        with open(os.path.join(base_artifact_dir, "CHANGELOG.md"), "w", encoding="utf-8") as version_fs:
            version_fs.write(f"### {VERSION}\nchange")

        # support-files
        pkg_conf_env_dir = os.path.join(base_artifact_dir, "support-files", "env")
        pkg_conf_tmpls_dir = os.path.join(base_artifact_dir, "support-files", "templates")

        os.makedirs(pkg_conf_env_dir, exist_ok=True)
        os.makedirs(pkg_conf_tmpls_dir, exist_ok=True)

        for templ_name in ["#etc#gse#gse_data_proxy.conf", "#etc#gse#gse_file_proxy.conf"]:
            # 写入配置模板
            with open(os.path.join(pkg_conf_tmpls_dir, templ_name), "w", encoding="utf-8") as version_fs:
                version_fs.write(config_templates.GSE_FILE_PROXY_CONFIG_TEMPL)

        return base_artifact_dir

    @classmethod
    def gen_base_agent_pkg(cls):
        for package_os, cpu_arch in cls.OS_CPU_CHOICES:
            pkg_dir = os.path.join(cls.TMP_DIR, uuid.uuid4().hex, agent.AgentArtifactBuilder.PKG_DIR)
            cls.gen_agent_bin(pkg_dir, package_os)
            # 拷贝证书
            shutil.copytree(settings.GSE_CERT_PATH, os.path.join(pkg_dir, "cert"))

            pkg_path: str = os.path.join(
                settings.DOWNLOAD_PATH,
                agent.AgentArtifactBuilder.BASE_STORAGE_DIR,
                package_os,
                cpu_arch,
                f"{AgentBaseTestCase.ARTIFACT_BUILDER_CLASS.NAME}-{VERSION}.tgz",
            )
            os.makedirs(os.path.dirname(pkg_path), exist_ok=True)
            with tarfile.open(pkg_path, "w:gz") as tf:
                tf.add(pkg_dir, arcname=agent.AgentArtifactBuilder.PKG_DIR, recursive=True)

            if cls.OVERWRITE_VERSION:
                shutil.copyfile(
                    pkg_path,
                    os.path.join(
                        os.path.dirname(pkg_path),
                        f"{AgentBaseTestCase.ARTIFACT_BUILDER_CLASS.NAME}-{cls.OVERWRITE_VERSION}.tgz",
                    ),
                )
