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

import yaml
from django.conf import settings
from django.test.utils import override_settings

from apps.utils.unittest.testcase import CustomAPITestCase


class ViewsTestCase(CustomAPITestCase):
    def version__assert_version(self, expect_status: str):
        app_yaml_path = os.path.join(settings.PROJECT_ROOT, "app.yml")
        with open(file=app_yaml_path, encoding="utf-8") as dev_yaml_fs:
            app_yaml = yaml.safe_load(dev_yaml_fs)
        self.assertEqual(expect_status, app_yaml["version"])

    @override_settings(BK_BACKEND_CONFIG=False)
    def test_version(self):
        for url in ["/version/", "/backend/version/"]:
            version_info = self.client.get(url)
            self.assertEqual(version_info["app_code"], settings.APP_CODE)
            self.assertEqual(version_info["module"], "default")
            self.version__assert_version(expect_status=version_info["version"])

    @override_settings(BK_BACKEND_CONFIG=True)
    def test_version__backend(self):
        for url in ["/version/", "/backend/version/"]:
            version_info = self.client.get(url)
            self.assertEqual(version_info["module"], "backend")
            self.version__assert_version(expect_status=version_info["version"])
