# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import os
import shutil
from typing import Optional

import mock
from django.conf import settings
from django.core.management import call_command

from apps.backend.tests.plugin import utils
from apps.core.files import core_files_constants
from apps.utils import files
from apps.utils.unittest.testcase import CustomBaseTestCase


class CopyFileToNginxTestCase(CustomBaseTestCase):
    BK_SCRIPTS_PATH: str = os.path.join(settings.PROJECT_ROOT, "script_tools")
    DOWNLOAD_PATH: Optional[str] = None
    OVERWRITE_OBJ__KV_MAP = {
        settings: {
            "BK_SCRIPTS_PATH": BK_SCRIPTS_PATH,
            "STORAGE_TYPE": core_files_constants.StorageType.FILE_SYSTEM.value,
        },
    }

    @classmethod
    def setUpClass(cls):
        cls.DOWNLOAD_PATH = files.mk_and_return_tmpdir()
        cls.OVERWRITE_OBJ__KV_MAP[settings]["DOWNLOAD_PATH"] = cls.DOWNLOAD_PATH
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.DOWNLOAD_PATH)
        super().tearDownClass()

    def test_case(self):
        call_command("copy_file_to_nginx")
        file_paths = files.fetch_file_paths_from_dir(dir_path=self.DOWNLOAD_PATH, ignored_dir_names=["__pycache__"])
        for file_path in file_paths:
            file_relative_path = file_path.replace(self.DOWNLOAD_PATH + os.path.sep, "")
            self.assertTrue(os.path.exists(os.path.join(self.BK_SCRIPTS_PATH, file_relative_path)))

        self.assertTrue(len(file_paths) != 0)
        self.assertEquals(
            len(file_paths),
            len(files.fetch_file_paths_from_dir(dir_path=self.BK_SCRIPTS_PATH, ignored_dir_names=["__pycache__"])),
        )


class BkRepoCopyFileToNginxTestCase(CopyFileToNginxTestCase):
    BK_SCRIPTS_PATH: str = os.path.join(settings.PROJECT_ROOT, "script_tools")
    OVERWRITE_OBJ__KV_MAP = {
        settings: {
            "BKREPO_USERNAME": "username",
            "BKREPO_PASSWORD": "blueking",
            "BKREPO_PROJECT": "project",
            "BKREPO_BUCKET": "private",
            "BKREPO_ENDPOINT_URL": "http://127.0.0.1",
            "BK_SCRIPTS_PATH": BK_SCRIPTS_PATH,
            "STORAGE_TYPE": core_files_constants.StorageType.BLUEKING_ARTIFACTORY.value,
        },
    }

    @classmethod
    def setUpClass(cls):
        mock.patch("apps.core.files.storage.CustomBKRepoStorage", utils.CustomBKRepoMockStorage).start()
        super().setUpClass()
