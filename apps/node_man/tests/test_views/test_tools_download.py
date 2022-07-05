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
from unittest.mock import patch

from django.conf import settings
from django.test.utils import override_settings
from rest_framework import status

from apps.node_man import constants
from apps.utils.unittest.testcase import CustomAPITestCase


class MockData(object):
    def __init__(self, data):
        self.data = data

    def get(self, url, params, stream):
        return self.data


class ToolsDownloadTestCase(CustomAPITestCase):
    MOCK_FILE = None
    MOCK_DATA = None

    @override_settings(DOWNLOAD_PATH=settings.BK_SCRIPTS_PATH)
    def setUp(self):
        super().setUp()
        backend_download_url = "/backend/tools/download/"
        tools_files = [file_name for file_name in constants.FILES_TO_PUSH_TO_PROXY[2]["files"]]
        self.MOCK_FILE = tools_files[0]
        result = self.client.get(backend_download_url, {"file_name": self.MOCK_FILE}, stream=True)
        self.MOCK_DATA = MockData(data=result)

    def test_tools_download(self):
        with patch("apps.node_man.views.requests", self.MOCK_DATA):
            url = "/tools/download/"
            response = self.client.get(url, {"file_name": self.MOCK_FILE}, stream=True)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
