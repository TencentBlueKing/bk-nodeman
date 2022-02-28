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
import json
import re
from typing import List

import mock
from django.conf import settings

from apps.backend.agent.tools import gen_commands
from apps.backend.components.collections.agent_new import install
from apps.backend.components.collections.agent_new.components import InstallComponent
from apps.backend.constants import REDIS_INSTALL_CALLBACK_KEY_TPL
from apps.backend.utils.redis import REDIS_INST
from apps.core.remote import exceptions
from apps.core.remote.tests import base
from apps.core.remote.tests.base import AsyncMockConn
from apps.mock_data import api_mkd
from apps.mock_data import utils as mock_data_utils
from apps.node_man import constants, models
from pipeline.component_framework.test import (
    ComponentTestCase,
    ExecuteAssertion,
    ScheduleAssertion,
)

from . import utils


class InstallBaseTestCase(utils.AgentServiceBaseTestCase):
    OS_TYPE = constants.OsType.LINUX
    NODE_TYPE = constants.NodeType.AGENT
    JOB_API_MOCK_PATH = "apps.backend.components.collections.agent_new.install.JobApi"
    EXECUTE_CMD_MOCK_PATH = "apps.backend.components.collections.agent_new.install.execute_cmd"
    PUT_FILE_MOCK_PATH = "apps.backend.components.collections.agent_new.install.put_file"

    @staticmethod
    def update_callback_url():
        settings.BKAPP_NODEMAN_CALLBACK_URL = "http://127.0.0.1/backend"
        settings.BKAPP_NODEMAN_OUTER_CALLBACK_URL = "http://127.0.0.1/backend"

    def init_mock_clients(self):
        self.job_mock_client = api_mkd.job.utils.JobApiMockClient(
            fast_execute_script_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.RETURN_VALUE.value, return_obj={"job_instance_id": 1}
            ),
        )

    def init_redis_data(self):
        # 初始化redis数据，用于schedule时读取解析
        for sub_inst_id in self.common_inputs["subscription_instance_ids"]:
            name = REDIS_INSTALL_CALLBACK_KEY_TPL.format(sub_inst_id=sub_inst_id)
            json_dumps_logs = [
                json.dumps(log)
                for log in [
                    {
                        "timestamp": "1580870937",
                        "level": "INFO",
                        "step": "report_cpu_arch",
                        "log": "aarch64",
                        "status": "DONE",
                    },
                    {
                        "timestamp": "1580870937",
                        "level": "INFO",
                        "step": "check_deploy_result",
                        "log": "gse agent has been deployed successfully",
                        "status": "DONE",
                    },
                ]
            ]
            REDIS_INST.lpush(name, *json_dumps_logs)

    def init_hosts(self):
        models.Host.objects.filter(bk_host_id__in=self.obj_factory.bk_host_ids).update(
            os_type=self.OS_TYPE, node_type=self.NODE_TYPE, ap_id=constants.DEFAULT_AP_ID
        )

    def update_common_inputs(self):
        self.common_inputs.update(success_callback_step="check_deploy_result")

    def start_patch(self):
        mock.patch(self.JOB_API_MOCK_PATH, self.job_mock_client).start()
        mock.patch(target=self.EXECUTE_CMD_MOCK_PATH, return_value="").start()
        mock.patch(target=self.PUT_FILE_MOCK_PATH, return_value="").start()
        base.get_asyncssh_connect_mock_patch().start()

    def setUp(self) -> None:
        self.update_callback_url()
        self.init_mock_clients()
        self.init_hosts()
        super().setUp()
        self.update_common_inputs()
        self.start_patch()

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        return self.common_inputs["subscription_instance_ids"]

    def component_cls(self):
        # 模块 mock 装饰器，需要重新加载
        # 参考：https://stackoverflow.com/questions/7667567/can-i-patch-a-python-decorator-before-it-wraps-a-function
        importlib.reload(install)
        InstallComponent.bound_service = install.InstallService
        self.start_patch()
        return InstallComponent

    def cases(self):
        self.init_redis_data()
        return [
            ComponentTestCase(
                name=f"测试{self.OS_TYPE}-{self.NODE_TYPE}安装",
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=bool(self.fetch_succeeded_sub_inst_ids()),
                    outputs={
                        "succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids(),
                        "scheduling_sub_inst_ids": self.fetch_succeeded_sub_inst_ids(),
                        "polling_time": 0,
                    },
                ),
                schedule_assertion=ScheduleAssertion(
                    success=True,
                    schedule_finished=True,
                    outputs={
                        "succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids(),
                        "scheduling_sub_inst_ids": [],
                        "polling_time": 0,
                    },
                ),
                execute_call_assertion=None,
                patchers=[],
            )
        ]

    @classmethod
    def tearDownClass(cls):
        mock.patch.stopall()
        super().tearDownClass()


class LinuxInstallTestCase(InstallBaseTestCase):
    def test_gen_agent_command(self):
        host = models.Host.objects.get(bk_host_id=self.obj_factory.bk_host_ids[0])
        installation_tool = gen_commands(host, mock_data_utils.JOB_TASK_PIPELINE_ID, is_uninstall=False, sub_inst_id=0)
        token = re.match(r"(.*) -c (.*?) -O", installation_tool.run_cmd).group(2)
        run_cmd = (
            f"nohup bash /tmp/setup_agent.sh -s {mock_data_utils.JOB_TASK_PIPELINE_ID}"
            f" -r http://127.0.0.1/backend -l http://127.0.0.1/download"
            f" -c {token}"
            f' -O 48668 -E 58925 -A 58625 -V 58930 -B 10020 -S 60020 -Z 60030 -K 10030 -e "" -a "" -k ""'
            f" -i 0 -I 127.0.0.1 -N SERVER -p /usr/local/gse -T /tmp/ &> /tmp/nm.nohup.out &"
        )
        self.assertEqual(installation_tool.run_cmd, run_cmd)


class InstallWindowsSSHTestCase(InstallBaseTestCase):
    OS_TYPE = constants.OsType.WINDOWS

    def test_gen_win_command(self):
        host = models.Host.objects.get(bk_host_id=self.obj_factory.bk_host_ids[0])
        installation_tool = gen_commands(host, mock_data_utils.JOB_TASK_PIPELINE_ID, is_uninstall=False, sub_inst_id=0)
        token = re.match(r"(.*) -c (.*?) -O", installation_tool.run_cmd).group(2)
        run_cmd = (
            f"nohup C:/tmp/setup_agent.bat -s {mock_data_utils.JOB_TASK_PIPELINE_ID}"
            f" -r http://127.0.0.1/backend -l http://127.0.0.1/download -c {token}"
            f' -O 48668 -E 58925 -A 58625 -V 58930 -B 10020 -S 60020 -Z 60030 -K 10030 -e " " -a " " -k " "'
            f" -i 0 -I 127.0.0.1 -N SERVER -p c:\\\\gse -T C:\\\\tmp\\\\ &> C:/tmp/nm.nohup.out &"
        )
        self.assertEqual(installation_tool.run_cmd, run_cmd)


class InstallWindowsTestCase(InstallBaseTestCase):
    OS_TYPE = constants.OsType.WINDOWS

    def test_gen_win_command(self):
        host = models.Host.objects.get(bk_host_id=self.obj_factory.bk_host_ids[0])
        installation_tool = gen_commands(host, mock_data_utils.JOB_TASK_PIPELINE_ID, is_uninstall=False, sub_inst_id=0)
        token = re.match(r"(.*) -c (.*?) -O", installation_tool.run_cmd).group(2)
        windows_run_cmd = (
            f"C:\\tmp\\setup_agent.bat -s {mock_data_utils.JOB_TASK_PIPELINE_ID}"
            f" -r http://127.0.0.1/backend -l http://127.0.0.1/download -c {token}"
            f' -O 48668 -E 58925 -A 58625 -V 58930 -B 10020 -S 60020 -Z 60030 -K 10030 -e "" -a "" -k ""'
            f" -i 0 -I 127.0.0.1 -N SERVER -p c:\\gse -T C:\\tmp\\"
        )
        self.assertEqual(installation_tool.win_commands[-1], windows_run_cmd)

    def start_patch(self):
        # 让 Windows SSH 检测失败
        class AsyncMockErrorConn(AsyncMockConn):
            async def connect(self):
                raise exceptions.DisconnectError

        mock.patch("apps.backend.components.collections.common.remote.conns.AsyncsshConn", AsyncMockErrorConn).start()
        super().start_patch()


class InstallLinuxPagentTestCase(InstallBaseTestCase):
    NODE_TYPE = constants.NodeType.PAGENT
    CLOUD_ID = 1

    def init_hosts(self):
        self.init_alive_proxies(bk_cloud_id=self.CLOUD_ID)
        models.Host.objects.filter(bk_host_id__in=self.obj_factory.bk_host_ids).update(
            os_type=self.OS_TYPE, node_type=self.NODE_TYPE, bk_cloud_id=self.CLOUD_ID, ap_id=constants.DEFAULT_AP_ID
        )

    def test_gen_pagent_command(self):
        host = models.Host.objects.get(bk_host_id=self.obj_factory.bk_host_ids[0])
        installation_tool = gen_commands(host, mock_data_utils.JOB_TASK_PIPELINE_ID, is_uninstall=False, sub_inst_id=0)
        token = re.match(r"(.*) -c (.*?) -O", installation_tool.run_cmd).group(2)
        run_cmd = (
            f"-s {mock_data_utils.JOB_TASK_PIPELINE_ID} -r http://127.0.0.1/backend -l http://127.0.0.1/download"
            f" -c {token}"
            f" -O 48668 -E 58925 -A 58625 -V 58930 -B 10020 -S 60020 -Z 60030 -K 10030"
            f' -e "1.1.1.1" -a "1.1.1.1" -k "1.1.1.1" -L /data/bkee/public/bknodeman/download'
            f" -HLIP 127.0.0.1 -HIIP 127.0.0.1 -HA root -HP 22 -HI 'password' -HC {self.CLOUD_ID} -HNT PAGENT"
            f" -HOT linux -HDD '/tmp/'"
            f" -HPP '17981' -HSN 'setup_agent.sh' -HS 'bash'"
            f" -p '/usr/local/gse' -I 1.1.1.1"
            f" -o http://1.1.1.1:{settings.BK_NODEMAN_NGINX_DOWNLOAD_PORT}/"
        )
        self.assertEqual(installation_tool.run_cmd, run_cmd)


class InstallFailedTestCase(InstallBaseTestCase):
    def init_redis_data(self):
        # 初始化redis数据，用于schedule时读取解析
        for sub_inst_id in self.common_inputs["subscription_instance_ids"]:
            name = REDIS_INSTALL_CALLBACK_KEY_TPL.format(sub_inst_id=sub_inst_id)
            REDIS_INST.lpush(
                name,
                json.dumps(
                    {
                        "timestamp": "1580870937",
                        "level": "ERROR",
                        "step": "download_pkg",
                        "log": "download failed",
                        "status": "FAILED",
                    }
                ),
            )

    def cases(self):
        self.init_redis_data()
        return [
            ComponentTestCase(
                name="测试安装失败",
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=bool(self.fetch_succeeded_sub_inst_ids()),
                    outputs={
                        "succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids(),
                        "scheduling_sub_inst_ids": self.fetch_succeeded_sub_inst_ids(),
                        "polling_time": 0,
                    },
                ),
                schedule_assertion=ScheduleAssertion(
                    success=False,
                    schedule_finished=True,
                    outputs={
                        "succeeded_subscription_instance_ids": [],
                        "scheduling_sub_inst_ids": [],
                        "polling_time": 0,
                    },
                ),
                execute_call_assertion=None,
                patchers=[],
            )
        ]


class InstallAgentWithInstallChannelSuccessTest(InstallBaseTestCase):
    def init_hosts(self):
        install_channel = self.create_install_channel()
        models.Host.objects.filter(bk_host_id__in=self.obj_factory.bk_host_ids).update(
            os_type=self.OS_TYPE, node_type=self.NODE_TYPE, install_channel_id=install_channel.id
        )

    def test_gen_install_channel_agent_command(self):
        host = models.Host.objects.get(bk_host_id=self.obj_factory.bk_host_ids[0])
        installation_tool = gen_commands(host, mock_data_utils.JOB_TASK_PIPELINE_ID, is_uninstall=False, sub_inst_id=0)
        token = re.match(r"(.*) -c (.*?) -O", installation_tool.run_cmd).group(2)
        run_cmd = (
            f"-s {mock_data_utils.JOB_TASK_PIPELINE_ID} -r http://127.0.0.1/backend"
            f" -l http://1.1.1.1:{settings.BK_NODEMAN_NGINX_DOWNLOAD_PORT}/ -c {token}"
            f" -O 48668 -E 58925 -A 58625 -V 58930 -B 10020 -S 60020 -Z 60030 -K 10030"
            f' -e "127.0.0.1" -a "127.0.0.1" -k "127.0.0.1" -L /data/bkee/public/bknodeman/download'
            f" -HLIP 127.0.0.1 -HIIP 127.0.0.1 -HA root -HP 22 -HI 'password' -HC 0 -HNT AGENT"
            f" -HOT linux -HDD '/tmp/'"
            f" -HPP '17981' -HSN 'setup_agent.sh' -HS 'bash'"
            f" -p '/usr/local/gse' -I 1.1.1.1"
            f" -o http://1.1.1.1:{settings.BK_NODEMAN_NGINX_DOWNLOAD_PORT}/"
            f" -CPA 'http://127.0.0.1:17981'"
        )
        self.assertEqual(installation_tool.run_cmd, run_cmd)


class ManualInstallSuccessTest(InstallBaseTestCase):
    def init_hosts(self):
        models.Host.objects.filter(bk_host_id__in=self.obj_factory.bk_host_ids).update(
            os_type=self.OS_TYPE, node_type=self.NODE_TYPE, is_manual=True
        )
