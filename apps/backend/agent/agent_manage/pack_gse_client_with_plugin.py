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
import re
import shutil
import tarfile

from django.conf import settings
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from apps.backend import exceptions
from apps.core.files.storage import get_storage
from apps.node_man import constants
from apps.node_man.models import AgentConfigTemplate, GseAgentDesc
from apps.utils import files
from common.log import logger


class GseClientPack(object):

    storage = get_storage()
    decompose_tmp = files.mk_and_return_tmpdir()
    integrate_tmp = files.mk_and_return_tmpdir()
    plugin_bin_sub_name = "bin"
    plugin_etc_sub_name = "etc"
    client_cert_sub_name = "cert"

    def pack_gse_client_with_plugins(
        self,
        client_version: str,
        plugins_version: str,
        cert_package: str,
        client_package: str,
        plugins_package: str,
    ):
        setattr(self, "client_version", client_version)
        setattr(self, "plugins_version", plugins_version)
        setattr(self, "cert_package", cert_package)
        self.extra_file(cert_package)
        self.extra_file(client_package)
        self.extra_file(plugins_package, recursion=True)
        self.pack_agent_client(self.fetch_support_plugin_os(), constants.CPU_TUPLE)
        self.pack_proxy_client()
        self.client_config_template_load(
            version=self.client_version, file_path=os.path.join(self.decompose_tmp, "gse", "support-files", "templates")
        )
        self.clean_up_tmp()

    def extra_file(self, filename: str, recursion: bool = False):
        file_dir_name = os.path.dirname(filename)
        with self.storage.open(name=filename, mode="rb") as tf_from_storage:
            with tarfile.open(fileobj=tf_from_storage) as tf:
                # 检查是否存在可疑内容
                for file_info in tf.getmembers():
                    if file_info.name.startswith("/") or "../" in file_info.name:
                        logger.error(
                            "file-> {file_path} contains member-> {name} try to escape!".ormat(
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
            for cert in constants.CERT_RULE_MAP[client_type]:
                shutil.copy(os.path.join(self.decompose_tmp, cert), target)
        if client_type == constants.NodeType.PROXY:
            for file in os.listdir(source):
                if constants.CERT_RULE_MAP[client_type].match(file):
                    shutil.copy(os.path.join(self.decompose_tmp, file), target)

        if settings.BKAPP_RUN_ENV == constants.BkappRunEnvType.EE.value:
            shutil.copy(os.path.join(source, constants.CERT_RULE_MAP["spicial"]), target)

    def pack_agent_client(self, os_types: list, cpu_types: list):
        for os_type in os_types:
            for arch_type in cpu_types:
                tag = f"{os_type}_{arch_type}"
                agent_integrate_tmp = os.path.join(self.integrate_tmp, "agent")
                plugins_integrate_tmp = os.path.join(self.integrate_tmp, "plugins")
                agent_decompose_tmp = os.path.join(self.decompose_tmp, "gse", f"agent_{tag}")
                cert_integrate_tmp = os.path.join(agent_integrate_tmp, self.client_cert_sub_name)

                if not os.path.exists(agent_decompose_tmp):
                    logger.warning(_(f"gse package not found sub directory -> {tag}"))
                    continue
                shutil.copytree(agent_decompose_tmp, agent_integrate_tmp)

                self.integrate_cert_file(
                    source=self.decompose_tmp,
                    target=os.path.join(cert_integrate_tmp),
                    client_type=constants.NodeType.AGENT,
                )

                self.integrate_plugins(source=self.decompose_tmp, target=plugins_integrate_tmp, category=tag)

                gse_agent_package = GseAgentDesc.assemble_package_name(
                    os_type=os_type,
                    arch_type=arch_type,
                    version=self.client_version,
                )

                self.compression_package(package_name=gse_agent_package, file_list=["agent", "plugins"])

                gse_agent_upgrade_package = GseAgentDesc.assemble_package_name(
                    os_type=os_type,
                    arch_type=arch_type,
                    version=self.client_version,
                    is_upgrade_package=True,
                )

                self.compression_package(
                    package_name=gse_agent_upgrade_package,
                    file_list=["agent/bin"],
                )

                shutil.rmtree(plugins_integrate_tmp)
                shutil.rmtree(agent_integrate_tmp)

    @classmethod
    def fetch_support_plugin_os(cls):
        if settings.BKAPP_RUN_ENV == constants.BkappRunEnvType.EE.value:
            support_plugins_os_list = constants.PLUGIN_OS_TUPLE
        else:
            support_plugins_os_list = list(constants.PLUGIN_OS_TUPLE)
            support_plugins_os_list.remove(constants.OsType.AIX.lower())
        return support_plugins_os_list

    def integrate_plugins(self, source: str, target: str, category: str):
        plugins_integrate_bin_tmp = os.path.join(target, self.plugin_bin_sub_name)
        plugins_integrate_etc_tmp = os.path.join(target, self.plugin_etc_sub_name)
        plugin_category = f"plugins_{category}"
        for plugin_sub_dir in [plugins_integrate_etc_tmp, plugins_integrate_bin_tmp]:
            if not os.path.exists(plugin_sub_dir):
                os.makedirs(plugin_sub_dir)

        decompose_plugin_sub_dirs = [sub for sub in os.listdir(os.path.join(source, plugin_category))]
        for sub_dir in decompose_plugin_sub_dirs:
            bin_abs_path = os.path.join(source, plugin_category, sub_dir, self.plugin_bin_sub_name)
            etc_abs_path = os.path.join(source, plugin_category, sub_dir, self.plugin_etc_sub_name)
            for bin_file in os.listdir(bin_abs_path):
                shutil.copy(os.path.join(bin_abs_path, bin_file), os.path.join(target, self.plugin_bin_sub_name))
            # pluginscripts没配置文件目录
            if sub_dir not in ["pluginscripts"]:
                for file in os.listdir(etc_abs_path):
                    shutil.copy(os.path.join(etc_abs_path, file), os.path.join(target, self.plugin_etc_sub_name))

        # 清理模板文件，后续考虑出包层面删掉
        tpl_re = re.compile(".*.tpl")
        for tpl in os.listdir(plugins_integrate_etc_tmp):
            if tpl_re.match(tpl):
                os.remove(os.path.join(plugins_integrate_etc_tmp, tpl))

    def compression_package(
        self,
        package_name: str,
        file_list: list,
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
            "cert": self.cert_package,
            "version": self.client_version,
            "source": "deploy_init",
            "complete_plugin_version": self.plugins_version,
            "md5": md5,
            "is_upgrade_package": is_upgrade_package,
            "is_support_config_template": is_support_config_template,
            "releasing_type": "offline",
        }
        GseAgentDesc.create_or_update_record(**record)
        logger.info(_(f"init official agents, pack -> {package_name} success!"))

    def pack_proxy_client(self):
        os_type = constants.OsType.LINUX.lower()
        arch_type = constants.CpuType.x86_64
        proxy_integrate_tmp = os.path.join(self.integrate_tmp, "proxy")
        proxy_cert_integrate_tmp = os.path.join(proxy_integrate_tmp, self.client_cert_sub_name)
        plugins_integrate_tmp = os.path.join(self.integrate_tmp, "plugins")
        bin_abs_path = os.path.join(proxy_integrate_tmp, "plugins", self.plugin_bin_sub_name)
        etc_abs_path = os.path.join(proxy_integrate_tmp, "plugins", self.plugin_etc_sub_name)

        shutil.copytree(os.path.join(self.decompose_tmp, "gse", "proxy"), proxy_integrate_tmp)

        for sub_path in [bin_abs_path, etc_abs_path]:
            if not os.path.exists(sub_path):
                os.makedirs(sub_path)

        self.integrate_cert_file(
            source=self.decompose_tmp,
            target=os.path.join(proxy_cert_integrate_tmp),
            client_type=constants.NodeType.PROXY,
        )
        self.integrate_plugins(
            source=self.decompose_tmp, target=plugins_integrate_tmp, category=f"{os_type}_{arch_type}"
        )

        gse_proxy_package = GseAgentDesc.assemble_package_name(
            os_type=os_type,
            arch_type=arch_type,
            version=self.client_version,
            is_proxy_package=True,
        )

        self.compression_package(package_name=gse_proxy_package, file_list=["proxy", "plugins"])

        gse_proxy_upgrade_package = GseAgentDesc.assemble_package_name(
            os_type=os_type,
            arch_type=arch_type,
            version=self.client_version,
            is_proxy_package=True,
            is_upgrade_package=True,
        )

        self.compression_package(
            package_name=gse_proxy_upgrade_package,
            file_list=["proxy/bin"],
        )

        shutil.rmtree(plugins_integrate_tmp)
        shutil.rmtree(proxy_integrate_tmp)

    def clean_up_tmp(self):
        for tmp in [self.decompose_tmp, self.integrate_tmp]:
            if os.path.exists(tmp):
                shutil.rmtree(tmp)

    @classmethod
    def client_config_template_load(cls, file_path: str, version: str):
        # TODO: 使用指定cpu类型精准匹配
        agent_config_re = re.compile(r"^agent_(?P<os_type>.*)_(?P<cpu_arch>.*)#etc#(?P<config>.*)")
        proxy_config_re = re.compile(r"^proxy#etc#(?P<config>.*)")

        for config_file in os.listdir(os.path.join(file_path)):
            template_file_path = os.path.join(file_path, config_file)
            agent_match = agent_config_re.match(config_file)
            proxy_match = proxy_config_re.match(config_file)
            with open(template_file_path) as template_fs:
                if agent_match is not None:
                    agent_info_dict = agent_match.groupdict()
                    os_type = agent_info_dict["os_type"]
                    cpu_arch = agent_info_dict["cpu_arch"]
                    config = agent_info_dict["config"]
                    config_template_obj, __ = AgentConfigTemplate.objects.update_or_create(
                        name=config,
                        version=version,
                        os_type=os_type,
                        cpu_arch=cpu_arch,
                        is_proxy_config=False,
                        defaults=dict(
                            content=template_fs.read(),
                            is_release_version=True,
                            creator="system",
                            create_time=timezone.now(),
                            source_app_code="bk_nodeman",
                        ),
                    )
                elif proxy_match is not None:
                    proxy_info_dict = proxy_match.groupdict()
                    config = proxy_info_dict["config"]
                    config_template_obj, __ = AgentConfigTemplate.objects.update_or_create(
                        name=config,
                        version=version,
                        os_type=constants.OsType.LINUX.lower(),
                        cpu_arch=constants.CpuType.x86_64,
                        is_proxy_config=True,
                        defaults=dict(
                            content=template_fs.read(),
                            is_release_version=True,
                            creator="system",
                            create_time=timezone.now(),
                            source_app_code="bk_nodeman",
                        ),
                    )
                else:
                    continue
                logger.info(
                    "template -> {config} is create for gse client"
                    "version -> {version}".format(
                        config=config_template_obj.name,
                        version=config_template_obj.version,
                    )
                )
