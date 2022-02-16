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
import asyncio
import random

from apps.mock_data import utils
from apps.utils import concurrent
from apps.utils.encrypt import rsa
from apps.utils.unittest import testcase

from .. import conns
from . import base


class AsyncsshConnTestCase(testcase.CustomBaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        base.get_asyncssh_connect_mock_patch().start()

    @staticmethod
    async def run_async():
        client_key_string, __ = rsa.generate_keys()
        async with conns.AsyncsshConn(
            host=utils.DEFAULT_IP,
            port=22,
            username=utils.DEFAULT_USERNAME,
            password="123",
            client_key_strings=[client_key_string],
        ) as conn:
            return await conn.run("echo hello", check=True)

    def test_run_with_thread(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.run_async())

    def test_run_with_multi_coroutine(self):
        test_num = random.randint(2, 5)
        outputs = concurrent.batch_call_coroutine(func=self.run_async, params_list=[{} for __ in range(test_num)])
        for output in outputs:
            self.assertTrue(isinstance(output, conns.RunOutput))


class ParamikoConnTestCase(testcase.CustomBaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        base.get_paramiko_ssh_client_mock_patch().start()

    def test_run(self):
        client_key_string, __ = rsa.generate_keys()
        with conns.ParamikoConn(
            host=utils.DEFAULT_IP,
            port=22,
            username=utils.DEFAULT_USERNAME,
            password="123",
            client_key_strings=[client_key_string],
        ) as conn:
            output = conn.run("echo hello", check=True)
        self.assertTrue(isinstance(output, conns.RunOutput))
