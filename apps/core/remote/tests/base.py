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
import typing

import asyncssh
import mock
from six import StringIO

from ..clients import file
from ..conns import RunOutput, base

ASYNCSSH_CONNECT_MOCK_PATH = "apps.core.remote.conns.asyncssh_impl.asyncssh.connect"

PARAMIKO_SSH_CLIENT_MOCK_PATH = "apps.core.remote.conns.paramiko_impl.paramiko.SSHClient"


class ParamikoSFTPMockClient:
    def close(self, *ars, **kwargs):
        pass

    def put(self, *ars, **kwargs):
        pass


class AsyncsshSFTPMockClient:
    async def put(self, *args, **kwargs):
        pass

    async def makedirs(self, *args, **kwargs):
        pass

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._conn = None

    def exit(self, *args, **kwargs):
        pass

    def wait_closed(self, *args, **kwargs):
        pass


class FileMockClientMixin:
    FILE_MOCK_CLIENT_CLASS = None

    def create_file_mock_client(self):
        return self.FILE_MOCK_CLIENT_CLASS()


class AsyncMockConn(base.BaseConn):
    def close(self):
        pass

    async def connect(self):
        pass

    def _run(
        self, command: str, check: bool = False, timeout: typing.Optional[typing.Union[int, float]] = None, **kwargs
    ) -> RunOutput:
        pass

    def file_client(self) -> file.FileBaseClient:
        pass

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._conn = None


class AsyncSSHMockClient(FileMockClientMixin):

    FILE_MOCK_CLIENT_CLASS = AsyncsshSFTPMockClient

    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def run(self, command: str, check=False, timeout=None, **kwargs):
        return asyncssh.SSHCompletedProcess(command=command, exit_status=0, stdout="", stderr="")

    async def start_sftp_client(self, *args, **kwargs):
        return self.create_file_mock_client()


class ParamikoSSHMockClient(FileMockClientMixin):

    FILE_MOCK_CLIENT_CLASS = ParamikoSFTPMockClient

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

    def open_sftp(self, *args, **kwargs):
        return self.create_file_mock_client()


def get_asyncssh_mock_connect(asyncssh_mock_connect_client_class: typing.Type[AsyncSSHMockClient]):

    asyncssh_mock_connect_client_class = asyncssh_mock_connect_client_class or AsyncSSHMockClient

    @asyncssh.misc.async_context_manager
    async def asyncssh_mock_connect(
        host, port=(), *, tunnel=(), family=(), flags=0, local_addr=None, config=(), options=None, **kwargs
    ) -> AsyncSSHMockClient:
        asyncssh.SSHClientConnectionOptions(
            options, config=config, host=host, port=port, tunnel=tunnel, family=family, local_addr=local_addr, **kwargs
        )
        return asyncssh_mock_connect_client_class()

    return asyncssh_mock_connect


def get_asyncssh_connect_mock_patch(
    asyncssh_mock_connect_client_class: typing.Optional[typing.Type[AsyncSSHMockClient]] = None,
):
    return mock.patch(ASYNCSSH_CONNECT_MOCK_PATH, get_asyncssh_mock_connect(asyncssh_mock_connect_client_class))


def get_paramiko_ssh_client_mock_patch():
    return mock.patch(PARAMIKO_SSH_CLIENT_MOCK_PATH, ParamikoSSHMockClient)
