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

import mock
from django.conf import settings
from django.core.management import call_command

from apps.backend.tests.plugin import utils
from apps.core.tag.targets import PluginTargetHelper
from apps.mock_data import backend_mkd
from apps.mock_data import utils as mock_data_utils
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


class ImportCommandWithTagTestCase(ImportCommandTestCase):
    def test_import_command(self):
        """测试导入命令"""
        call_command("init_official_plugins", tag="stable")
        self.assertTrue(models.Packages.objects.all().exists())
        self.assertTrue(models.UploadPackage.objects.all().exists())
        self.assertTrue(models.PluginConfigTemplate.objects.all().exists())

        plugin_desc = models.GsePluginDesc.objects.get(name=utils.PLUGIN_NAME)
        tag = PluginTargetHelper.get_tag(plugin_desc.id, utils.PACKAGE_VERSION)
        self.assertEqual(tag.name, "stable")


class ImportCommandWithRunPolicyTestCase(ImportCommandTestCase):
    def test_import_command(self):
        """测试导入命令"""

        scope = backend_mkd.subscription.unit.SUBSCRIPTION_DATA["scope"]
        sub = models.Subscription.objects.create(
            bk_biz_id=scope["bk_biz_id"],
            object_type=scope["object_type"],
            node_type=scope["node_type"],
            nodes=scope["nodes"],
            target_hosts=backend_mkd.subscription.unit.SUBSCRIPTION_DATA.get("target_hosts"),
            from_system="blueking",
            creator="admin",
            enable=True,
            name="test_policy",
            pid=models.Subscription.ROOT,
            plugin_name=utils.PLUGIN_NAME,
            category=models.Subscription.CategoryType.POLICY,
        )

        SubscriptionHandler = mock.MagicMock()
        SubscriptionHandler.run = mock.MagicMock(return_value={"task_id": 1, "subscription_id": sub.id})
        with mock.patch(
            "apps.backend.management.commands.init_official_plugins.SubscriptionHandler",
            return_value=SubscriptionHandler,
        ):
            call_command("init_official_plugins", tag="stable", run_policy=True)

        SubscriptionHandler.run.assert_called_once()
        self.assertTrue(models.Packages.objects.all().exists())
        self.assertTrue(models.UploadPackage.objects.all().exists())
        self.assertTrue(models.PluginConfigTemplate.objects.all().exists())

        plugin_desc = models.GsePluginDesc.objects.get(name=utils.PLUGIN_NAME)
        tag = PluginTargetHelper.get_tag(plugin_desc.id, utils.PACKAGE_VERSION)
        self.assertEqual(tag.name, "stable")


class ImportCommandBkRepoTestCase(ImportCommandTestCase):
    OVERWRITE_OBJ__KV_MAP = mock_data_utils.OVERWRITE_OBJ__KV_MAP

    @classmethod
    def setUpClass(cls):
        mock.patch("apps.core.files.storage.CustomBKRepoStorage", mock_data_utils.CustomBKRepoMockStorage).start()
        super().setUpClass()
