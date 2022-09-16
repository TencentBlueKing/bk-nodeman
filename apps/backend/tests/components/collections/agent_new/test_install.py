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
import importlib
import json
import os
import re
from typing import Any, Dict, List, Optional

import mock
from django.conf import settings
from django.test import override_settings

from apps.backend.agent.solution_maker import ExecutionSolution
from apps.backend.agent.tools import InstallationTools, gen_commands
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
    CUSTOM_DATAIPC_DIR = "/var/run/gse_test"

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
            report_agent_obj: models.Host = models.Host.objects.get(bk_host_id=self.obj_factory.bk_host_ids[0])
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
                        "step": "report_agent_id",
                        "log": f"{report_agent_obj.bk_cloud_id}:{report_agent_obj.inner_ip}",
                        "status": "DONE",
                    },
                    {
                        "timestamp": "1580870937",
                        "level": "INFO",
                        "step": "report_os_version",
                        "status": "DONE",
                        "log": "6.1.1.1",
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

    def adjust_ap(self):
        ap: models.AccessPoint = models.AccessPoint.objects.first()
        ap.agent_config["linux"]["dataipc"] = os.path.join(self.CUSTOM_DATAIPC_DIR, "ipc.state.report")
        ap.save()

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
        self.adjust_ap()
        super().setUp()
        self.update_common_inputs()
        self.start_patch()

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        return self.common_inputs["subscription_instance_ids"]

    @classmethod
    def execution_solution_parser(
        cls,
        run_cmd_param_extract: Dict[str, str],
        solution_type: Optional[str] = None,
        installation_tool: Optional[InstallationTools] = None,
        execution_solution: Optional[ExecutionSolution] = None,
    ) -> Dict[str, Any]:

        if execution_solution is None:
            execution_solution = installation_tool.type__execution_solution_map[solution_type]

        execution_solution_steps = execution_solution.steps
        parse_result: Dict[str, Any] = {"cmds": [], "dependencies": [], "params": {}}
        for execution_solution_step in execution_solution_steps:
            for content in execution_solution_step.contents:
                if execution_solution_step.type == constants.CommonExecutionSolutionStepType.COMMANDS.value:
                    parse_result["cmds"].append(content.text)
                    if content.name != "run_cmd":
                        continue

                    for param_name, re_str in run_cmd_param_extract.items():
                        try:
                            parse_result["params"][param_name] = re.match(re_str, content.text).group(2)
                        except Exception:
                            pass

                elif execution_solution_step.type == constants.CommonExecutionSolutionStepType.DEPENDENCIES.value:
                    parse_result["dependencies"].append(content.name)
        return parse_result

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
    def test_shell_solution(self):
        host = models.Host.objects.get(bk_host_id=self.obj_factory.bk_host_ids[0])
        installation_tool = gen_commands(host, mock_data_utils.JOB_TASK_PIPELINE_ID, is_uninstall=False, sub_inst_id=0)
        solution_parse_result: Dict[str, Any] = self.execution_solution_parser(
            installation_tool=installation_tool,
            solution_type=constants.CommonExecutionSolutionType.SHELL.value,
            run_cmd_param_extract={"token": r"(.*) -c (.*?) -s"},
        )

        self.assertEqual(solution_parse_result["dependencies"], [])
        self.assertEqual(
            solution_parse_result["cmds"],
            [
                f"mkdir -p {installation_tool.dest_dir}",
                f"mkdir -p {self.CUSTOM_DATAIPC_DIR}",
                f"curl http://127.0.0.1/download/setup_agent.sh "
                f"-o {installation_tool.dest_dir}setup_agent.sh --connect-timeout 5 -sSf",
                f"chmod +x {installation_tool.dest_dir}setup_agent.sh",
                f"nohup bash {installation_tool.dest_dir}setup_agent.sh"
                f' -O 48668 -E 58925 -A 58625 -V 58930 -B 10020 -S 60020 -Z 60030 -K 10030 -e "" -a "" -k ""'
                f" -l http://127.0.0.1/download -r http://127.0.0.1/backend"
                f" -i 0 -I {host.inner_ip} -T {installation_tool.dest_dir} -p /usr/local/gse"
                f" -c {solution_parse_result['params']['token']} -s {mock_data_utils.JOB_TASK_PIPELINE_ID}"
                f" -N SERVER &> /tmp/nm.nohup.out &",
            ],
        )


class InstallWindowsSSHTestCase(InstallBaseTestCase):
    OS_TYPE = constants.OsType.WINDOWS

    def _test_shell_solution(self, validate_encrypted_password: bool):

        host = models.Host.objects.get(bk_host_id=self.obj_factory.bk_host_ids[0])
        installation_tool = gen_commands(host, mock_data_utils.JOB_TASK_PIPELINE_ID, is_uninstall=False, sub_inst_id=0)

        run_cmd_param_extract = {"token": r"(.*) -c (.*?) -s"}
        if validate_encrypted_password:
            run_cmd_param_extract["encrypted_password"] = r"(.*) -P (.*?) -N"

        solution_parse_result: Dict[str, Any] = self.execution_solution_parser(
            installation_tool=installation_tool,
            solution_type=constants.CommonExecutionSolutionType.SHELL.value,
            run_cmd_param_extract=run_cmd_param_extract,
        )

        if validate_encrypted_password:
            # 校验是否存在 Cygwin 所需的占位符
            self.assertTrue(solution_parse_result["params"]["encrypted_password"].endswith(' "'))
            encrypted_password_params = f" -U root -P {solution_parse_result['params']['encrypted_password']}"
        else:
            encrypted_password_params = ""

        installation_tool.dest_dir = installation_tool.dest_dir.replace("\\", "/")

        run_cmd = (
            f"nohup {installation_tool.dest_dir}setup_agent.bat"
            f' -O 48668 -E 58925 -A 58625 -V 58930 -B 10020 -S 60020 -Z 60030 -K 10030 -e " " -a " " -k " "'
            f" -l http://127.0.0.1/download -r http://127.0.0.1/backend"
            f" -i 0 -I {host.inner_ip} -T C:\\\\tmp\\\\ -p c:\\\\gse"
            f" -c {solution_parse_result['params']['token']}"
            f" -s {mock_data_utils.JOB_TASK_PIPELINE_ID}{encrypted_password_params}"
            f" -N SERVER &> {installation_tool.dest_dir}nm.nohup.out &"
        )

        self.assertEqual(
            solution_parse_result["cmds"],
            [f"mkdir -p {installation_tool.dest_dir}"]
            + [
                f"curl {installation_tool.package_url}/{dependence} "
                f"-o {installation_tool.dest_dir}{dependence} --connect-timeout 5 -sSf"
                for dependence in constants.AgentWindowsDependencies.list_member_values()
            ]
            + [
                f"{installation_tool.dest_dir}curl.exe http://127.0.0.1/download/setup_agent.bat "
                f"-o {installation_tool.dest_dir}setup_agent.bat --connect-timeout 5 -sSf",
                f"chmod +x {installation_tool.dest_dir}setup_agent.bat",
                run_cmd,
            ],
        )

    def test_shell_solution(self):
        self._test_shell_solution(validate_encrypted_password=False)

    @override_settings(REGISTER_WIN_SERVICE_WITH_PASS=True)
    def test_shell_solution__register_win(self):
        self._test_shell_solution(validate_encrypted_password=True)


class InstallWindowsTestCase(InstallBaseTestCase):
    OS_TYPE = constants.OsType.WINDOWS

    def test_batch_solution(self):
        host = models.Host.objects.get(bk_host_id=self.obj_factory.bk_host_ids[0])
        installation_tool = gen_commands(host, mock_data_utils.JOB_TASK_PIPELINE_ID, is_uninstall=False, sub_inst_id=0)
        solution_parse_result: Dict[str, Any] = self.execution_solution_parser(
            installation_tool=installation_tool,
            solution_type=constants.CommonExecutionSolutionType.BATCH.value,
            run_cmd_param_extract={"token": r"(.*) -c (.*?) -s"},
        )

        self.assertEqual(constants.AgentWindowsDependencies.list_member_values(), solution_parse_result["dependencies"])
        self.assertEqual(
            solution_parse_result["cmds"],
            [
                f"mkdir {installation_tool.dest_dir}",
                f"{installation_tool.dest_dir}curl.exe http://127.0.0.1/download/setup_agent.bat"
                f" -o {installation_tool.dest_dir}setup_agent.bat -sSf",
                f"{installation_tool.dest_dir}setup_agent.bat"
                f' -O 48668 -E 58925 -A 58625 -V 58930 -B 10020 -S 60020 -Z 60030 -K 10030 -e "" -a "" -k ""'
                f" -l http://127.0.0.1/download -r http://127.0.0.1/backend"
                f" -i 0 -I {host.inner_ip} -T C:\\tmp\\ -p c:\\gse"
                f" -c {solution_parse_result['params']['token']} -s {mock_data_utils.JOB_TASK_PIPELINE_ID} -N SERVER",
            ],
        )

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

    def test_shell_solution(self):
        host = models.Host.objects.get(bk_host_id=self.obj_factory.bk_host_ids[0])
        installation_tool = gen_commands(host, mock_data_utils.JOB_TASK_PIPELINE_ID, is_uninstall=False, sub_inst_id=0)
        solution_parse_result: Dict[str, Any] = self.execution_solution_parser(
            installation_tool=installation_tool,
            solution_type=constants.CommonExecutionSolutionType.SHELL.value,
            run_cmd_param_extract={"token": r"(.*) -c (.*?) -s", "host_solutions_json_b64": r"(.*) -HSJB (.*)"},
        )

        self.assertTrue(
            type(
                json.loads(
                    base64.b64decode(solution_parse_result["params"]["host_solutions_json_b64"].encode()).decode()
                )
            ),
            list,
        )

        self.assertEqual(
            solution_parse_result["cmds"],
            [
                f"-l http://127.0.0.1/download -r http://127.0.0.1/backend -L /data/bkee/public/bknodeman/download"
                f" -c {solution_parse_result['params']['token']} -s {mock_data_utils.JOB_TASK_PIPELINE_ID}"
                f" -HNT PAGENT -HIIP {host.inner_ip}"
                f" -HC {self.CLOUD_ID} -HOT {host.os_type.lower()} -HI '{host.identity.password}'"
                f" -HP {host.identity.port} -HA {host.identity.account} -HLIP {host.inner_ip}"
                f" -HDD '{installation_tool.dest_dir}' -HPP '17981' -I 1.1.1.1"
                f" -HSJB {solution_parse_result['params']['host_solutions_json_b64']}"
            ],
        )

    def test_target_host_shell_solution(self):
        host = models.Host.objects.get(bk_host_id=self.obj_factory.bk_host_ids[0])
        installation_tool = gen_commands(host, mock_data_utils.JOB_TASK_PIPELINE_ID, is_uninstall=False, sub_inst_id=0)
        target_host_solutions = installation_tool.type__execution_solution_map[
            constants.CommonExecutionSolutionType.SHELL.value
        ].target_host_solutions
        # Linux 主机只有 shell 一种执行方案
        self.assertEqual(len(target_host_solutions), 1)

        solution_parse_result: Dict[str, Any] = self.execution_solution_parser(
            execution_solution=target_host_solutions[0], run_cmd_param_extract={"token": r"(.*) -c (.*?) -s"}
        )

        self.assertEqual(solution_parse_result["dependencies"], [])
        self.assertEqual(
            solution_parse_result["cmds"],
            [
                f"mkdir -p {installation_tool.dest_dir}",
                f"mkdir -p {self.CUSTOM_DATAIPC_DIR}",
                f"curl http://127.0.0.1/download/setup_agent.sh "
                f"-o {installation_tool.dest_dir}setup_agent.sh --connect-timeout 5 -sSf"
                f" -x http://1.1.1.1:{settings.BK_NODEMAN_NGINX_PROXY_PASS_PORT}",
                f"chmod +x {installation_tool.dest_dir}setup_agent.sh",
                f"nohup bash {installation_tool.dest_dir}setup_agent.sh"
                f" -O 48668 -E 58925 -A 58625 -V 58930 -B 10020 -S 60020 -Z 60030 -K 10030"
                f' -e "1.1.1.1" -a "1.1.1.1" -k "1.1.1.1"'
                f" -l http://1.1.1.1:{settings.BK_NODEMAN_NGINX_DOWNLOAD_PORT} -r http://127.0.0.1/backend"
                f" -i {host.bk_cloud_id} -I {host.inner_ip} -T {installation_tool.dest_dir} -p /usr/local/gse"
                f" -c {solution_parse_result['params']['token']} -s {mock_data_utils.JOB_TASK_PIPELINE_ID}"
                f" -N PROXY -x http://1.1.1.1:{settings.BK_NODEMAN_NGINX_PROXY_PASS_PORT} &> /tmp/nm.nohup.out &",
            ],
        )


class InstallWindowsPagentTestCase(InstallLinuxPagentTestCase):
    OS_TYPE = constants.OsType.WINDOWS

    def test_target_host_shell_solution(self):
        host = models.Host.objects.get(bk_host_id=self.obj_factory.bk_host_ids[0])
        installation_tool = gen_commands(host, mock_data_utils.JOB_TASK_PIPELINE_ID, is_uninstall=False, sub_inst_id=0)
        target_host_solutions = installation_tool.type__execution_solution_map[
            constants.CommonExecutionSolutionType.SHELL.value
        ].target_host_solutions
        type__execution_solution_map = {
            target_host_solution.type: target_host_solution for target_host_solution in target_host_solutions
        }
        solution_parse_result: Dict[str, Any] = self.execution_solution_parser(
            execution_solution=type__execution_solution_map[constants.CommonExecutionSolutionType.SHELL.value],
            run_cmd_param_extract={"token": r"(.*) -c (.*?) -s"},
        )

        installation_tool.dest_dir = installation_tool.dest_dir.replace("\\", "/")

        self.assertEqual(solution_parse_result["dependencies"], [])

        run_cmd = (
            f"nohup {installation_tool.dest_dir}setup_agent.bat"
            f" -O 48668 -E 58925 -A 58625 -V 58930 -B 10020 -S 60020 -Z 60030 -K 10030"
            f' -e "1.1.1.1 " -a "1.1.1.1 " -k "1.1.1.1 "'
            f" -l http://1.1.1.1:{settings.BK_NODEMAN_NGINX_DOWNLOAD_PORT} -r http://127.0.0.1/backend"
            f" -i {host.bk_cloud_id} -I {host.inner_ip} -T C:\\\\tmp\\\\ -p c:\\\\gse"
            f" -c {solution_parse_result['params']['token']}"
            f" -s {mock_data_utils.JOB_TASK_PIPELINE_ID}"
            f" -N PROXY -x http://1.1.1.1:{settings.BK_NODEMAN_NGINX_PROXY_PASS_PORT}"
            f" &> {installation_tool.dest_dir}nm.nohup.out &"
        )

        self.assertEqual(
            solution_parse_result["cmds"],
            [f"mkdir -p {installation_tool.dest_dir}"]
            + [
                f"curl {installation_tool.package_url}/{dependence} -o {installation_tool.dest_dir}{dependence} "
                f"--connect-timeout 5 -sSf -x http://1.1.1.1:{settings.BK_NODEMAN_NGINX_PROXY_PASS_PORT}"
                for dependence in constants.AgentWindowsDependencies.list_member_values()
            ]
            + [
                f"{installation_tool.dest_dir}curl.exe http://127.0.0.1/download/setup_agent.bat"
                f" -o {installation_tool.dest_dir}setup_agent.bat --connect-timeout 5 -sSf"
                f" -x http://1.1.1.1:{settings.BK_NODEMAN_NGINX_PROXY_PASS_PORT}",
                f"chmod +x {installation_tool.dest_dir}setup_agent.bat",
                run_cmd,
            ],
        )

    def test_target_host_batch_solution(self):
        host = models.Host.objects.get(bk_host_id=self.obj_factory.bk_host_ids[0])
        installation_tool = gen_commands(host, mock_data_utils.JOB_TASK_PIPELINE_ID, is_uninstall=False, sub_inst_id=0)
        target_host_solutions = installation_tool.type__execution_solution_map[
            constants.CommonExecutionSolutionType.SHELL.value
        ].target_host_solutions
        type__execution_solution_map = {
            target_host_solution.type: target_host_solution for target_host_solution in target_host_solutions
        }
        solution_parse_result: Dict[str, Any] = self.execution_solution_parser(
            execution_solution=type__execution_solution_map[constants.CommonExecutionSolutionType.BATCH.value],
            run_cmd_param_extract={"token": r"(.*) -c (.*?) -s"},
        )

        self.assertEqual(constants.AgentWindowsDependencies.list_member_values(), solution_parse_result["dependencies"])
        self.assertEqual(
            solution_parse_result["cmds"],
            [
                f"mkdir {installation_tool.dest_dir}",
                f"{installation_tool.dest_dir}curl.exe http://127.0.0.1/download/setup_agent.bat"
                f" -o {installation_tool.dest_dir}setup_agent.bat -sSf"
                f" -x http://1.1.1.1:{settings.BK_NODEMAN_NGINX_PROXY_PASS_PORT}",
                f"{installation_tool.dest_dir}setup_agent.bat"
                f" -O 48668 -E 58925 -A 58625 -V 58930 -B 10020 -S 60020 -Z 60030 -K 10030"
                f' -e "1.1.1.1" -a "1.1.1.1" -k "1.1.1.1"'
                f" -l http://1.1.1.1:{settings.BK_NODEMAN_NGINX_DOWNLOAD_PORT} -r http://127.0.0.1/backend"
                f" -i {host.bk_cloud_id} -I {host.inner_ip} -T C:\\tmp\\ -p c:\\gse"
                f" -c {solution_parse_result['params']['token']} -s {mock_data_utils.JOB_TASK_PIPELINE_ID}"
                f" -N PROXY -x http://1.1.1.1:{settings.BK_NODEMAN_NGINX_PROXY_PASS_PORT}",
            ],
        )


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

        solution_parse_result: Dict[str, Any] = self.execution_solution_parser(
            installation_tool=installation_tool,
            solution_type=constants.CommonExecutionSolutionType.SHELL.value,
            run_cmd_param_extract={"token": r"(.*) -c (.*?) -s", "host_solutions_json_b64": r"(.*) -HSJB (.*)"},
        )

        self.assertEqual(
            solution_parse_result["cmds"],
            [
                f"-l http://1.1.1.1:17980/ -r http://127.0.0.1/backend -L /data/bkee/public/bknodeman/download"
                f" -c {solution_parse_result['params']['token']} -s {mock_data_utils.JOB_TASK_PIPELINE_ID}"
                f" -HNT AGENT -HIIP {host.inner_ip}"
                f" -HC 0 -HOT linux -HI 'password' -HP 22 -HA root -HLIP {host.inner_ip}"
                f" -HDD '/tmp/' -HPP '17981' -I 1.1.1.1 -CPA 'http://127.0.0.1:17981'"
                f" -HSJB {solution_parse_result['params']['host_solutions_json_b64']}"
            ],
        )


class ManualInstallSuccessTest(InstallBaseTestCase):
    def init_hosts(self):
        models.Host.objects.filter(bk_host_id__in=self.obj_factory.bk_host_ids).update(
            os_type=self.OS_TYPE, node_type=self.NODE_TYPE, is_manual=True
        )


class UninstallSuccessTest(InstallBaseTestCase):
    def structure_common_inputs(self) -> Dict[str, Any]:
        common_inputs = super().structure_common_inputs()
        common_inputs["is_uninstall"] = True
        return common_inputs

    def test_shell_solution(self):
        host = models.Host.objects.get(bk_host_id=self.obj_factory.bk_host_ids[0])
        # 验证非 root 添加 sudo
        host.identity.account = "test"

        installation_tool = gen_commands(host, mock_data_utils.JOB_TASK_PIPELINE_ID, is_uninstall=True, sub_inst_id=0)
        solution_parse_result: Dict[str, Any] = self.execution_solution_parser(
            installation_tool=installation_tool,
            solution_type=constants.CommonExecutionSolutionType.SHELL.value,
            run_cmd_param_extract={"token": r"(.*) -c (.*?) -s"},
        )

        self.assertEqual(solution_parse_result["dependencies"], [])
        self.assertEqual(
            solution_parse_result["cmds"],
            [
                f"sudo mkdir -p {installation_tool.dest_dir}",
                f"sudo mkdir -p {self.CUSTOM_DATAIPC_DIR}",
                f"sudo curl http://127.0.0.1/download/setup_agent.sh "
                f"-o {installation_tool.dest_dir}setup_agent.sh --connect-timeout 5 -sSf",
                f"sudo chmod +x {installation_tool.dest_dir}setup_agent.sh",
                f"sudo nohup bash {installation_tool.dest_dir}setup_agent.sh"
                f' -O 48668 -E 58925 -A 58625 -V 58930 -B 10020 -S 60020 -Z 60030 -K 10030 -e "" -a "" -k ""'
                f" -l http://127.0.0.1/download -r http://127.0.0.1/backend"
                f" -i 0 -I {host.inner_ip} -T {installation_tool.dest_dir} -p /usr/local/gse"
                f" -c {solution_parse_result['params']['token']} -s {mock_data_utils.JOB_TASK_PIPELINE_ID}"
                f" -N SERVER -R &> /tmp/nm.nohup.out &",
            ],
        )
