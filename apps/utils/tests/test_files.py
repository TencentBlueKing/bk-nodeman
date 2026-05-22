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
import shutil
import tarfile
import tempfile

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

    def _build_malicious_tar(self, member_name: str, link_name: str = "", linktype=tarfile.REGTYPE) -> io.BytesIO:
        """Build a tar archive in memory with a single attacker-controlled member."""
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tf:
            info = tarfile.TarInfo(name=member_name)
            info.type = linktype
            if linktype in (tarfile.LNKTYPE, tarfile.SYMTYPE):
                info.linkname = link_name
                tf.addfile(info)
            else:
                payload = b"pwn"
                info.size = len(payload)
                tf.addfile(info, io.BytesIO(payload))
        buf.seek(0)
        return buf

    def test_safe_extract_blocks_path_traversal(self):
        """Regression test: tar members that escape the target directory must be rejected."""
        bad_names = [
            "../evil",
            "/etc/passwd",
            "..",
            "a/..",
            "a/../../etc/passwd",
            "a/./../../evil",
        ]
        tmp_dir = tempfile.mkdtemp()
        try:
            for name in bad_names:
                buf = self._build_malicious_tar(name)
                with tarfile.open(fileobj=buf, mode="r") as tf:
                    with self.assertRaises(ValueError, msg=f"member {name!r} should be rejected"):
                        files.safe_extract(tf, path=tmp_dir)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_safe_extract_blocks_links(self):
        """Hard / symbolic link members must be rejected to prevent indirect traversal."""
        tmp_dir = tempfile.mkdtemp()
        try:
            for linktype in (tarfile.LNKTYPE, tarfile.SYMTYPE):
                buf = self._build_malicious_tar("inner", link_name="../../etc/passwd", linktype=linktype)
                with tarfile.open(fileobj=buf, mode="r") as tf:
                    with self.assertRaises(ValueError):
                        files.safe_extract(tf, path=tmp_dir)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_safe_extract_normal_archive(self):
        """A well-formed archive must extract successfully."""
        tmp_dir = tempfile.mkdtemp()
        try:
            buf = self._build_malicious_tar("sub/hello.txt")
            with tarfile.open(fileobj=buf, mode="r") as tf:
                files.safe_extract(tf, path=tmp_dir)
            self.assertTrue(os.path.isfile(os.path.join(tmp_dir, "sub", "hello.txt")))
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
