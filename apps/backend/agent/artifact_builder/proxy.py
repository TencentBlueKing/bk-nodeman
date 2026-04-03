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
import logging
import os
import shutil
import tarfile
import typing

from django.utils.translation import ugettext_lazy as _

from apps.node_man import constants, models

from . import base

logger = logging.getLogger("app")


class ProxyArtifactBuilder(base.BaseArtifactBuilder):

    NAME = constants.GsePackageCode.PROXY.value
    PKG_DIR = constants.GsePackageDir.PROXY.value
    CERT_FILENAMES: typing.List[str] = constants.GseCert.list_member_values()
    ENV_FILES = constants.GsePackageEnv.PROXY.value
    TEMPLATE_PATTERN = constants.GsePackageTemplatePattern.PROXY.value
    # 服务二进制目录
    SERVER_BIN_DIR: str = "server/bin"
    # 所需的二进制文件
    PROXY_SVR_EXES: typing.List[str] = ["gse_data", "gse_file"]
    AGENT_BINARY_NAME: str = "gse_agent"

    def extract_initial_artifact(self, initial_artifact_local_path: str, extract_dir: str):
        with tarfile.open(name=initial_artifact_local_path) as tf:
            tf.extractall(path=extract_dir)

        extract_dir: str = os.path.join(extract_dir, self.BASE_PKG_DIR)
        if not os.path.exists(extract_dir):
            raise FileExistsError(_("Proxy 包解压后不存在 {base_pkg_dir} 目录").format(base_pkg_dir=self.BASE_PKG_DIR))

        os_str: str = constants.PluginOsType.linux
        cpu_arch: str = self._get_elf_arch(os.path.join(extract_dir, self.SERVER_BIN_DIR, self.PROXY_SVR_EXES[0]))

        # 按正则规范构建 Proxy 安装包的目录
        proxy_dir: str = os.path.join(extract_dir, self.PKG_PATH_DIR_TEMPL.format(os=os_str, cpu_arch=cpu_arch))
        proxy_bin_dir: str = os.path.join(proxy_dir, "bin")

        if os.path.exists(os.path.join(extract_dir, self.SERVER_BIN_DIR, self.AGENT_BINARY_NAME)):
            os.makedirs(proxy_bin_dir, exist_ok=True)
            logger.info(f"make proxy_bin_dir -> {proxy_bin_dir} success.")
            self.PROXY_SVR_EXES.append(self.AGENT_BINARY_NAME)
        else:
            # 把基础 Agent 包拉过来
            pkg_name: str = f"{constants.GsePackageCode.AGENT.value}-{self._get_version(extract_dir)}.tgz"
            base_agent_pkg_path: str = os.path.join(
                self.download_path, self.BASE_STORAGE_DIR, os_str, cpu_arch, pkg_name
            )
            if not self.storage.exists(base_agent_pkg_path):
                raise FileExistsError(
                    _("构建 Proxy 所需 Agent 包不存在：file_path -> {file_path}").format(file_path=base_agent_pkg_path)
                )

            base_agent_src: str = os.path.join(extract_dir, str(constants.GsePackageDir.AGENT.value))
            # src 存在即移除，确保基础 Agent 解压目录是干净的
            if os.path.exists(base_agent_src):
                shutil.rmtree(base_agent_src)
                logger.warning(f"base_agent_src -> {base_agent_src} not clean, removed it.")

            # 执行解压
            with self.storage.open(name=base_agent_pkg_path, mode="rb") as tf_from_storage:
                with tarfile.open(fileobj=tf_from_storage) as tf:
                    tf.extractall(extract_dir)
                    logger.info(f"file -> {base_agent_pkg_path} extract to dir -> {extract_dir} success.")

            os.rename(base_agent_src, proxy_dir)
            logger.info(f"rename base_agent_src -> {base_agent_src} to proxy_dir -> {proxy_dir}")

            # bin 目录检查
            if not os.path.exists(proxy_bin_dir):
                raise FileExistsError(_("构建 Proxy 所需 Agent 不存在 bin 路径"))

        # 将所需的二进制放到安装包目录
        for svr_exe in self.PROXY_SVR_EXES:
            svr_exe_path: str = os.path.join(extract_dir, self.SERVER_BIN_DIR, svr_exe)
            if not os.path.exists(svr_exe_path):
                raise FileExistsError(
                    _("构建 Proxy 所需二进制 [{svr_exe}] 不存在：svr_exe_path -> {svr_exe_path}").format(
                        svr_exe=svr_exe, svr_exe_path=svr_exe_path
                    )
                )

            svr_exe_dst_path: str = os.path.join(proxy_bin_dir, svr_exe)
            shutil.copyfile(svr_exe_path, svr_exe_dst_path)
            logger.info(f"copy {svr_exe} from {svr_exe_path} to {svr_exe_dst_path} success.")

        self._inject_dependencies(extract_dir)
        return extract_dir

    def update_or_create_support_files(self, package_infos: typing.List[typing.Dict]):
        """
        创建或更新support_files记录
        :param package_infos:
        :return:
        """
        for package_info in package_infos:
            support_files = package_info["artifact_meta_info"]["support_files_info"]
            version = package_info["artifact_meta_info"]["version"]
            package = package_info["package_dir_info"]

            for env_file in support_files["env"]:
                with open(env_file["file_absolute_path"], "r") as f:
                    env_str = f.read()

                logger.info(
                    f"update_or_create_support_files: env_file->{env_file} version->{version} raw_env->{env_str}"
                )
                env_value: typing.Dict[str, typing.Any] = self.parse_env(env_str)
                logger.info(
                    f"update_or_create_support_files: env_file->{env_file} version->{version} env_value->{env_value}"
                )

                models.GseConfigEnv.objects.update_or_create(
                    defaults={"env_value": env_value},
                    version=version,
                    os=package["os"],
                    cpu_arch=package["cpu_arch"],
                    agent_name=(
                        constants.GsePackageCode.AGENT.value
                        if env_file["file_name"] in constants.GsePackageEnv.AGENT.value
                        else self.NAME
                    ),
                )

            for template in support_files["templates"]:
                with open(template["file_absolute_path"], "r") as f:
                    content = f.read()
                logger.info(
                    f"update_or_create_support_files: template->{template} version->{version} content->{content}"
                )

                models.GseConfigTemplate.objects.update_or_create(
                    defaults={"content": content},
                    name=template["file_name"],
                    version=version,
                    os=package["os"],
                    cpu_arch=package["cpu_arch"],
                    agent_name=(
                        constants.GsePackageCode.AGENT.value
                        if constants.GsePackageTemplatePattern.AGENT.value.search(template["file_name"])
                        else self.NAME
                    ),
                )

    def _get_support_files_info(self, extract_dir: str) -> typing.Dict[str, typing.Any]:
        return super()._get_support_files_info(extract_dir=extract_dir)

    def _get_elf_arch(self, binary_path: str) -> str:
        if not os.path.exists(binary_path):
            return constants.CpuType.x86_64

        import struct

        # ELF e_machine: https://refspecs.linuxfoundation.org/elf/gabi4+/ch4.eheader.html
        EM_AARCH64 = 0xB7  # AARCH64 架构
        with open(binary_path, "rb") as f:
            magic = f.read(4)
            if magic != b"\x7fELF":
                raise ValueError(_("文件 {binary_path} 不是合法的 ELF 文件").format(binary_path=binary_path))

            # ELF 头偏移 5 字节是 EI_DATA
            f.seek(5)
            ei_data = f.read(1)[0]

            if ei_data == 1:  # ELFDATA2LSB (小端序)
                fmt = "<H"
            elif ei_data == 2:  # ELFDATA2MSB (大端序)
                fmt = ">H"
            else:
                fmt = "@H"  # 使用系统字节序

            f.seek(18)
            e_machine = struct.unpack(fmt, f.read(2))[0]
            if e_machine == EM_AARCH64:
                return constants.CpuType.aarch64
            else:
                # 目前仅支持 x86_64 和 aarch64 两种架构
                return constants.CpuType.x86_64
