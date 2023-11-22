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


from apps.backend.tests.components.collections.plugin.utils import (
    GSE_PLUGIN_DESC_INFO,
    PKG_INFO,
    PKG_PROJECT_NAME,
)
from apps.node_man import models
from apps.utils.unittest.testcase import CustomAPITestCase


class PluginViewTestCase(CustomAPITestCase):
    PLUGIN_NAME = "bk_collector"

    def setUp(self) -> None:
        # 初始化数据
        gse_plugin_dict = dict(GSE_PLUGIN_DESC_INFO, **{"name": self.PLUGIN_NAME, "config_file": "config.yaml"})
        models.GsePluginDesc.objects.create(**gse_plugin_dict)
        package_dict = dict(PKG_INFO, **{"project": self.PLUGIN_NAME})
        models.Packages.objects.create(**package_dict)

    def test_common_plugin_list(self):
        response = self.client.get(f"/api/plugin/{self.PLUGIN_NAME}/package/", {"os": "LINUX"})
        self.assertTrue(response["result"])
        self.assertEqual(response["data"][0]["project"], self.PLUGIN_NAME)


class PluginViewCommonTestCase(PluginViewTestCase):
    PLUGIN_NAME = "bkmonitorbeat"


class PluginPackageDashTestCase(PluginViewTestCase):
    PLUGIN_NAME = "bk-collector"


class PluginNotFoundViewTestCase(PluginViewTestCase):
    PLUGIN_NAME = "bk_collector_not-found"

    def setUp(self) -> None:
        super().setUp()
        models.GsePluginDesc.objects.filter(name=self.PLUGIN_NAME).update(name=PKG_PROJECT_NAME)
        models.Packages.objects.filter(project=self.PLUGIN_NAME).update(project=PKG_PROJECT_NAME)

    def test_common_plugin_list(self):
        response = self.client.get(f"/api/plugin/{self.PLUGIN_NAME}/package/", {"os": "LINUX"})
        self.assertFalse(response["result"])
        self.assertRegex(response["message"], r"bk_collector_not-found in.*")
