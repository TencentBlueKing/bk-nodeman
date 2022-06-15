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

from apps.mock_data import common_unit
from apps.node_man import constants
from apps.utils import files
from apps.utils.unittest.testcase import CustomAPITestCase


class AgentPkgBaseTestCase(CustomAPITestCase):
    TMP_DIR: str = None
    OFFICIAL_AGENT: str = None
    DOWNLOAD_PATH: str = None

    @classmethod
    def setUpClass(cls):
        # TODO: 统一环境变量覆盖模式
        cls.TMP_DIR = files.mk_and_return_tmpdir()

        cls.BK_OFFICIAL_AGENT_INIT_PATH = os.path.join(cls.TMP_DIR, "official_agent")

        cls.DOWNLOAD_PATH = os.path.join(cls.TMP_DIR, "download")

        super().setUpClass()

    def setUp(self):
        self.mock_agent_pkg_path = self.mock_agent_pkg()
        self.mock_cert_pkg()

        for dir_name in [
            self.BK_OFFICIAL_AGENT_INIT_PATH,
            self.DOWNLOAD_PATH,
            os.path.join(self.TMP_DIR, constants.AgentPackageMap.CERT),
        ]:
            if not os.path.isdir(dir_name):
                os.makedirs(dir_name)
        super().setUp()

    def mock_cert_pkg(self):
        cert_path = os.path.join(self.TMP_DIR, constants.AgentPackageMap.CERT)
        os.makedirs(cert_path)

        for cert_file in common_unit.agent.CERT_FILES:
            cert_file_abs_path = os.path.join(cert_path, cert_file)
            open(cert_file_abs_path, "w+").close()

        os.chdir(cert_path)
        with tarfile.open(common_unit.agent.CERT_PKG_NAME, "w:gz") as tf:
            for file in os.listdir(cert_path):
                tf.add(file)
        return os.path.join(cert_path, common_unit.agent.CERT_PKG_NAME)

    def mock_agent_pkg(self):
        gse_agent_path = os.path.join(self.TMP_DIR, "gse_agent")
        agent_pkg_name = (
            f"{common_unit.agent.AGENT_PKG_HEAD_NAME}-{common_unit.agent.AGENT_PKG_VERSION}."
            f"{common_unit.agent.AGENT_PKG_SUFFIX_NAME}"
        )
        agent_platform_bin_tree = {
            os.path.join(
                gse_agent_path, constants.AgentPackageMap.GSE, platform_sub_path, constants.AgentPackageMap.BIN
            ): common_unit.agent.AGENT_PLATFORM_BIN_FILES
            for platform_sub_path in common_unit.agent.AGENT_PLATFORM_DIRS
        }

        # agent
        for agent_platform_path, agent_file_list in agent_platform_bin_tree.items():
            os.makedirs(agent_platform_path)
            os.makedirs(agent_platform_path.replace(constants.AgentPackageMap.BIN, constants.AgentPackageMap.ETC))
            os.makedirs(agent_platform_path.replace(constants.AgentPackageMap.BIN, constants.AgentPackageMap.CERT))

            for file in agent_file_list:
                open(os.path.join(agent_platform_path, file), "w+").close()

        # proxy
        for proxy_sub_path in [
            constants.AgentPackageMap.BIN,
            constants.AgentPackageMap.ETC,
            constants.AgentPackageMap.CERT,
        ]:
            os.makedirs(
                os.path.join(
                    gse_agent_path, constants.AgentPackageMap.GSE, constants.NodeType.PROXY.lower(), proxy_sub_path
                )
            )

        for proxy_file in common_unit.agent.PROXY_PLATFORM_BIN_FILES:
            open(
                os.path.join(
                    gse_agent_path,
                    constants.AgentPackageMap.GSE,
                    constants.NodeType.PROXY.lower(),
                    constants.AgentPackageMap.BIN,
                    proxy_file,
                ),
                "w+",
            ).close()

        # template-agent
        agent_template_path = os.path.join(
            gse_agent_path,
            constants.AgentPackageMap.GSE,
            constants.AgentPackageMap.SUPPORT_FILES,
            constants.AgentPackageMap.TEMPLATE,
        )
        os.makedirs(os.path.join(agent_template_path))

        agent_platform_config_files = [
            f"{constants.NodeType.AGENT.lower()}_{os_type.lower()}_{cpu_arch}#{constants.AgentPackageMap.ETC}"
            f"#{common_unit.agent.AGENT_CONFIG_FILE_NAME}"
            for os_type in constants.OS_TUPLE
            for cpu_arch in constants.CPU_TUPLE
        ]

        for platform_config_file in agent_platform_config_files:
            with open(os.path.join(agent_template_path, platform_config_file), "w+") as f:
                f.write(common_unit.agent.AGENT_CONFIG_TEMPLATE)

        # template-proxy
        proxy_config_file_name = (
            f"{constants.NodeType.PROXY.lower()}#{constants.AgentPackageMap.ETC}"
            f"#{common_unit.agent.PROXY_CONFIG_FILE_NAME}"
        )

        with open(os.path.join(agent_template_path, proxy_config_file_name), "w+") as e:
            e.write(common_unit.agent.PROXY_BTSVR_CONFIG_TEMPLATE)

        os.chdir(gse_agent_path)

        # project.yaml

        with open(
            os.path.join(gse_agent_path, constants.AgentPackageMap.GSE, constants.AgentPackageMap.PROJECTS_YAML), "w+"
        ) as yf:

            yf.write(common_unit.agent.AGENT_YAML_CONFIG)

        with tarfile.open(agent_pkg_name, "w:gz") as tf_file:
            for sub_dir in os.listdir(gse_agent_path):
                tf_file.add(sub_dir)

        return agent_pkg_name

    def tearDown(self):
        if os.path.exists(self.TMP_DIR):
            shutil.rmtree(self.TMP_DIR)

        super().tearDown()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.TMP_DIR):
            shutil.rmtree(cls.TMP_DIR)

        super().tearDownClass()
