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
import base64
import os

from django.conf import settings

from apps.backend.components.collections.agent_new.components import (
    RunUpgradeCommandComponent,
)
from apps.backend.components.collections.agent_new.run_upgrade_command import (
    AGENT_RELOAD_CMD_TEMPLATE,
    NODE_TYPE__RELOAD_CMD_TPL_MAP,
    PROCESS_PULL_CONFIGURATION_CMD,
    WINDOWS_UPGRADE_CMD_TEMPLATE,
)
from apps.node_man import constants, models
from common.api import JobApi
from env.constants import GseVersion

from . import base


class RunUpgradeCommandSuccessTestCase(base.JobBaseTestCase):
    # 获取Linux测试脚本和Windows测试脚本
    SCRIPT_PATH = os.path.join(settings.BK_SCRIPTS_PATH, "upgrade_agent.sh.tpl")
    with open(SCRIPT_PATH, encoding="utf-8") as fh:
        LINUX_TEST_SCRIPT_TEMPLATE = fh.read()

    LINUX_TEST_SCRIPTS = LINUX_TEST_SCRIPT_TEMPLATE.format(
        setup_path="/usr/local/gse",
        temp_path="/tmp",
        package_name="gse_client-linux-x86_64_upgrade.tgz",
        node_type="agent",
        reload_cmd=AGENT_RELOAD_CMD_TEMPLATE.format(setup_path="/usr/local/gse", node_type="agent", procs="gse_agent"),
        process_pull_configuration_cmd=PROCESS_PULL_CONFIGURATION_CMD,
        pkg_cpu_arch="x86_64",
    )
    WINDOWS_TEST_SCRIPTS = WINDOWS_UPGRADE_CMD_TEMPLATE.format(
        setup_path="c:\\gse", temp_path="C:\\tmp", package_name="gse_client-windows-x86_64_upgrade.tgz"
    )
    TEST_SCRIPTS_MAP = {constants.OsType.WINDOWS: WINDOWS_TEST_SCRIPTS, constants.OsType.LINUX: LINUX_TEST_SCRIPTS}

    @classmethod
    def setup_obj_factory(cls):
        cls.obj_factory.init_host_num = 10
        cls.obj_factory.host_os_type_options = [constants.OsType.LINUX]

    @classmethod
    def get_default_case_name(cls) -> str:
        return "测试 Linux 机器 Agent 升级脚本成功"

    def component_cls(self):
        return RunUpgradeCommandComponent

    def tearDown(self) -> None:
        record = self.job_api_mock_client.call_recorder.record
        for record_result in record[JobApi.fast_execute_script]:
            fast_execute_script_query_params = record_result.args[0]
            self.assertEqual(
                self.TEST_SCRIPTS_MAP[fast_execute_script_query_params["os_type"]],
                base64.b64decode(fast_execute_script_query_params["script_content"]).decode(),
            )
            super().tearDown()


class LinuxAgent2UpgradeSuccessTestCase(RunUpgradeCommandSuccessTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "测试 Linux 机器 Agent2 升级脚本成功"

    def structure_common_inputs(self):
        inputs = super().structure_common_inputs()
        inputs["meta"] = {"GSE_VERSION": GseVersion.V2.value}
        return inputs

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.obj_factory.init_gse_package_desc()
        sub_step_obj: models.SubscriptionStep = cls.obj_factory.sub_step_objs[0]
        sub_step_obj.config.update({"name": "gse_agent", "version": "2.0.0"})
        sub_step_obj.save()

    def tearDown(self) -> None:
        record = self.job_api_mock_client.call_recorder.record
        test_script_content = self.LINUX_TEST_SCRIPT_TEMPLATE.format(
            setup_path="/usr/local/gse",
            temp_path="/tmp",
            package_name="gse_agent-2.0.0.tgz",
            node_type="agent",
            reload_cmd=NODE_TYPE__RELOAD_CMD_TPL_MAP["agent"].format(setup_path="/usr/local/gse", node_type="agent"),
            process_pull_configuration_cmd="",
            pkg_cpu_arch="x86_64",
        )
        for record_result in record[JobApi.fast_execute_script]:
            fast_execute_script_query_params = record_result.args[0]
            self.assertEqual(
                test_script_content,
                base64.b64decode(fast_execute_script_query_params["script_content"]).decode(),
            )


class WindowsSuccessTestCase(RunUpgradeCommandSuccessTestCase):
    @classmethod
    def setup_obj_factory(cls):
        cls.obj_factory.init_host_num = 10
        cls.obj_factory.host_os_type_options = [constants.OsType.WINDOWS]

    @classmethod
    def get_default_case_name(cls) -> str:
        return "测试 Windows 机器 Agent 升级脚本成功"

    def component_cls(self):
        return RunUpgradeCommandComponent


class HybridSuccessTest(RunUpgradeCommandSuccessTestCase):
    @classmethod
    def setup_obj_factory(cls):
        cls.obj_factory.init_host_num = 10
        cls.obj_factory.host_os_type_options = [constants.OsType.WINDOWS, constants.OsType.LINUX]

    @classmethod
    def get_default_case_name(cls) -> str:
        return "测试Windows与Linux混合 Agent升级脚本成功"

    def component_cls(self):
        return RunUpgradeCommandComponent
