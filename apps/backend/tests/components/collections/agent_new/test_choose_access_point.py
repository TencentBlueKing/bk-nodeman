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
import copy
import importlib
import random
from typing import Any, Callable, List, Optional

import asyncssh
import mock

from apps.backend.components.collections.agent_new import choose_access_point
from apps.backend.components.collections.agent_new.components import (
    ChooseAccessPointComponent,
)
from apps.core.remote import exceptions
from apps.core.remote.tests.base import (
    AsyncMockConn,
    AsyncSSHMockClient,
    get_asyncssh_connect_mock_patch,
)
from apps.mock_data import common_unit
from apps.node_man import constants, models
from pipeline.component_framework.test import (
    ComponentTestCase,
    ExecuteAssertion,
    Patcher,
)

from . import utils

WINDOWS_PING_STDOUT = """
Pinging 127.0.0.1 with 32 bytes of data:
Reply from 127.0.0.1: bytes=32 time=2ms TTL=128
Reply from 127.0.0.1: bytes=32 time=2ms TTL=128
Reply from 127.0.0.1: bytes=32 time=2ms TTL=128
Reply from 127.0.0.1: bytes=32 time=2ms TTL=128

Ping statistics for 127.0.0.1:
    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),
Approximate round trip times in milli-seconds:
    Minimum = 2ms, Maximum = 2ms, Average = 2ms
"""


def ping_time_selector(*args, **kwargs):
    return "1.0"


def win_ping_time_selector(*args, **kwargs):
    return {"data": WINDOWS_PING_STDOUT}


class ChooseAccessPointTestCase(utils.AgentServiceBaseTestCase):
    OS_TYPE = constants.OsType.LINUX
    NODE_TYPE = constants.NodeType.AGENT
    SSH_MAN_MOCK_PATH = "apps.backend.components.collections.agent_new.choose_access_point.SshMan"
    EXECUTE_CMD_MOCK_PATH = "apps.backend.components.collections.agent_new.choose_access_point.execute_cmd"

    except_ap_ids: Optional[List[int]] = None
    ssh_mock_client: Optional[Any] = None
    ssh_ping_time_selector: Optional[Callable] = None

    def init_mock_clients(self):
        ssh_man_ping_time_selector = self.ssh_ping_time_selector

        class CustomAsyncSSHMockClient(AsyncSSHMockClient):
            async def run(self, command: str, check=False, timeout=None, **kwargs):
                return asyncssh.SSHCompletedProcess(
                    command=command, exit_status=0, stdout=ssh_man_ping_time_selector(), stderr=""
                )

        self.ssh_mock_client = CustomAsyncSSHMockClient

    def init_hosts(self):
        models.Host.objects.filter(bk_host_id__in=self.obj_factory.bk_host_ids).update(
            os_type=self.OS_TYPE, node_type=self.NODE_TYPE, ap_id=constants.DEFAULT_AP_ID
        )

    def start_patch(self):
        get_asyncssh_connect_mock_patch(self.ssh_mock_client).start()

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
                patchers=[Patcher(target=self.EXECUTE_CMD_MOCK_PATH, side_effect=win_ping_time_selector)],
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

    @classmethod
    def tearDownClass(cls):
        mock.patch.stopall()
        super().tearDownClass()


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


class WindowsSSHAgentTestCase(ChooseAccessPointTestCase):
    OS_TYPE = constants.OsType.WINDOWS

    def get_default_case_name(self) -> str:
        return f"{self.NODE_TYPE}-{self.OS_TYPE} 通过 SSH 通道检测网络情况"

    def init_mock_clients(self):
        def ping_error_selector(*args, **kwargs):
            return WINDOWS_PING_STDOUT

        self.ssh_ping_time_selector = ping_error_selector
        super().init_mock_clients()


class WindowsAgentTestCase(ChooseAccessPointTestCase):
    OS_TYPE = constants.OsType.WINDOWS

    def get_default_case_name(self) -> str:
        return f"{self.NODE_TYPE}-{self.OS_TYPE} 通过 WMI 检测网络情况"

    def start_patch(self):
        # 让 Windows SSH 检测失败
        class AsyncMockErrorConn(AsyncMockConn):
            async def connect(self):
                raise exceptions.DisconnectError

        mock.patch("apps.backend.components.collections.common.remote.conns.AsyncsshConn", AsyncMockErrorConn).start()


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


class ProxyTestCase(ChooseAccessPointTestCase):
    NODE_TYPE = constants.NodeType.PROXY

    def init_hosts(self):
        bk_cloud_id = random.randint(10, 1000)
        cloud_model_data = copy.deepcopy(common_unit.host.CLOUD_MODEL_DATA)
        cloud_model_data.update(bk_cloud_id=bk_cloud_id, ap_id=constants.DEFAULT_AP_ID)
        models.Cloud.objects.create(**cloud_model_data)
        models.Host.objects.filter(bk_host_id__in=self.obj_factory.bk_host_ids).update(
            os_type=self.OS_TYPE,
            node_type=self.NODE_TYPE,
            bk_cloud_id=bk_cloud_id,
            ap_id=random.randint(constants.DEFAULT_AP_ID + 10, constants.DEFAULT_AP_ID + 100),
        )

    def tearDown(self) -> None:
        self.except_ap_ids = [constants.DEFAULT_AP_ID]
        super().tearDown()
