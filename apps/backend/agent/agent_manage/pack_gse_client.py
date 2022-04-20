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
import shutil
import tarfile
from typing import Dict, List

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from apps.backend import exceptions
from apps.core.files.storage import get_storage
from apps.node_man import constants
from apps.node_man.models import GseAgentDesc
from apps.utils import files
from common.log import logger


class GseClientPack(object):
    def __init__(self, cert_package: str, client_package: str):
        self.cert_pkg_name = cert_package
        self.client_name = client_package
        self.storage = get_storage(file_overwrite=True)
        self.decompose_tmp = files.mk_and_return_tmpdir()
        self.integrate_tmp = files.mk_and_return_tmpdir()

    def __del__(self):
        for tmp in [self.decompose_tmp, self.integrate_tmp]:
            if os.path.isdir(tmp):
                shutil.rmtree(tmp)

    def pack_gse_client(
        self,
    ):
        pkg_name_version = constants.AgentPackageMap.GSE_AGENT_PACKAGE_RE.match(
            os.path.basename(self.client_name)
        ).groupdict()["version"]

        self.extra_file(self.cert_pkg_name)
        self.extra_file(self.client_name)
        yaml_config = self.add_default_yaml_config(
            yaml_config=self.project_yaml_parse(
                os.path.join(self.decompose_tmp, constants.AgentPackageMap.GSE, constants.AgentPackageMap.PROJECTS_YAML)
            ),
            default_version=pkg_name_version,
        )

        self.pack_agent_client(self.fetch_support_plugin_os(), constants.CPU_TUPLE, yaml_config)
        self.pack_proxy_client(yaml_config)
        setattr(self, "yaml_config", yaml_config)

        self.clean_up_tmp()

    def extra_file(self, filename: str, recursion: bool = False):
        file_dir_name = os.path.dirname(filename)
        with self.storage.open(name=filename, mode="rb") as tf_from_storage:
            with tarfile.open(fileobj=tf_from_storage) as tf:
                # 检查是否存在可疑内容
                for file_info in tf.getmembers():
                    if file_info.name.startswith("/") or "../" in file_info.name:
                        logger.error(
                            "file-> {file_path} contains member-> {name} try to escape!".format(
                                file_path=file_dir_name, name=file_info.name
                            )
                        )
                        raise exceptions.PluginParseError(_("文件包含非法路径成员 -> {name}，请检查").format(name=file_info.name))
                logger.info(
                    "file-> {file_path} extract to path -> {tmp_dir} success.".format(
                        file_path=file_dir_name, tmp_dir=self.decompose_tmp
                    )
                )
                recursion_files = [
                    os.path.join(self.decompose_tmp, recursion_file.name) for recursion_file in tf.getmembers()
                ]
                tf.extractall(path=self.decompose_tmp)
            if recursion:
                for recursion_file in recursion_files:
                    if tarfile.is_tarfile(recursion_file):
                        with tarfile.open(recursion_file) as tr:
                            tr.extractall(path=self.decompose_tmp)

    def integrate_cert_file(self, source: str, target: str, client_type: str):
        if client_type == constants.NodeType.AGENT:
            for cert in constants.AgentPackageMap.CERT_RULE_MAP[client_type]:
                shutil.copy(os.path.join(self.decompose_tmp, cert), target)
        if client_type == constants.NodeType.PROXY:
            for file in os.listdir(source):
                if constants.AgentPackageMap.CERT_RULE_MAP[client_type].match(file):
                    shutil.copy(os.path.join(self.decompose_tmp, file), target)

        if settings.BKAPP_RUN_ENV == constants.BkappRunEnvType.EE.value:
            for special_file in constants.AgentPackageMap.CERT_RULE_MAP["special"]:
                shutil.copy(os.path.join(source, special_file), target)

    def pack_agent_client(self, os_types: List[str], cpu_types: List[str], yaml_config: Dict[str, str]):
        for os_type in os_types:
            for arch_type in cpu_types:
                tag = f"{os_type}_{arch_type}"
                agent_integrate_tmp = os.path.join(self.integrate_tmp, constants.NodeType.AGENT.lower())
                agent_decompose_tmp = os.path.join(self.decompose_tmp, constants.AgentPackageMap.GSE, f"agent_{tag}")
                cert_integrate_tmp = os.path.join(agent_integrate_tmp, constants.AgentPackageMap.CERT)

                if not os.path.exists(agent_decompose_tmp):
                    logger.warning(_(f"gse package not found sub directory -> {tag}"))
                    continue
                shutil.copytree(agent_decompose_tmp, agent_integrate_tmp)

                self.integrate_cert_file(
                    source=self.decompose_tmp,
                    target=os.path.join(cert_integrate_tmp),
                    client_type=constants.NodeType.AGENT,
                )

                gse_agent_package = GseAgentDesc.assemble_package_name(
                    os_type=os_type,
                    arch_type=arch_type,
                )

                self.compression_package(
                    package_name=gse_agent_package,
                    file_list=[constants.NodeType.AGENT.lower()],
                    os_type=os_type,
                    cpu_arch=arch_type,
                    desc=yaml_config["desc"],
                    version=yaml_config["version"],
                )

                gse_agent_upgrade_package = GseAgentDesc.assemble_package_name(
                    os_type=os_type,
                    arch_type=arch_type,
                    is_upgrade_package=True,
                )

                self.compression_package(
                    package_name=gse_agent_upgrade_package,
                    file_list=[f"{constants.NodeType.AGENT.lower()}/{constants.AgentPackageMap.BIN}"],
                    is_upgrade_package=True,
                    cpu_arch=arch_type,
                    os_type=os_type,
                    desc=yaml_config["desc"],
                    version=yaml_config["version"],
                )

                shutil.rmtree(agent_integrate_tmp)

    @classmethod
    def fetch_support_plugin_os(cls):
        if settings.BKAPP_RUN_ENV == constants.BkappRunEnvType.EE.value:
            support_plugins_os_list = constants.PLUGIN_OS_TUPLE
        else:
            support_plugins_os_list = list(constants.PLUGIN_OS_TUPLE)
            support_plugins_os_list.remove(constants.OsType.AIX.lower())
        return support_plugins_os_list

    @classmethod
    def add_default_yaml_config(cls, yaml_config: Dict[str, str], default_version: str = None) -> Dict[str, str]:
        if not yaml_config.get("desc"):
            yaml_config.update({"desc": constants.AgentPackageMap.AGENT_DEFAULT_MEDIUM["desc"]})
        if default_version is not None:
            yaml_config.update({"version": default_version})

        return yaml_config

    def compression_package(
        self,
        os_type: str,
        cpu_arch: str,
        package_name: str,
        desc: str,
        version: str,
        file_list: List[str],
        is_proxy_package: bool = False,
        is_upgrade_package: bool = False,
        is_support_config_template: bool = False,
    ):
        os.chdir(self.integrate_tmp)
        with tarfile.open(package_name, "w:gz") as tf_file:
            for file in file_list:
                tf_file.add(file)

        # 删除文件目录并转移打包成功的文件
        with open(package_name, mode="rb") as tf_file_fs:
            target_file_path = os.path.join(settings.DOWNLOAD_PATH, package_name)
            self.storage.save(name=target_file_path, content=tf_file_fs)
            tf_file_fs.seek(0)
            md5 = self.storage.get_file_md5(package_name)

        record = {
            "package_name": package_name,
            "cert_name": self.cert_pkg_name,
            "client_name": self.client_name,
            "version": version,
            "source": constants.AgentSourceType.BACKEND,
            "md5": md5,
            "os_type": os_type,
            "description": desc,
            "cpu_arch": cpu_arch,
            "is_proxy_package": is_proxy_package,
            "is_upgrade_package": is_upgrade_package,
            "is_support_config_template": is_support_config_template,
        }
        GseAgentDesc.objects.update_or_create(package_name=package_name, defaults=record)
        logger.info(_(f"Init official agents, pack -> {package_name} success!"))

    def pack_proxy_client(self, yaml_config: Dict[str, str]):
        os_type = constants.OsType.LINUX.lower()
        arch_type = constants.CpuType.x86_64
        proxy_integrate_tmp = os.path.join(self.integrate_tmp, constants.NodeType.PROXY.lower())
        proxy_cert_integrate_tmp = os.path.join(proxy_integrate_tmp, constants.AgentPackageMap.CERT)

        shutil.copytree(
            os.path.join(self.decompose_tmp, constants.AgentPackageMap.GSE, constants.NodeType.PROXY.lower()),
            proxy_integrate_tmp,
        )

        self.integrate_cert_file(
            source=self.decompose_tmp,
            target=os.path.join(proxy_cert_integrate_tmp),
            client_type=constants.NodeType.PROXY,
        )

        # 打包proxy包
        gse_proxy_package = GseAgentDesc.assemble_package_name(
            os_type=os_type,
            arch_type=arch_type,
            is_proxy_package=True,
        )

        self.compression_package(
            package_name=gse_proxy_package,
            file_list=[constants.NodeType.PROXY.lower()],
            is_proxy_package=True,
            os_type=os_type,
            cpu_arch=arch_type,
            version=yaml_config["version"],
            desc=yaml_config["desc"],
        )

        # 打包proxy升级包
        gse_proxy_upgrade_package = GseAgentDesc.assemble_package_name(
            os_type=os_type,
            arch_type=arch_type,
            is_proxy_package=True,
            is_upgrade_package=True,
        )

        self.compression_package(
            package_name=gse_proxy_upgrade_package,
            file_list=[f"{constants.NodeType.PROXY.lower()}/{constants.AgentPackageMap.BIN}"],
            is_proxy_package=True,
            is_upgrade_package=True,
            os_type=os_type,
            cpu_arch=arch_type,
            version=yaml_config["version"],
            desc=yaml_config["desc"],
        )

        shutil.rmtree(proxy_integrate_tmp)

    def clean_up_tmp(self):
        for tmp in [self.decompose_tmp, self.integrate_tmp]:
            if os.path.exists(tmp):
                shutil.rmtree(tmp)

    @classmethod
    def project_yaml_parse(cls, yaml_path: str):
        from apps.backend.agent.tools import yaml_file_parse

        if not os.path.exists(yaml_path):
            logger.error(_(f"pack gse client with plugin -> {yaml_path} not exists"))
            return {}
        else:
            yaml_config = yaml_file_parse(file_path=yaml_path)
            return yaml_config
