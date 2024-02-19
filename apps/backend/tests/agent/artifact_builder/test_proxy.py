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

from apps.backend.tests.agent import utils
from apps.node_man import constants, models

from . import test_agent


class FileSystemTestCase(utils.ProxyBaseTestCase, test_agent.FileSystemTestCase):
    def parse_env_checker(self, env_values: typing.Dict[str, typing.Any]):
        # 字符串类型断言
        self.assertTrue(env_values["BK_GSE_HOME_DIR"] == "/usr/local/gse/proxy")
        # 数字类型断言
        self.assertTrue(env_values["BK_GSE_CLOUD_ID"] == 0)
        # 布尔类型断言, 布尔类型需要json.dumps之后的结果进行渲染
        self.assertTrue(env_values["BK_GSE_CUSTOM_BOOL_VALUE"] == "true")
        # 空字符串断言
        self.assertTrue(env_values["BK_GSE_FILE_AGENT_TLS_CA_FILE"] == "")

    def test_make(self):
        """测试安装包制作"""
        with self.ARTIFACT_BUILDER_CLASS(initial_artifact_path=self.ARCHIVE_PATH) as builder:
            builder.make()
        self.pkg_checker(version_str=utils.VERSION)
        self.template_and_env_checker(version_str=utils.VERSION)
        self.gse_package_and_desc_records_checker(version_str=utils.VERSION)


class BkRepoTestCase(FileSystemTestCase):
    pass


class AutoTypeStrategyCrontabTestCase(utils.AutoTypeStrategyMixin, FileSystemTestCase):
    pass


class AutoTypeStrategyDefaultTestCase(AutoTypeStrategyCrontabTestCase):
    AUTO_TYPE = constants.GseLinuxAutoType.RCLOCAL.value

    def setUp(self):
        super().setUp()
        models.GlobalSettings.objects.filter(key=models.GlobalSettings.KeyEnum.GSE2_LINUX_AUTO_TYPE.value).delete()


class AutoTypeStrategyDiffTestCase(AutoTypeStrategyCrontabTestCase):
    AUTO_TYPE_STRATEGY = {constants.GsePackageCode.PROXY.value: "crontab"}
    AUTO_TYPE = constants.GseLinuxAutoType.CRONTAB.value


class AutoTypeStrategyNotEffectTestCase(AutoTypeStrategyCrontabTestCase):
    AUTO_TYPE_STRATEGY = {constants.GsePackageCode.AGENT.value: "crontab"}
    AUTO_TYPE = constants.GseLinuxAutoType.RCLOCAL.value
