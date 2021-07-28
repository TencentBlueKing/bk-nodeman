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
from django.test import TestCase
from mock import MagicMock

from apps.backend.components.collections.agent import (
    ChooseAccessPointComponent,
    ChooseAccessPointService,
)
from apps.backend.tests.components.collections.agent import utils
from apps.node_man import constants, models
from pipeline.component_framework.test import (
    ComponentTestCase,
    ComponentTestMixin,
    ExecuteAssertion,
    Patcher,
)

DESCRIPTION = "选择接入点"

COMMON_INPUTS = utils.AgentTestObjFactory.inputs(
    attr_values={"description": DESCRIPTION, "bk_host_id": utils.BK_HOST_ID},
    # 主机信息保持和默认一致
    instance_info_attr_values={},
)


class ChooseAccessPointTestService(ChooseAccessPointService):
    id = utils.JOB_TASK_PIPELINE_ID
    root_pipeline_id = utils.INSTANCE_RECORD_ROOT_PIPELINE_ID


class ChooseAccessPointTestComponent(ChooseAccessPointComponent):
    bound_service = ChooseAccessPointTestService


ACCESS_POINTS = [
    {
        "name": "测试接入点1",
        "btfileserver": [],
        "dataserver": [],
        "taskserver": [
            {"inner_ip": "20.8.6.3", "outer_ip": "20.8.6.3"},
            {"inner_ip": "20.8.6.4", "outer_ip": "20.8.6.4"},
        ],
        "zk_hosts": [],
        "package_inner_url": "http://127.0.0.1/download",
        "package_outer_url": "http://127.0.0.1/download",
        "agent_config": "~",
        "description": "~",
    },
    {
        "name": "测试接入点2",
        "btfileserver": [],
        "dataserver": [],
        "taskserver": [
            {"inner_ip": "20.8.6.1", "outer_ip": "20.8.6.1"},
            {"inner_ip": "20.8.6.2", "outer_ip": "20.8.6.2"},
        ],
        "zk_hosts": [],
        "package_inner_url": "http://127.0.0.1/download",
        "package_outer_url": "http://127.0.0.1/download",
        "agent_config": "~",
        "description": "~",
    },
]

SSH_MAN_MOCK_PATH = "apps.backend.components.collections.agent.SshMan"


def ping_time_selector(*args, **kwargs):
    if "20.8.6.1" in args[0]:
        return 1.5
    if "20.8.6.2" in args[0]:
        return 2.5
    if "20.8.6.3" in args[0]:
        return 2.0
    if "20.8.6.4" in args[0]:
        return 2.1
    # 给默认接入点一个特别大的ping值
    return 10000


class SshManPlusMockClient(utils.SshManMockClient):
    def __init__(
        self,
        get_and_set_prompt_return=None,
        send_cmd_return=ping_time_selector,
        safe_close_return=None,
        ssh_return=None,
    ):
        super().__init__(get_and_set_prompt_return, safe_close_return, ssh_return)
        # 替换send_cmd为side_effect类型
        self.send_cmd = MagicMock(side_effect=send_cmd_return)


class AgentChooseApSuccessTest(TestCase, ComponentTestMixin):
    SSH_MOCK_CLIENT = SshManPlusMockClient(ssh_return="close")

    def setUp(self):
        utils.AgentTestObjFactory.init_db()
        ap_objs = [models.AccessPoint(**ap_param) for ap_param in ACCESS_POINTS]
        models.AccessPoint.objects.bulk_create(ap_objs)

    def component_cls(self):
        return ChooseAccessPointTestComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试Agent选择接入点成功：Linux主机",
                inputs=COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(success=True, outputs={}),
                schedule_assertion=None,
                execute_call_assertion=None,
                patchers=[Patcher(target=SSH_MAN_MOCK_PATH, return_value=self.SSH_MOCK_CLIENT)],
            )
        ]

    def tearDown(self):
        min_ping_ap = models.AccessPoint.objects.get(name="测试接入点2")
        # 测试接入点选择是否正确，选ping均值最小的
        self.assertTrue(models.Host.objects.filter(bk_host_id=utils.BK_HOST_ID, ap_id=min_ping_ap.id).exists())

        # 状态检查
        self.assertTrue(
            models.JobTask.objects.filter(bk_host_id=utils.BK_HOST_ID, current_step__endswith=DESCRIPTION).exists()
        )


def win_ping_time_selector(*args, **kwargs):
    if "20.8.6.1" in args[0]:
        return {"data": "ping = 3ms"}
    if "20.8.6.2" in args[0]:
        return {"data": "ping = 4ms"}
    if "20.8.6.3" in args[0]:
        return {"data": "ping = 2ms"}
    if "20.8.6.4" in args[0]:
        return {"data": "ping = 2ms"}
    # 给默认接入点一个特别大的ping值
    return {"data": "ping = 10000ms"}


class AgentChooseApWinSuccessTest(TestCase, ComponentTestMixin):
    EXECUTE_CMD_MOCK_PATH = "apps.backend.components.collections.agent.execute_cmd"
    SSH_MOCK_CLIENT = SshManPlusMockClient(ssh_return="close")

    def setUp(self):
        utils.AgentTestObjFactory.init_db()
        ap_objs = [models.AccessPoint(**ap_param) for ap_param in ACCESS_POINTS]
        models.AccessPoint.objects.bulk_create(ap_objs)

        # 更改安装主机的操作系统
        models.Host.objects.filter(bk_host_id=utils.BK_HOST_ID).update(os_type=constants.OsType.WINDOWS)

    def component_cls(self):
        return ChooseAccessPointTestComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试Agent选择接入点成功: 测试Window主机",
                inputs=COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(success=True, outputs={}),
                schedule_assertion=None,
                execute_call_assertion=None,
                patchers=[
                    Patcher(target=SSH_MAN_MOCK_PATH, return_value=self.SSH_MOCK_CLIENT),
                    Patcher(target=self.EXECUTE_CMD_MOCK_PATH, side_effect=win_ping_time_selector),
                ],
            )
        ]

    def tearDown(self):
        min_ping_ap = models.AccessPoint.objects.get(name="测试接入点1")
        # 测试接入点选择是否正确，选ping均值最小的
        self.assertTrue(models.Host.objects.filter(bk_host_id=utils.BK_HOST_ID, ap_id=min_ping_ap.id).exists())

        # 状态检查
        self.assertTrue(
            models.JobTask.objects.filter(bk_host_id=utils.BK_HOST_ID, current_step__endswith=DESCRIPTION).exists()
        )


class HadApSuccessTest(TestCase, ComponentTestMixin):
    def setUp(self):
        utils.AgentTestObjFactory.init_db()
        ap_objs = [models.AccessPoint(**ap_param) for ap_param in ACCESS_POINTS]
        models.AccessPoint.objects.bulk_create(ap_objs)

        ap_id = models.AccessPoint.objects.get(name="测试接入点1").id
        # 已分配接入点
        models.Host.objects.filter(bk_host_id=utils.BK_HOST_ID).update(ap_id=ap_id)

    def component_cls(self):
        return ChooseAccessPointTestComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试Agent选择接入点成功: 已分配接入点",
                inputs=COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(success=True, outputs={}),
                schedule_assertion=None,
                execute_call_assertion=None,
                patchers=None,
            )
        ]

    def tearDown(self):
        # 状态检查
        self.assertTrue(
            models.JobTask.objects.filter(bk_host_id=utils.BK_HOST_ID, current_step__endswith=DESCRIPTION).exists()
        )


class NotApFailTest(TestCase, ComponentTestMixin):
    SSH_MOCK_CLIENT = SshManPlusMockClient(ssh_return="close")

    def setUp(self):
        utils.AgentTestObjFactory.init_db()
        # 清空全部接入点
        models.AccessPoint.objects.all().delete()

    def component_cls(self):
        return ChooseAccessPointTestComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试不存在接入点，需要全局配置",
                inputs=COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(success=False, outputs={}),
                schedule_assertion=None,
                execute_call_assertion=None,
                patchers=[Patcher(target=SSH_MAN_MOCK_PATH, return_value=self.SSH_MOCK_CLIENT)],
            )
        ]

    def tearDown(self):
        # 不存在接入点，此时主机记录系统预留的AP_ID
        self.assertTrue(models.Host.objects.filter(bk_host_id=utils.BK_HOST_ID, ap_id=utils.DEFAULT_AP_ID).exists())

        # 状态检查
        self.assertTrue(
            models.JobTask.objects.filter(bk_host_id=utils.BK_HOST_ID, current_step__endswith=DESCRIPTION).exists()
        )


class ApPingTimeOutFailTest(TestCase, ComponentTestMixin):
    # 默认接入点ping值是10000，大于系统阈值9999，选择接入点失败
    SSH_MOCK_CLIENT = SshManPlusMockClient(ssh_return="close")

    def setUp(self):
        utils.AgentTestObjFactory.init_db()

    def component_cls(self):
        return ChooseAccessPointTestComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试没有可用接入点，ping超时",
                inputs=COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(success=False, outputs={}),
                schedule_assertion=None,
                execute_call_assertion=None,
                patchers=[Patcher(target=SSH_MAN_MOCK_PATH, return_value=self.SSH_MOCK_CLIENT)],
            )
        ]

    def tearDown(self):
        # 没有可用接入点时，主机中预留系统预置的AP_ID
        self.assertTrue(models.Host.objects.filter(bk_host_id=utils.BK_HOST_ID, ap_id=utils.DEFAULT_AP_ID).exists())

        # 状态检查
        self.assertTrue(
            models.JobTask.objects.filter(bk_host_id=utils.BK_HOST_ID, current_step__endswith=DESCRIPTION).exists()
        )
