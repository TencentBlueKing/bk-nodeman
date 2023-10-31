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

from .. import test_proxy
from . import test_agent


class FileSystemTestCase(
    test_proxy.FileSystemTestCase,
    test_agent.FileSystemTestCase,
):
    def parse_env_checker(self, env_values: typing.Dict[str, typing.Any]):
        # 字符串类型断言
        self.assertTrue(env_values["BK_GSE_HOME_DIR"] == "/usr/local/gse/proxy")
        # 数字类型断言
        self.assertTrue(env_values["BK_GSE_CLOUD_ID"] == 0)
        # 布尔类型断言, 布尔类型需要json.dumps之后的结果进行渲染
        self.assertTrue(env_values["BK_GSE_CUSTOM_BOOL_VALUE"] == "true")
        # 空字符串断言
        self.assertTrue(env_values["BK_GSE_FILE_AGENT_TLS_CA_FILE"] == "")


class BkRepoTestCase(FileSystemTestCase):
    pass
