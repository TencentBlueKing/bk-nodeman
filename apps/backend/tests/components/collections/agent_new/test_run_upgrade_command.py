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
import base64
import copy
import os
from typing import Any, Dict, List

from django.conf import settings

from apps.backend.components.collections.agent_new.components import (
    RunUpgradeCommandComponent,
)
from apps.backend.components.collections.agent_new.run_upgrade_command import (
    AGENT_RELOAD_SCRIPTS_TEMPLATE,
    WINDOWS_SCRIPTS_TEMPLATE,
)
from apps.mock_data import common_unit
from apps.node_man import constants
from common.api import JobApi

from . import base
from . import utils as agent_utils


class AgentBaseTestObjFactory(agent_utils.AgentTestObjFactory):
    TEST_HOST_NUM: int = 10
    HOST_OS_TYPE: str = constants.OsType.LINUX
    HOST_OS_TYPE_MAP: Dict[int, str] = {1: constants.OsType.LINUX, 0: constants.OsType.WINDOWS}

    def modify_host_os_type(self, instance_host_info_list) -> List[Dict[str, Any]]:
        for index, instance_host_info in enumerate(instance_host_info_list):
            if self.HOST_OS_TYPE == "HYBRID":
                instance_host_info.update(
                    os_type=self.HOST_OS_TYPE_MAP[index % len(self.HOST_OS_TYPE_MAP)],
                    bk_os_type=constants.BK_OS_TYPE[common_unit.host.HOST_MODEL_DATA["os_type"]],
                )
            else:
                instance_host_info.update(
                    os_type=self.HOST_OS_TYPE,
                    bk_os_type=constants.BK_OS_TYPE[common_unit.host.HOST_MODEL_DATA["os_type"]],
                )

        return self.fill_mock_ip(instance_host_info_list)

    def structure_instance_host_info_list(self) -> List[Dict[str, Any]]:
        """
        构造Agent安装目标实例，如需修改测试样例，可从此处入手
        :return:
        """
        instance_host_info_list = self.fill_mock_ip([copy.deepcopy(self.BASE_INSTANCE_HOST_INFO)])
        for index in range(1, self.TEST_HOST_NUM):
            host_info = copy.deepcopy(instance_host_info_list[0])
            host_info["bk_cloud_id"] = index
            instance_host_info_list.append(host_info)
        return self.modify_host_os_type(self.fill_mock_bk_host_id(instance_host_info_list))


class AgentWindowsTestObjFactory(AgentBaseTestObjFactory):
    HOST_OS_TYPE = constants.OsType.WINDOWS


class AgentHybridTestObjFactory(AgentBaseTestObjFactory):
    """
    测试既包含windows主机又包含linux主机的情况
    """

    HOST_OS_TYPE = "HYBRID"


class PushUpgradePackageLinuxSuccessTest(base.JobBaseTestCase):

    OBJ_FACTORY_CLASS = AgentBaseTestObjFactory

    # 获取Linux测试脚本和Windows测试脚本
    SCRIPT_PATH = os.path.join(settings.BK_SCRIPTS_PATH, "upgrade_agent.sh.tpl")
    with open(SCRIPT_PATH, encoding="utf-8") as fh:
        LINUX_TEST_SCRIPTS = fh.read()

    LINUX_TEST_SCRIPTS = LINUX_TEST_SCRIPTS.format(
        setup_path="/usr/local/gse",
        temp_path="/tmp",
        package_name="gse_client-linux-x86_64_upgrade.tgz",
        node_type="agent",
        reload_cmd=AGENT_RELOAD_SCRIPTS_TEMPLATE.format(setup_path="/usr/local/gse", node_type="agent"),
    )
    WINDOWS_TEST_SCRIPTS = WINDOWS_SCRIPTS_TEMPLATE.format(
        setup_path="c:\\gse",
        temp_path="C:\\tmp",
        package_name="gse_client-windows-x86_64_upgrade.tgz",
        package_name_tar="gse_client-windows-x86_64_upgrade.tgz".replace("tgz", "tar"),
    )
    TEST_SCRIPTS_MAP = {constants.OsType.WINDOWS: WINDOWS_TEST_SCRIPTS, constants.OsType.LINUX: LINUX_TEST_SCRIPTS}

    @classmethod
    def get_default_case_name(cls) -> str:
        return "测试Linux Agent升级脚本成功"

    def component_cls(self):
        return RunUpgradeCommandComponent

    def setUp(self) -> None:
        super().setUp()
        self.common_inputs.update({"package_type": "client"})

    def tearDown(self) -> None:
        record = self.job_api_mock_client.call_recorder.record
        for record_result in record[JobApi.fast_execute_script]:
            fast_execute_script_query_params = record_result.args[0]
            self.assertEqual(
                self.TEST_SCRIPTS_MAP[fast_execute_script_query_params["os_type"]],
                base64.b64decode(fast_execute_script_query_params["script_content"]).decode(),
            )
            super().tearDown()


class PushUpgradePackageWindowsSuccessTest(PushUpgradePackageLinuxSuccessTest):
    OBJ_FACTORY_CLASS = AgentWindowsTestObjFactory

    @classmethod
    def get_default_case_name(cls) -> str:
        return "测试Windows Agent升级脚本成功"

    def component_cls(self):
        return RunUpgradeCommandComponent


class PushUpgradePackageHybridSuccessTest(PushUpgradePackageLinuxSuccessTest):
    OBJ_FACTORY_CLASS = AgentHybridTestObjFactory

    @classmethod
    def get_default_case_name(cls) -> str:
        return "测试Windows与Linux混合 Agent升级脚本成功"

    def component_cls(self):
        return RunUpgradeCommandComponent
