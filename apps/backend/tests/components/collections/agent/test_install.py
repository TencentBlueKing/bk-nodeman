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
import re
import time

from django.conf import settings
from django.test import TestCase, override_settings
from mock import patch

from apps.backend.agent.tools import gen_commands
from apps.backend.api.constants import JobDataStatus, JobIPStatus
from apps.backend.components.collections.agent import InstallComponent, InstallService
from apps.backend.tests.components.collections.agent import utils
from apps.node_man import constants, models
from pipeline.component_framework.test import (
    ComponentTestCase,
    ComponentTestMixin,
    ExecuteAssertion,
    Patcher,
    ScheduleAssertion,
)

DESCRIPTION = "下发脚本命令"

COMMON_INPUTS = utils.AgentTestObjFactory.inputs(
    attr_values={"description": DESCRIPTION, "bk_host_id": utils.BK_HOST_ID},
    # 主机信息保持和默认一致
    instance_info_attr_values={},
)

COMMON_INPUTS.update({"is_uninstall": False, "bk_username": utils.DEFAULT_CREATOR})


class InstallTestService(InstallService):
    id = utils.JOB_TASK_PIPELINE_ID
    root_pipeline_id = utils.INSTANCE_RECORD_ROOT_PIPELINE_ID


class InstallTestComponent(InstallComponent):
    bound_service = InstallTestService


class InstallLinuxAgentSuccessTest(TestCase, ComponentTestMixin):
    SSH_MOCK_CLIENT = utils.SshManMockClient(ssh_return="close")

    def setUp(self):
        utils.AgentTestObjFactory.init_db()
        # 设置，默认接入点
        default_ap = models.AccessPoint.objects.get(name="默认接入点")
        models.Host.objects.filter(bk_host_id=utils.BK_HOST_ID).update(ap_id=default_ap.id)

    def component_cls(self):
        return InstallTestComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试下发Linux机器命令成功",
                inputs=COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(success=True, outputs={}),
                schedule_assertion=ScheduleAssertion(
                    success=True, schedule_finished=True, outputs={}, callback_data=[]
                ),
                execute_call_assertion=None,
                patchers=[Patcher(target=utils.SSH_MAN_MOCK_PATH, return_value=self.SSH_MOCK_CLIENT)],
            )
        ]

    def test_gen_agent_command(self):
        host = models.Host.objects.get(bk_host_id=utils.BK_HOST_ID)
        installation_tool = gen_commands(host, utils.JOB_TASK_PIPELINE_ID, is_uninstall=False)
        token = re.match(r"(.*) -c (.*?) -O", installation_tool.run_cmd).group(2)
        run_cmd = (
            f"nohup bash /tmp/setup_agent.sh -s {utils.JOB_TASK_PIPELINE_ID}"
            f" -r http://127.0.0.1/backend -l http://127.0.0.1/download"
            f" -c {token}"
            f' -O 48668 -E 58925 -A 58625 -V 58930 -B 10020 -S 60020 -Z 60030 -K 10030 -e "" -a "" -k ""'
            f" -i 0 -I 127.0.0.1 -N SERVER -p /usr/local/gse -T /tmp/ &"
        )
        self.assertEqual(installation_tool.run_cmd, run_cmd)

    def tearDown(self):
        if self._testMethodName == "test_gen_agent_command":
            return

        # 状态检查
        self.assertTrue(
            models.JobTask.objects.filter(bk_host_id=utils.BK_HOST_ID, current_step__endswith=DESCRIPTION).exists()
        )


class InstallWindowsAgentSuccessTest(TestCase, ComponentTestMixin):
    EXECUTE_CMD_MOCK_PATH = "apps.backend.components.collections.agent.execute_cmd"
    PUT_FILE_MACK_PATH = "apps.backend.components.collections.agent.put_file"

    def setUp(self):
        utils.AgentTestObjFactory.init_db()
        # 设置默认接入点及操作系统
        default_ap = models.AccessPoint.objects.get(name="默认接入点")
        models.Host.objects.filter(bk_host_id=utils.BK_HOST_ID).update(
            ap_id=default_ap.id, os_type=constants.OsType.WINDOWS
        )

    def component_cls(self):
        return InstallTestComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试下发Windows机器命令成功",
                inputs=COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(success=True, outputs={}),
                schedule_assertion=ScheduleAssertion(
                    success=True, schedule_finished=True, outputs={}, callback_data=[]
                ),
                execute_call_assertion=None,
                patchers=[
                    Patcher(target=self.EXECUTE_CMD_MOCK_PATH, return_value=None),
                    Patcher(target=self.PUT_FILE_MACK_PATH, return_value=None),
                ],
            )
        ]

    def test_gen_win_command(self):
        host = models.Host.objects.get(bk_host_id=utils.BK_HOST_ID)
        installation_tool = gen_commands(host, utils.JOB_TASK_PIPELINE_ID, is_uninstall=False)
        token = re.match(r"(.*) -c (.*?) -O", installation_tool.run_cmd).group(2)
        run_cmd = (
            f"C:\\tmp\\setup_agent.bat -s {utils.JOB_TASK_PIPELINE_ID}"
            f" -r http://127.0.0.1/backend -l http://127.0.0.1/download -c {token}"
            f' -O 48668 -E 58925 -A 58625 -V 58930 -B 10020 -S 60020 -Z 60030 -K 10030 -e "" -a "" -k ""'
            f" -i 0 -I 127.0.0.1 -N SERVER -p c:\\gse -T C:\\tmp\\"
        )
        self.assertEqual(installation_tool.run_cmd, run_cmd)

    def tearDown(self):
        if self._testMethodName == "test_gen_win_command":
            return
        # 状态检查
        self.assertTrue(
            models.JobTask.objects.filter(bk_host_id=utils.BK_HOST_ID, current_step__endswith=DESCRIPTION).exists()
        )


@override_settings(REGISTER_WIN_SERVICE_WITH_PASS=True)
class InstallWindowsAgentWithEncryptedPasswordSuccessTest(InstallWindowsAgentSuccessTest):
    def setUp(self):
        super().setUp()

    def test_gen_win_command(self):
        host = models.Host.objects.get(bk_host_id=utils.BK_HOST_ID)
        installation_tool = gen_commands(host, utils.JOB_TASK_PIPELINE_ID, is_uninstall=False)
        token = re.match(r"(.*) -c (.*?) -O", installation_tool.run_cmd).group(2)
        run_cmd = (
            f"C:\\tmp\\setup_agent.bat -s {utils.JOB_TASK_PIPELINE_ID}"
            f" -r http://127.0.0.1/backend -l http://127.0.0.1/download -c {token}"
            f' -O 48668 -E 58925 -A 58625 -V 58930 -B 10020 -S 60020 -Z 60030 -K 10030 -e "" -a "" -k ""'
            f" -i 0 -I 127.0.0.1 -N SERVER -p c:\\gse -T C:\\tmp\\ -U root -P "
        )
        # RSA每次加密的结果都不一样，因此只要保证startswith即可
        self.assertTrue(installation_tool.run_cmd.startswith(run_cmd))


class InstallWindowsPasswordAuthOverdueTest(TestCase, ComponentTestMixin):
    EXECUTE_CMD_MOCK_PATH = "apps.backend.components.collections.agent.execute_cmd"
    PUT_FILE_MACK_PATH = "apps.backend.components.collections.agent.put_file"

    def setUp(self):
        utils.AgentTestObjFactory.init_db()
        # 设置默认接入点及操作系统
        default_ap = models.AccessPoint.objects.get(name="默认接入点")
        models.Host.objects.filter(bk_host_id=utils.BK_HOST_ID).update(
            ap_id=default_ap.id, os_type=constants.OsType.WINDOWS
        )
        # 密码置空
        models.IdentityData.objects.filter(bk_host_id=utils.BK_HOST_ID).update(
            auth_type=constants.AuthType.PASSWORD, password=""
        )

    def component_cls(self):
        return InstallTestComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试下发Windows机器命令失败：AuthType.PASSWORD认证信息已过期",
                inputs=COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(success=False, outputs={}),
                schedule_assertion=None,
                execute_call_assertion=None,
                patchers=[
                    Patcher(target=self.EXECUTE_CMD_MOCK_PATH, return_value=None),
                    Patcher(target=self.PUT_FILE_MACK_PATH, return_value=None),
                ],
            )
        ]

    def tearDown(self):
        # 状态检查
        self.assertTrue(
            models.JobTask.objects.filter(bk_host_id=utils.BK_HOST_ID, current_step__endswith=DESCRIPTION).exists()
        )


class InstallWindowsKeyAuthOverdueTest(TestCase, ComponentTestMixin):
    EXECUTE_CMD_MOCK_PATH = "apps.backend.components.collections.agent.execute_cmd"
    PUT_FILE_MACK_PATH = "apps.backend.components.collections.agent.put_file"

    def setUp(self):
        utils.AgentTestObjFactory.init_db()
        # 设置默认接入点及操作系统
        default_ap = models.AccessPoint.objects.get(name="默认接入点")
        models.Host.objects.filter(bk_host_id=utils.BK_HOST_ID).update(
            ap_id=default_ap.id, os_type=constants.OsType.WINDOWS
        )
        # KEY置空
        models.IdentityData.objects.filter(bk_host_id=utils.BK_HOST_ID).update(auth_type=constants.AuthType.KEY, key="")

    def component_cls(self):
        return InstallTestComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试下发Windows机器命令失败：AuthType.KEY认证信息已过期",
                inputs=COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(success=False, outputs={}),
                schedule_assertion=None,
                execute_call_assertion=None,
                patchers=[
                    Patcher(target=self.EXECUTE_CMD_MOCK_PATH, return_value=None),
                    Patcher(target=self.PUT_FILE_MACK_PATH, return_value=None),
                ],
            )
        ]

    def tearDown(self):
        # 状态检查
        self.assertTrue(
            models.JobTask.objects.filter(bk_host_id=utils.BK_HOST_ID, current_step__endswith=DESCRIPTION).exists()
        )


JOB_CLIENT_V2_PATH = "apps.backend.components.collections.agent.client_v2"

FAST_EXECUTE_SCRIPT_RETURN = {"job_instance_name": "API Quick execution script1521100521303", "job_instance_id": 10000}


class InstallPAgentSuccessTest(TestCase, ComponentTestMixin):
    GET_JOB_INSTANCE_LOG_RETURN = [
        {
            "status": JobDataStatus.SUCCESS,
            "step_results": [
                {"tag": "", "ip_logs": [{"ip": "1.1.1.1", "log_content": "success"}], "ip_status": JobIPStatus.SUCCESS}
            ],
        },
    ]

    JOB_MOCK_CLIENT = utils.JobMockClient(
        fast_execute_script_return=FAST_EXECUTE_SCRIPT_RETURN, get_job_instance_log_return=GET_JOB_INSTANCE_LOG_RETURN
    )

    def setUp(self):
        utils.AgentTestObjFactory.init_db()
        # 设置默认接入点及操作系统
        default_ap = models.AccessPoint.objects.get(name="默认接入点")
        models.Host.objects.filter(bk_host_id=utils.BK_HOST_ID).update(
            ap_id=default_ap.id, node_type=constants.NodeType.PAGENT
        )
        # 创建可用Proxy
        models.Host.objects.create(
            **utils.AgentTestObjFactory.host_obj(
                {
                    "node_type": constants.NodeType.PROXY,
                    "bk_host_id": 23535,
                    "inner_ip": "1.1.1.1",
                    "login_ip": "1.1.1.1",
                }
            )
        )
        models.ProcessStatus.objects.create(
            bk_host_id=23535, name=models.ProcessStatus.GSE_AGENT_PROCESS_NAME, status=constants.ProcStateType.RUNNING
        )

        patch(JOB_CLIENT_V2_PATH, self.JOB_MOCK_CLIENT).start()
        self.job_client_v2 = patch(JOB_CLIENT_V2_PATH, self.JOB_MOCK_CLIENT)
        self.job_client_v2.start()

    def component_cls(self):
        return InstallTestComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试PAgent下发安装命令成功",
                inputs=COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(success=True, outputs={}),
                schedule_assertion=ScheduleAssertion(
                    success=True,
                    schedule_finished=True,
                    outputs={},
                    callback_data=[
                        {
                            "timestamp": time.time(),
                            "level": "INFO",
                            "step": "wait_for_job",
                            "log": "waiting job result",
                            "status": "-",
                            "job_status_kwargs": {
                                "bk_biz_id": utils.DEFAULT_BIZ_ID_NAME["bk_biz_id"],
                                "job_instance_id": 10000,
                            },
                            "prefix": "job",
                        }
                    ],
                ),
                execute_call_assertion=None,
                patchers=[
                    Patcher(
                        target="apps.backend.components.collections.agent.task_service.callback.apply_async",
                        return_value=True,
                    )
                ],
            )
        ]

    def test_gen_pagent_command(self):
        host = models.Host.objects.get(bk_host_id=utils.BK_HOST_ID)
        installation_tool = gen_commands(host, utils.JOB_TASK_PIPELINE_ID, is_uninstall=False)
        token = re.match(r"(.*) -c (.*?) -O", installation_tool.run_cmd).group(2)
        run_cmd = (
            f"-s {utils.JOB_TASK_PIPELINE_ID} -r http://127.0.0.1/backend -l http://127.0.0.1/download"
            f" -c {token}"
            f" -O 48668 -E 58925 -A 58625 -V 58930 -B 10020 -S 60020 -Z 60030 -K 10030"
            f' -e "1.1.1.1" -a "1.1.1.1" -k "1.1.1.1" -L /data/bkee/public/bknodeman/download'
            f" -HLIP 127.0.0.1 -HIIP 127.0.0.1 -HA root -HP 22 -HI 'aes_str:::H4MFaqax' -HC 0 -HNT PAGENT"
            f" -HOT linux -HDD '/tmp/'"
            f" -HPP '17981' -HSN 'setup_agent.sh' -HS 'bash'"
            f" -p '/usr/local/gse' -I 1.1.1.1"
            f" -o http://1.1.1.1:{settings.BK_NODEMAN_NGINX_DOWNLOAD_PORT}/"
        )
        self.assertEqual(installation_tool.run_cmd, run_cmd)

    def tearDown(self):
        if self._testMethodName == "test_gen_pagent_command":
            return
        # 状态检查
        self.assertTrue(
            models.JobTask.objects.filter(bk_host_id=utils.BK_HOST_ID, current_step__endswith=DESCRIPTION).exists()
        )
        self.job_client_v2.stop()


class InstallPAgentFailTest(TestCase, ComponentTestMixin):
    GET_JOB_INSTANCE_LOG_RETURN = [
        {
            "status": JobDataStatus.FAILED,
            "step_results": [
                {"tag": "", "ip_logs": [{"ip": "1.1.1.1", "log_content": "success"}], "ip_status": JobIPStatus.FAILED}
            ],
        },
    ]

    JOB_MOCK_CLIENT = utils.JobMockClient(
        fast_execute_script_return=FAST_EXECUTE_SCRIPT_RETURN, get_job_instance_log_return=GET_JOB_INSTANCE_LOG_RETURN
    )

    def setUp(self):
        utils.AgentTestObjFactory.init_db()
        # 设置默认接入点及操作系统
        default_ap = models.AccessPoint.objects.get(name="默认接入点")
        models.Host.objects.filter(bk_host_id=utils.BK_HOST_ID).update(
            ap_id=default_ap.id, node_type=constants.NodeType.PAGENT
        )
        # 创建可用Proxy
        models.Host.objects.create(
            **utils.AgentTestObjFactory.host_obj(
                {
                    "node_type": constants.NodeType.PROXY,
                    "bk_host_id": 23535,
                    "inner_ip": "1.1.1.1",
                    "login_ip": "1.1.1.1",
                }
            )
        )
        models.ProcessStatus.objects.create(
            bk_host_id=23535, name=models.ProcessStatus.GSE_AGENT_PROCESS_NAME, status=constants.ProcStateType.RUNNING
        )

        patch(JOB_CLIENT_V2_PATH, self.JOB_MOCK_CLIENT).start()

    def component_cls(self):
        return InstallTestComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试PAgent下发安装命令失败",
                inputs=COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(success=True, outputs={}),
                schedule_assertion=ScheduleAssertion(
                    success=False,
                    schedule_finished=True,
                    outputs={},
                    callback_data=[
                        {
                            "timestamp": time.time(),
                            "level": "INFO",
                            "step": "wait_for_job",
                            "log": "waiting job result",
                            "status": "-",
                            "job_status_kwargs": {
                                "bk_biz_id": utils.DEFAULT_BIZ_ID_NAME["bk_biz_id"],
                                "job_instance_id": 10000,
                            },
                            "prefix": "job",
                        }
                    ],
                ),
                execute_call_assertion=None,
                patchers=[
                    Patcher(
                        target="apps.backend.components.collections.agent.task_service.callback.apply_async",
                        return_value=True,
                    )
                ],
            )
        ]

    def tearDown(self):
        # 状态检查
        self.assertTrue(
            models.JobTask.objects.filter(bk_host_id=utils.BK_HOST_ID, current_step__endswith=DESCRIPTION).exists()
        )


class InstallAgentWithInstallChannelSuccessTest(TestCase, ComponentTestMixin):
    GET_JOB_INSTANCE_LOG_RETURN = [
        {
            "status": JobDataStatus.SUCCESS,
            "step_results": [
                {"tag": "", "ip_logs": [{"ip": "1.1.1.1", "log_content": "success"}], "ip_status": JobIPStatus.SUCCESS}
            ],
        },
    ]

    JOB_MOCK_CLIENT = utils.JobMockClient(
        fast_execute_script_return=FAST_EXECUTE_SCRIPT_RETURN, get_job_instance_log_return=GET_JOB_INSTANCE_LOG_RETURN
    )

    def setUp(self):
        utils.AgentTestObjFactory.init_db()
        # 设置默安装通道
        install_channel = models.InstallChannel.objects.create(
            bk_cloud_id=constants.DEFAULT_CLOUD,
            jump_servers=["1.1.1.1"],
            upstream_servers={
                "taskserver": ["127.0.0.1"],
                "btfileserver": ["127.0.0.1"],
                "dataserver": ["127.0.0.1"],
                "channel_proxy_address": "http://127.0.0.1:17981",
                "agent_download_proxy": False,
            },
        )
        models.Host.objects.filter(bk_host_id=utils.BK_HOST_ID).update(install_channel_id=install_channel.id)
        # 创建可用安装通道节点
        jump_server_host_id = 23535
        models.Host.objects.create(
            **utils.AgentTestObjFactory.host_obj(
                {
                    "node_type": constants.NodeType.AGENT,
                    "bk_host_id": jump_server_host_id,
                    "inner_ip": "1.1.1.1",
                    "login_ip": "1.1.1.1",
                }
            )
        )
        models.ProcessStatus.objects.create(
            bk_host_id=jump_server_host_id,
            name=models.ProcessStatus.GSE_AGENT_PROCESS_NAME,
            status=constants.ProcStateType.RUNNING,
        )

        patch(JOB_CLIENT_V2_PATH, self.JOB_MOCK_CLIENT).start()
        self.job_client_v2 = patch(JOB_CLIENT_V2_PATH, self.JOB_MOCK_CLIENT)
        self.job_client_v2.start()

    def component_cls(self):
        return InstallTestComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="测试安装通道Agent下发安装命令成功",
                inputs=COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(success=True, outputs={}),
                schedule_assertion=ScheduleAssertion(
                    success=True,
                    schedule_finished=True,
                    outputs={},
                    callback_data=[
                        {
                            "timestamp": time.time(),
                            "level": "INFO",
                            "step": "wait_for_job",
                            "log": "waiting job result",
                            "status": "-",
                            "job_status_kwargs": {
                                "bk_biz_id": utils.DEFAULT_BIZ_ID_NAME["bk_biz_id"],
                                "job_instance_id": 10000,
                            },
                            "prefix": "job",
                        }
                    ],
                ),
                execute_call_assertion=None,
                patchers=[
                    Patcher(
                        target="apps.backend.components.collections.agent.task_service.callback.apply_async",
                        return_value=True,
                    )
                ],
            )
        ]

    def test_gen_install_channel_agent_command(self):
        host = models.Host.objects.get(bk_host_id=utils.BK_HOST_ID)
        installation_tool = gen_commands(host, utils.JOB_TASK_PIPELINE_ID, is_uninstall=False)
        token = re.match(r"(.*) -c (.*?) -O", installation_tool.run_cmd).group(2)
        run_cmd = (
            f"-s {utils.JOB_TASK_PIPELINE_ID} -r http://127.0.0.1/backend"
            f" -l http://1.1.1.1:{settings.BK_NODEMAN_NGINX_DOWNLOAD_PORT}/ -c {token}"
            f" -O 48668 -E 58925 -A 58625 -V 58930 -B 10020 -S 60020 -Z 60030 -K 10030"
            f' -e "127.0.0.1" -a "127.0.0.1" -k "127.0.0.1" -L /data/bkee/public/bknodeman/download'
            f" -HLIP 127.0.0.1 -HIIP 127.0.0.1 -HA root -HP 22 -HI 'aes_str:::H4MFaqax' -HC 0 -HNT AGENT"
            f" -HOT linux -HDD '/tmp/'"
            f" -HPP '17981' -HSN 'setup_agent.sh' -HS 'bash'"
            f" -p '/usr/local/gse' -I 1.1.1.1"
            f" -o http://1.1.1.1:{settings.BK_NODEMAN_NGINX_DOWNLOAD_PORT}/"
            f" -ADP 'False' -CPA 'http://127.0.0.1:17981'"
        )
        self.assertEqual(installation_tool.run_cmd, run_cmd)

    def tearDown(self):
        if self._testMethodName == "test_gen_install_channel_agent_command":
            return
        # 状态检查
        self.assertTrue(
            models.JobTask.objects.filter(bk_host_id=utils.BK_HOST_ID, current_step__endswith=DESCRIPTION).exists()
        )
        self.job_client_v2.stop()


@override_settings(REGISTER_WIN_SERVICE_WITH_PASS=True)
class InstallWindowsPAgentWithEncryptedPasswordSuccessTest(InstallPAgentSuccessTest):
    def setUp(self):
        super().setUp()
        models.Host.objects.filter(bk_host_id=utils.BK_HOST_ID).update(os_type=constants.OsType.WINDOWS)

    def test_gen_pagent_command(self):
        host = models.Host.objects.get(bk_host_id=utils.BK_HOST_ID)
        installation_tool = gen_commands(host, utils.JOB_TASK_PIPELINE_ID, is_uninstall=False)
        token = re.match(r"(.*) -c (.*?) -O", installation_tool.run_cmd).group(2)
        run_cmd = (
            f"-s {utils.JOB_TASK_PIPELINE_ID} -r http://127.0.0.1/backend -l http://127.0.0.1/download"
            f" -c {token}"
            f" -O 48668 -E 58925 -A 58625 -V 58930 -B 10020 -S 60020 -Z 60030 -K 10030"
            f' -e "1.1.1.1" -a "1.1.1.1" -k "1.1.1.1" -L /data/bkee/public/bknodeman/download'
            f" -HLIP 127.0.0.1 -HIIP 127.0.0.1 -HA root -HP 22 -HI 'aes_str:::H4MFaqax' -HC 0 -HNT PAGENT"
            f" -HOT windows -HDD 'C:\\tmp\\'"
            f" -HPP '17981' -HSN 'setup_agent.bat' -HS 'bash'"
            f" -p 'c:\\gse' -I 1.1.1.1"
            f" -o http://1.1.1.1:{settings.BK_NODEMAN_NGINX_DOWNLOAD_PORT}/ -HEP"
        )
        self.assertTrue(installation_tool.run_cmd.startswith(run_cmd))
