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
import importlib
import random
from typing import Any, Callable, List, Optional

import mock
from six import StringIO

from apps.backend.components.collections.agent_new import choose_access_point
from apps.backend.components.collections.agent_new.components import (
    ChooseAccessPointComponent,
)
from apps.core.remote.tests.base import (
    PARAMIKO_SSH_CLIENT_MOCK_PATH,
    ParamikoSSHMockClient,
)
from apps.node_man import constants, models
from pipeline.component_framework.test import (
    ComponentTestCase,
    ExecuteAssertion,
    Patcher,
)

from . import utils


def ping_time_selector(*args, **kwargs):
    return "1.0"


def win_ping_time_selector(*args, **kwargs):
    return {"data": "ping = 3ms"}


class ChooseAccessPointTestCase(utils.AgentServiceBaseTestCase):
    OS_TYPE = constants.OsType.LINUX
    NODE_TYPE = constants.NodeType.AGENT
    SSH_MAN_MOCK_PATH = "apps.backend.components.collections.agent_new.choose_access_point.SshMan"

    except_ap_ids: Optional[List[int]] = None
    ssh_mock_client: Optional[Any] = None
    ssh_ping_time_selector: Optional[Callable] = None

    def init_mock_clients(self):
        ssh_man_ping_time_selector = self.ssh_ping_time_selector

        class CustomParamikoSSHMockClient(ParamikoSSHMockClient):
            @staticmethod
            def exec_command(command: str, check=False, timeout=None, **kwargs):
                return command, StringIO(ssh_man_ping_time_selector()), StringIO("")

        self.ssh_mock_client = CustomParamikoSSHMockClient

    def init_hosts(self):
        models.Host.objects.filter(bk_host_id__in=self.obj_factory.bk_host_ids).update(
            os_type=self.OS_TYPE, node_type=self.NODE_TYPE, ap_id=constants.DEFAULT_AP_ID
        )

    def start_patch(self):
        pass

    def setUp(self) -> None:
        self.ssh_ping_time_selector = ping_time_selector
        self.init_mock_clients()
        self.init_hosts()
        super().setUp()

    def get_default_case_name(self) -> str:
        return f"{self.NODE_TYPE}-{self.OS_TYPE} 选择接入点成功"

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        return self.common_inputs["subscription_instance_ids"]

    def component_cls(self):
        importlib.reload(choose_access_point)
        ChooseAccessPointComponent.bound_service = choose_access_point.ChooseAccessPointService
        self.start_patch()
        return ChooseAccessPointComponent

    def cases(self):
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=bool(self.fetch_succeeded_sub_inst_ids()),
                    outputs={"succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids()},
                ),
                schedule_assertion=None,
                execute_call_assertion=None,
                patchers=[Patcher(target=PARAMIKO_SSH_CLIENT_MOCK_PATH, return_value=self.ssh_mock_client)],
            )
        ]

    def tearDown(self) -> None:
        host_infos = models.Host.objects.filter(bk_host_id__in=self.obj_factory.bk_host_ids).values(
            "bk_host_id", "ap_id"
        )
        # 验证主机接入点已切换
        for host_info in host_infos:
            if not self.except_ap_ids:
                self.assertTrue(host_info["ap_id"] != constants.DEFAULT_AP_ID)
            else:
                self.assertTrue(host_info["ap_id"] in self.except_ap_ids)

        super().tearDown()


class PingErrorTestCase(ChooseAccessPointTestCase):
    def get_default_case_name(self) -> str:
        return f"{self.NODE_TYPE}-{self.OS_TYPE} ping 不可达"

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        return []

    def setUp(self) -> None:
        self.except_ap_ids = [constants.DEFAULT_AP_ID]
        super().setUp()

    def init_mock_clients(self):
        def ping_error_selector(*args, **kwargs):
            return random.choice(["", str(choose_access_point.ChooseAccessPointService.MIN_PING_TIME + 1)])

        self.ssh_ping_time_selector = ping_error_selector
        super().init_mock_clients()


class AssignedAccessPointTestCase(ChooseAccessPointTestCase):
    """测试已分配接入点的情况"""

    def get_default_case_name(self) -> str:
        return f"{self.NODE_TYPE}-{self.OS_TYPE} 测试主机已分配接入点的情况"

    def init_hosts(self):
        ap_obj = self.create_ap(name="专用接入点", description="用于测试主机已分配接入点的情况")
        models.Host.objects.filter(bk_host_id__in=self.obj_factory.bk_host_ids).update(
            os_type=self.OS_TYPE, node_type=self.NODE_TYPE, ap_id=ap_obj.id
        )


class WindowsAgentTestCase(ChooseAccessPointTestCase):
    OS_TYPE = constants.OsType.WINDOWS
    EXECUTE_CMD_MOCK_PATH = "apps.backend.components.collections.agent_new.choose_access_point.execute_cmd"

    def init_mock_clients(self):
        # windows 用不上 ssh
        pass

    def start_patch(self):
        mock.patch(target=self.EXECUTE_CMD_MOCK_PATH, side_effect=win_ping_time_selector).start()

    def setUp(self) -> None:
        self.start_patch()
        super().setUp()


class LinuxPAgentTestCase(ChooseAccessPointTestCase):
    NODE_TYPE = constants.NodeType.PAGENT

    def init_hosts(self):
        random_cloud_id = random.randint(10, 20)
        self.init_alive_proxies(bk_cloud_id=random_cloud_id)
        models.Host.objects.filter(bk_host_id__in=self.obj_factory.bk_host_ids).update(
            os_type=self.OS_TYPE, node_type=self.NODE_TYPE, bk_cloud_id=random_cloud_id, ap_id=constants.DEFAULT_AP_ID
        )


class NotAliveProxiesTestCase(LinuxPAgentTestCase):
    def get_default_case_name(self) -> str:
        return f"{self.NODE_TYPE}-{self.OS_TYPE} 云区域下无可用Proxy"

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        return []

    def setUp(self) -> None:
        super().setUp()
        self.except_ap_ids = [constants.DEFAULT_AP_ID]
        models.ProcessStatus.objects.update(status=constants.ProcStateType.TERMINATED)
