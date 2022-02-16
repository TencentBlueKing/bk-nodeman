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
import asyncssh
import mock
from six import StringIO

ASYNCSSH_CONNECT_MOCK_PATH = "apps.core.remote.conns.asyncssh_impl.asyncssh.connect"

PARAMIKO_SSH_CLIENT_MOCK_PATH = "apps.core.remote.conns.paramiko_impl.paramiko.SSHClient"


class AsyncSSHMockClient:
    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def run(self, command: str, check=False, timeout=None, **kwargs):
        return asyncssh.SSHCompletedProcess(command=command, exit_status=0, stdout="", stderr="")


class ParamikoSSHMockClient:
    @staticmethod
    def set_missing_host_key_policy(*args, **kwargs):
        pass

    @staticmethod
    def connect(*args, **kwargs):
        pass

    @staticmethod
    def close():
        pass

    @staticmethod
    def exec_command(command: str, check=False, timeout=None, **kwargs):
        return command, StringIO(""), StringIO("")


@asyncssh.misc.async_context_manager
async def asyncssh_mock_connect(
    host, port=(), *, tunnel=(), family=(), flags=0, local_addr=None, config=(), options=None, **kwargs
) -> AsyncSSHMockClient:
    asyncssh.SSHClientConnectionOptions(
        options, config=config, host=host, port=port, tunnel=tunnel, family=family, local_addr=local_addr, **kwargs
    )
    return AsyncSSHMockClient()


def get_asyncssh_connect_mock_patch():
    return mock.patch(ASYNCSSH_CONNECT_MOCK_PATH, asyncssh_mock_connect)


def get_paramiko_ssh_client_mock_patch():
    return mock.patch(PARAMIKO_SSH_CLIENT_MOCK_PATH, ParamikoSSHMockClient)
