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
import socket
import typing
from concurrent import futures

import asyncssh
from django.utils.translation import ugettext_lazy as _

from .. import constants, exceptions
from ..clients import file
from . import base


class AsyncsshConn(base.BaseConn):
    """
    基于 asyncssh 实现的异步 SSH 连接
    asyncssh
        仓库：https://github.com/ronf/asyncssh
        文档：https://asyncssh.readthedocs.io/en/stable/index.html
    """

    # SSH 客户端连接，具体功能及 api 参考：https://asyncssh.readthedocs.io/en/stable/api.html#sshclientconnection
    _conn: typing.Optional[asyncssh.SSHClientConnection] = None

    def close(self):
        pass

    async def connect(self):
        client_keys = []
        for client_key_string in self.client_key_strings:
            try:
                client_keys.append(asyncssh.import_private_key(client_key_string))
            except asyncssh.KeyImportError:
                # 忽略RSA密钥导入失败，后续逻辑会捕获相应的远程登录异常
                pass

        try:
            # API 文档：https://asyncssh.readthedocs.io/en/stable/api.html#connect
            # 连接参数说明（SSHClientConnectionOptions）：👇
            # https://asyncssh.readthedocs.io/en/stable/api.html#asyncssh.SSHClientConnectionOptions
            # 认证顺序：👇 可以显式传入 preferred_auth 进行控制
            # gssapi-keyex -> gssapi-with-mic -> hostbased -> [ publickey -> keyboard-interactive -> password ]
            self._conn = await asyncssh.connect(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                # 若无传入密钥，设置 client_keys=None，禁用本地私钥扫描
                client_keys=client_keys or None,
                kex_algs=constants.KEX_ALGS,
                encryption_algs=constants.ENCRYPTION_ALGS,
                known_hosts=None,
                connect_timeout=self.connect_timeout,
                **self.options
            )
        except asyncssh.KeyExchangeFailed as e:
            raise exceptions.KeyExchangeError({"err_msg": e}) from e
        except asyncssh.PermissionDenied as e:
            raise exceptions.PermissionDeniedError({"err_msg": e}) from e
        except asyncssh.ConnectionLost as e:
            raise exceptions.ConnectionLostError({"err_msg": e}) from e
        except futures.TimeoutError as e:
            raise exceptions.RemoteTimeoutError(_("连接超时：{err_msg}").format(err_msg=e)) from e
        except (asyncssh.DisconnectError, socket.error, Exception) as e:
            raise exceptions.DisconnectError({"err_msg": e}) from e

        return self._conn

    async def _run(
        self, command: str, check: bool = False, timeout: typing.Optional[typing.Union[int, float]] = None, **kwargs
    ) -> base.RunOutput:
        try:
            ssh_completed_process: asyncssh.SSHCompletedProcess = await self._conn.run(
                command, check=check, timeout=timeout
            )
        except asyncssh.TimeoutError as e:
            raise exceptions.RemoteTimeoutError(_("命令执行超时：{err_msg}").format(err_msg=e)) from e
        except asyncssh.ChannelOpenError as e:
            raise exceptions.SessionError({"err_msg": e}) from e
        except asyncssh.ProcessError as e:
            # 仅在 check=True 时抛出
            raise exceptions.ProcessError(
                {
                    "err_msg": _("exit_status -> {exit_status}, stdout -> {stdout}, stderr -> {stderr}").format(
                        exit_status=e.exit_status, stdout=e.stdout, stderr=e.stderr
                    )
                }
            ) from e

        return base.RunOutput(command=command, stdout=ssh_completed_process.stdout, stderr=ssh_completed_process.stderr)

    async def run(
        self, command: str, check: bool = False, timeout: typing.Optional[typing.Union[int, float]] = None, **kwargs
    ) -> base.RunOutput:
        run_output = await self._run(command, check, timeout, **kwargs)
        for inspector in self.inspectors:
            inspector(self, run_output)
        return run_output

    async def file_client(self) -> file.AsyncSFTPClient:
        if self._conn is None:
            await self.connect()
        sftp_client = await self._conn.start_sftp_client()
        return file.AsyncSFTPClient(sftp_client)

    async def __aenter__(self):
        """异步上下文支持"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文支持"""
        await self._conn.__aexit__(exc_type, exc_val, exc_tb)
        self._conn = None
