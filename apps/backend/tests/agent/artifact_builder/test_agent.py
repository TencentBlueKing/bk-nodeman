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
import os

import mock
from django.conf import settings
from django.db.utils import IntegrityError

from apps.backend.tests.agent import utils
from apps.mock_data import utils as mock_data_utils
from apps.node_man import constants, models


class FileSystemTestCase(utils.AgentBaseTestCase):

    OVERWRITE_VERSION = "stable"

    @classmethod
    def setUpClass(cls):
        # 关闭Agent包管理
        try:
            models.GlobalSettings.set_config(models.GlobalSettings.KeyEnum.ENABLE_AGENT_PKG_MANAGE.value, False)
        except IntegrityError:
            models.GlobalSettings.update_config(models.GlobalSettings.KeyEnum.ENABLE_AGENT_PKG_MANAGE.value, False)
        super().setUpClass()

    def pkg_checker(self, version_str: str):
        """
        安装包检查
        :param version_str: 版本
        :return:
        """
        pkg_name: str = f"{self.ARTIFACT_BUILDER_CLASS.NAME}-{version_str}.tgz"
        for package_os, cpu_arch in self.OS_CPU_CHOICES:
            package_path: str = os.path.join(
                settings.DOWNLOAD_PATH, self.ARTIFACT_BUILDER_CLASS.BASE_STORAGE_DIR, package_os, cpu_arch, pkg_name
            )
            self.assertTrue(os.path.exists(package_path))

    def test_make(self):
        """测试安装包制作"""
        with self.ARTIFACT_BUILDER_CLASS(initial_artifact_path=self.ARCHIVE_PATH) as builder:
            builder.make()
        self.pkg_checker(version_str=utils.VERSION)

    def test_make__overwrite_version(self):
        """测试版本号覆盖"""
        with self.ARTIFACT_BUILDER_CLASS(
            initial_artifact_path=self.ARCHIVE_PATH, overwrite_version=self.OVERWRITE_VERSION
        ) as builder:
            builder.make()
        self.pkg_checker(version_str=self.OVERWRITE_VERSION)


class BkRepoTestCase(FileSystemTestCase):
    FILE_OVERWRITE = True
    OVERWRITE_OBJ__KV_MAP = mock_data_utils.OVERWRITE_OBJ__KV_MAP

    @classmethod
    def setUpClass(cls):
        mock.patch("apps.core.files.storage.CustomBKRepoStorage", mock_data_utils.CustomBKRepoMockStorage).start()
        super().setUpClass()


class AutoTypeStrategyCrontabTestCase(utils.AutoTypeStrategyMixin, FileSystemTestCase):
    pass


class AutoTypeStrategyDefaultTestCase(AutoTypeStrategyCrontabTestCase):
    AUTO_TYPE = constants.GseLinuxAutoType.RCLOCAL.value

    def setUp(self):
        super().setUp()
        models.GlobalSettings.objects.filter(key=models.GlobalSettings.KeyEnum.GSE2_LINUX_AUTO_TYPE.value).delete()


class AutoTypeStrategyDiffTestCase(AutoTypeStrategyCrontabTestCase):
    AUTO_TYPE_STRATEGY = {"gse_proxy": "crontab"}
    AUTO_TYPE = constants.GseLinuxAutoType.RCLOCAL.value


class AutoTypeStrategyNotEffectTestCase(AutoTypeStrategyCrontabTestCase):
    AUTO_TYPE_STRATEGY = {"gse_agent": "crontab"}
    AUTO_TYPE = constants.GseLinuxAutoType.CRONTAB.value
