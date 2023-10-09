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

from apps.node_man import constants

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

    def extract_initial_artifact(self, initial_artifact_local_path: str, extract_dir: str):
        # todo: 是否使用Archive(initial_artifact_local_path).extractall(extract_dir, auto_create_dir=True)
        with tarfile.open(name=initial_artifact_local_path) as tf:
            tf.extractall(path=extract_dir)

        extract_dir: str = os.path.join(extract_dir, self.BASE_PKG_DIR)
        if not os.path.exists(extract_dir):
            raise FileExistsError(_("Proxy 包解压后不存在 {base_pkg_dir} 目录").format(base_pkg_dir=self.BASE_PKG_DIR))

        # 把基础 Agent 包拉过来
        os_str: str = constants.PluginOsType.linux
        cpu_arch: str = constants.CpuType.x86_64
        pkg_name: str = f"{constants.GsePackageCode.AGENT.value}-{self._get_version(extract_dir)}.tgz"
        base_agent_pkg_path: str = os.path.join(self.download_path, self.BASE_STORAGE_DIR, os_str, cpu_arch, pkg_name)
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

        # 按正则规范构建 Proxy 安装包的目录
        proxy_dir: str = os.path.join(extract_dir, self.PKG_PATH_DIR_TEMPL.format(os=os_str, cpu_arch=cpu_arch))
        os.rename(base_agent_src, proxy_dir)
        logger.info(f"rename base_agent_src -> {base_agent_src} to proxy_dir -> {proxy_dir}")

        # bin 目录检查
        proxy_bin_dir: str = os.path.join(proxy_dir, "bin")
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

    def _get_support_files_info(self, extract_dir: str) -> typing.Dict[str, typing.Any]:
        return super()._get_support_files_info(extract_dir=extract_dir)
