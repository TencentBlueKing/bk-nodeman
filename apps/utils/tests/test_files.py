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
import io
import os

from django.conf import settings

from apps.utils import files
from apps.utils.unittest.testcase import CustomBaseTestCase


class TestFiles(CustomBaseTestCase):
    def test_md5sum(self):
        self.assertEqual(files.md5sum(file_obj=io.BytesIO(b"this is a string")), "b37e16c620c055cf8207b999e3270e9b")

    def test_path_handler(self):
        windows_join_path = "C:\\gse\\external_plugins"
        not_windows_join_path = "/usr/local/gse/external_plugins"
        self.assertEqual(files.PathHandler("windows").join("C:\\gse", "external_plugins"), windows_join_path)
        self.assertEqual(files.PathHandler("WINDOWS").join("C:\\gse", "external_plugins"), windows_join_path)
        self.assertEqual(files.PathHandler("linux").join("/usr/local/gse", "external_plugins"), not_windows_join_path)
        self.assertEqual(files.PathHandler("aix").join("/usr/local/gse", "external_plugins"), not_windows_join_path)

    def test_mk_and_return_tmpdir(self):
        self.assertTrue(os.path.exists(files.mk_and_return_tmpdir()))

    def test_fetch_file_paths_from_dir(self):
        file_list = files.fetch_file_paths_from_dir(
            settings.PROJECT_ROOT, ignored_dir_names=["static"], ignored_file_names=["readme_en.md"]
        )
        self.assertTrue(os.path.join(settings.PROJECT_ROOT, "readme.md") in file_list)
        self.assertFalse(os.path.join(settings.PROJECT_ROOT, "readme_en.md") in file_list)
        self.assertFalse(os.path.join(settings.PROJECT_ROOT, "static", "index.html") in file_list)

        self.assertRaises(
            NotADirectoryError, files.fetch_file_paths_from_dir, os.path.join(settings.PROJECT_ROOT, "readme.md")
        )
