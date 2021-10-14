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
import copy
import random
from typing import Callable, List, Optional

import mock

from apps.backend.components.collections.agent import (
    ChooseAccessPointComponent,
    ChooseAccessPointService,
)
from apps.mock_data import common_unit
from apps.mock_data import utils as mock_data_utils
from apps.node_man import constants, models
from apps.utils import basic
from pipeline.component_framework.test import (
    ComponentTestCase,
    ExecuteAssertion,
    Patcher,
)

from . import utils


def ping_time_selector(*args, **kwargs):
    return 1.0


def win_ping_time_selector(*args, **kwargs):
    return {"data": "ping = 3ms"}


class ChooseAccessPointTestCase(utils.AgentServiceBaseTestCase):
    OS_TYPE = constants.OsType.LINUX
    NODE_TYPE = constants.NodeType.AGENT

    except_ap_ids: Optional[List[int]] = None
    ssh_man_mock_client: Optional[utils.SshManMockClient] = None
    ssh_man_ping_time_selector: Optional[Callable] = None

    @classmethod
    def create_ap(cls, name: str, description: str) -> models.AccessPoint:
        # 创建一个测试接入点
        ap_model_data = basic.remove_keys_from_dict(origin_data=common_unit.host.AP_MODEL_DATA, keys=["id"])
        ap_model_data.update({"name": name, "description": description, "is_default": False, "is_enabled": True})
        ap_obj = models.AccessPoint(**ap_model_data)
        ap_obj.save()
        return ap_obj

    def init_mock_clients(self):
        self.ssh_man_mock_client = utils.SshManMockClient(
            ssh_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.RETURN_VALUE.value, return_obj="close"
            ),
            send_cmd_return_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.SIDE_EFFECT.value, return_obj=self.ssh_man_ping_time_selector
            ),
        )

    def init_hosts(self):
        models.Host.objects.filter(bk_host_id__in=self.obj_factory.bk_host_ids).update(
            os_type=self.OS_TYPE, node_type=self.NODE_TYPE, ap_id=constants.DEFAULT_AP_ID
        )

    def setUp(self) -> None:
        self.ssh_man_ping_time_selector = ping_time_selector
        self.init_mock_clients()
        self.init_hosts()
        super().setUp()

    def get_default_case_name(self) -> str:
        return f"{self.NODE_TYPE}-{self.OS_TYPE} 选择接入点成功"

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        return self.common_inputs["subscription_instance_ids"]

    def component_cls(self):
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
                patchers=[Patcher(target=self.SSH_MAN_MOCK_PATH, return_value=self.ssh_man_mock_client)],
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
            return random.choice([None, ChooseAccessPointService.MIN_PING_TIME + 1])

        self.ssh_man_ping_time_selector = ping_error_selector
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
    EXECUTE_CMD_MOCK_PATH = "apps.backend.components.collections.agent.execute_cmd"

    def init_mock_clients(self):
        # windows 用不上 sshMan
        pass

    def setUp(self) -> None:
        mock.patch(target=self.EXECUTE_CMD_MOCK_PATH, side_effect=win_ping_time_selector).start()
        super().setUp()


class LinuxPAgentTestCase(ChooseAccessPointTestCase):
    NODE_TYPE = constants.NodeType.PAGENT

    def init_alive_proxies(self, bk_cloud_id: int):

        ap_obj = self.create_ap(name="Proxy专用接入点", description="用于测试PAgent是否正确通过存活Proxy获取到接入点")
        self.except_ap_ids = [ap_obj.id]

        proxy_host_ids = []
        proxy_data_host_list = []
        proc_status_data_list = []
        init_proxy_num = random.randint(5, 10)
        random_begin_host_id = self.obj_factory.RANDOM_BEGIN_HOST_ID + len(self.obj_factory.bk_host_ids) + 1

        for index in range(init_proxy_num):
            proxy_host_id = random_begin_host_id + index
            proxy_host_ids.append(proxy_host_id)
            proxy_data = copy.deepcopy(common_unit.host.HOST_MODEL_DATA)
            proxy_data.update(
                {
                    "ap_id": ap_obj.id,
                    "bk_cloud_id": bk_cloud_id,
                    "node_type": constants.NodeType.PROXY,
                    "bk_host_id": proxy_host_id,
                }
            )
            proc_status_data = copy.deepcopy(common_unit.host.PROCESS_STATUS_MODEL_DATA)
            proc_status_data.update(
                {
                    "bk_host_id": proxy_host_id,
                    "status": constants.ProcStateType.RUNNING,
                    "proc_type": constants.ProcType.AGENT,
                }
            )
            proxy_data_host_list.append(proxy_data)
            proc_status_data_list.append(proc_status_data)
        self.obj_factory.bulk_create_model(model=models.Host, create_data_list=proxy_data_host_list)
        self.obj_factory.bulk_create_model(model=models.ProcessStatus, create_data_list=proc_status_data_list)

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
