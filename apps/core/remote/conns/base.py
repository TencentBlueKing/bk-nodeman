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

import abc
import typing

from .. import constants
from ..clients import file

BytesOrStr = typing.Union[str, bytes]


class RunOutput:
    command: str = None
    stdout: typing.Optional[str] = None
    stderr: typing.Optional[str] = None

    def __init__(self, command: BytesOrStr, stdout: BytesOrStr, stderr: BytesOrStr):
        self.command = self.bytes2str(command)
        self.stdout = self.bytes2str(stdout)
        self.stderr = self.bytes2str(stderr)

    @staticmethod
    def bytes2str(val: BytesOrStr) -> str:
        if isinstance(val, bytes):
            return val.decode(encoding="utf-8")
        return val

    def __str__(self):
        outputs = [f"command: {self.command}", f"stdout: {self.stdout}", f"stderr: {self.stderr}"]
        return "\n".join(outputs)


class BaseConn(abc.ABC):
    """连接基类"""

    # 连接地址或域名
    host: str = None
    # 连接端口
    port: int = None
    # 登录用户名
    username: str = None
    # 登录密码
    password: typing.Optional[str] = None
    # 登录密钥
    client_key_strings: typing.Optional[typing.List[str]] = None
    # 连接超时时间
    connect_timeout: typing.Union[int, float] = None
    # 检查器列表，用于输出预处理
    inspectors: typing.List[typing.Callable[["BaseConn", RunOutput], None]] = None
    # 连接参数
    options: typing.Dict[str, typing.Any] = None
    # 连接对象
    _conn: typing.Any = None

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: typing.Optional[str] = None,
        client_key_strings: typing.Optional[typing.List[str]] = None,
        connect_timeout: typing.Optional[typing.Union[int, float]] = None,
        inspectors: typing.List[typing.Callable[["BaseConn", RunOutput], bool]] = None,
        **options,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.client_key_strings = client_key_strings or []
        self.connect_timeout = (connect_timeout, constants.DEFAULT_CONNECT_TIMEOUT)[connect_timeout is None]
        self.inspectors = inspectors or []
        self.options = options

    @abc.abstractmethod
    def close(self):
        raise NotImplementedError

    @abc.abstractmethod
    def connect(self):
        """
        创建一个连接
        :return:
        :raises:
            KeyExchangeError
            PermissionDeniedError 认证失败
            ConnectionLostError 连接丢失
            RemoteTimeoutError 连接超时
            DisconnectError 远程连接失败
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _run(
        self, command: str, check: bool = False, timeout: typing.Optional[typing.Union[int, float]] = None, **kwargs
    ) -> RunOutput:
        """命令执行"""
        raise NotImplementedError

    def run(
        self, command: str, check: bool = False, timeout: typing.Optional[typing.Union[int, float]] = None, **kwargs
    ) -> RunOutput:
        """
        命令执行
        :param command: 命令
        :param check: 返回码非0抛出 ProcessError 异常
        :param timeout: 命令执行最大等待时间，超时抛出 RemoteTimeoutError 异常
        :param kwargs:
        :return:
        :raises:
            SessionError 回话异常，连接被重置等
            ProcessError 命令执行异常
            RemoteTimeoutError 执行超时
        """
        run_output = self._run(command, check, timeout, **kwargs)
        # 输出预处理
        for inspector in self.inspectors:
            inspector(self, run_output)
        return run_output

    @abc.abstractmethod
    def file_client(self) -> file.FileBaseClient:
        """
        获取一个文件客户端
        :return:
        :raises:
            RemoteIOError IO 异常
            FileClientError 文件远程客户端异常
        """
        raise NotImplementedError

    def __enter__(self) -> "BaseConn":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        self._conn = None
