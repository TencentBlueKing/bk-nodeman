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

from django.conf import settings
from django.core.management import call_command

from apps.backend.tests.plugin import utils
from apps.node_man import models


class ImportCommandTestCase(utils.PluginBaseTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.OVERWRITE_OBJ__KV_MAP[settings].update(BK_OFFICIAL_PLUGINS_INIT_PATH=cls.TMP_DIR)
        super().setUpTestData()

    def test_import_command(self):
        """测试导入命令"""
        call_command("init_official_plugins")
        self.assertTrue(models.Packages.objects.all().exists())
        self.assertTrue(models.UploadPackage.objects.all().exists())
        self.assertTrue(models.PluginConfigTemplate.objects.all().exists())
