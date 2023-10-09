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
import shutil
import uuid

import mock
from django.conf import settings
from django.core.management import call_command

from apps.backend.tests.agent import utils
from apps.mock_data import utils as mock_data_utils
from apps.node_man import models

from . import test_agent


class FileSystemImportAgentTestCase(test_agent.FileSystemTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.OVERWRITE_OBJ__KV_MAP[settings].update(
            BK_OFFICIAL_PLUGINS_INIT_PATH=os.path.join(cls.TMP_DIR, uuid.uuid4().hex)
        )
        super().setUpTestData()

    def setUp(self):
        super().setUp()
        agent_module_dir: str = os.path.join(settings.BK_OFFICIAL_PLUGINS_INIT_PATH, self.ARTIFACT_BUILDER_CLASS.NAME)
        os.makedirs(agent_module_dir, exist_ok=True)
        shutil.copyfile(self.ARCHIVE_PATH, os.path.join(agent_module_dir, self.ARCHIVE_NAME))

    def test_make(self):
        """测试导入命令"""
        call_command("init_agents")
        self.assertTrue(models.UploadPackage.objects.all().exists())
        self.pkg_checker(version_str=utils.VERSION)
        self.template_and_env_checker(version_str=utils.VERSION)
        self.gse_package_and_desc_records_checker(version_str=utils.VERSION)

    def test_make__overwrite_version(self):
        """测试版本号覆盖"""
        call_command("init_agents", overwrite_version=self.OVERWRITE_VERSION)
        self.pkg_checker(version_str=utils.VERSION)
        self.template_and_env_checker(version_str=utils.VERSION)
        self.pkg_checker(version_str=self.OVERWRITE_VERSION)
        self.tag_checker()
        self.gse_package_and_desc_records_checker(version_str=utils.VERSION)


class BkRepoImportAgentTestCase(FileSystemImportAgentTestCase):
    FILE_OVERWRITE = True
    OVERWRITE_OBJ__KV_MAP = mock_data_utils.OVERWRITE_OBJ__KV_MAP

    @classmethod
    def setUpClass(cls):
        mock.patch("apps.core.files.storage.CustomBKRepoStorage", mock_data_utils.CustomBKRepoMockStorage).start()
        super().setUpClass()


class FileSystemImportProxyTestCase(FileSystemImportAgentTestCase):
    pass


class BkRepoImportProxyTestCase(FileSystemImportProxyTestCase):
    pass
