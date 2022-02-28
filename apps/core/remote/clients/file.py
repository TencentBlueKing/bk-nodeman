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

import asyncssh
import paramiko

from apps.utils import exc

from .. import exceptions


def exc_handler(
    wrapped: typing.Callable,
    instance: typing.Any,
    args: typing.Tuple[typing.Any],
    kwargs: typing.Dict[str, typing.Any],
    caught_exc: Exception,
):
    if isinstance(caught_exc, IOError):
        raise exceptions.RemoteIOError({"err_msg": caught_exc}) from caught_exc
    raise exceptions.RemoteIOError({"err_msg": caught_exc}) from caught_exc


class FileBaseClient(abc.ABC):

    _client = None

    def __init__(self, client=None, **options):
        if client:
            self._client = client

    @abc.abstractmethod
    def close(self):
        raise NotImplementedError

    def __enter__(self) -> "FileBaseClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        self._client = None

    async def __aenter__(self) -> "FileBaseClient":
        """异步上下文支持"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文支持"""
        self._client = None

    @abc.abstractmethod
    def put(self, localpaths: typing.List[str], remotepath: str):
        raise NotImplementedError

    @abc.abstractmethod
    def makedirs(self, path: str):
        raise NotImplementedError


class AsyncSFTPClient(FileBaseClient):

    _client: typing.Optional[asyncssh.SFTPClient] = None

    async def close(self):
        self._client.exit()
        await self._client.wait_closed()

    async def __aexit__(self, ex_type, exc_val, exc_tb):
        await self._client.__aexit__(ex_type, exc_val, exc_tb)
        await super().__aexit__(ex_type, exc_val, exc_tb)

    @exc.ExceptionHandler(exc_handler=exc_handler)
    async def put(self, localpaths: typing.List[str], remotepath: str):
        await self._client.put(localpaths, remotepath)

    @exc.ExceptionHandler(exc_handler=exc_handler)
    async def makedirs(self, path: str):
        await self._client.makedirs(path, exist_ok=True)


class ParamikoSFTPClient(FileBaseClient):

    _client: typing.Optional[paramiko.SFTPClient] = None

    def close(self):
        self._client.close()
        self._client = None

    @exc.ExceptionHandler(exc_handler=exc_handler)
    def put(self, localpaths: typing.List[str], remotepath: str):
        for localpath in localpaths:
            self._client.put(localpath, remotepath)

    def makedirs(self, path: str):
        # 可参考：https://stackoverflow.com/questions/14819681/
        raise NotImplementedError
