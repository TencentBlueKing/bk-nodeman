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
import time
import typing

import paramiko
from django.utils.translation import ugettext_lazy as _
from six import StringIO

from .. import exceptions
from ..clients import file
from . import base


class ParamikoConn(base.BaseConn):
    """
    基于 paramiko 实现的同步 SSH 连接
    paramiko
        仓库：https://github.com/paramiko/paramiko
        文档：https://www.paramiko.org/
    """

    _conn: typing.Optional[paramiko.SSHClient] = None

    def close(self):
        self._conn.close()

    def connect(self) -> paramiko.SSHClient:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # 仅支持单个密钥
        if self.client_key_strings:
            pkey = paramiko.RSAKey.from_private_key(StringIO(self.client_key_strings[0]))
        else:
            pkey = None

        # API 文档：https://docs.paramiko.org/en/stable/api/client.html#paramiko.client.SSHClient.connect
        # 认证顺序：
        #  - pkey or key_filename
        #  - Any “id_rsa”, “id_dsa” or “id_ecdsa” key discoverable in ~/.ssh/ (look_for_keys=True)
        #  - username/password auth, if a password was given
        try:
            ssh.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                pkey=pkey,
                password=self.password,
                timeout=self.connect_timeout,
                # 从安全上考虑，禁用本地RSA私钥扫描
                look_for_keys=False,
                **self.options
            )
        except paramiko.BadHostKeyException as e:
            raise exceptions.PermissionDeniedError(_("密钥验证失败：{err_msg}").format(err_msg=e)) from e
        except paramiko.AuthenticationException as e:
            raise exceptions.PermissionDeniedError({"err_msg": e}) from e
        except (paramiko.SSHException, socket.error, Exception) as e:
            raise exceptions.DisconnectError({"err_msg": e}) from e
        self._conn = ssh
        return ssh

    def _run(
        self, command: str, check: bool = False, timeout: typing.Optional[typing.Union[int, float]] = None, **kwargs
    ) -> base.RunOutput:

        begin_time = time.time()
        try:
            __, stdout, stderr = self._conn.exec_command(command=command, timeout=timeout)
        except paramiko.SSHException as e:
            if check:
                raise exceptions.ProcessError({"err_msg": e})
            # exec_command 方法没有明确抛出 timeout 异常，需要记录调用前后时间差进行抛出
            cost_time = time.time() - begin_time
            if cost_time > timeout:
                raise exceptions.RemoteTimeoutError(_("连接超时：{err_msg}").format(err_msg=e)) from e
            stdout, stderr = StringIO(""), StringIO(str(e))
        return base.RunOutput(command=command, stdout=stdout.read(), stderr=stderr.read())

    def file_client(self) -> file.ParamikoSFTPClient:
        if self._conn is None:
            self.connect()
        sftp_client = self._conn.open_sftp()
        return file.ParamikoSFTPClient(sftp_client)
