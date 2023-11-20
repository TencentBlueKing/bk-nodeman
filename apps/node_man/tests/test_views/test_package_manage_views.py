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

from apps.backend.tests.subscription.agent_adapter.test_adapter import (
    Proxy2StepAdapterTestCase,
)
from apps.core.tag.models import Tag
from apps.node_man.constants import GSE_PACKAGE_ENABLE_ALIAS_MAP
from apps.node_man.handlers.meta import MetaHandler
from apps.node_man.models import GsePackageDesc, GsePackages
from apps.node_man.tests.utils import (
    create_gse_package,
    update_or_create_package_records,
)


class PackageManageViewsTestCase(Proxy2StepAdapterTestCase):
    @patch(
        "apps.backend.agent.artifact_builder.base.BaseArtifactBuilder.update_or_create_package_records",
        update_or_create_package_records,
    )
    def setUp(self):
        super().setUp()
        with self.ARTIFACT_BUILDER_CLASS(initial_artifact_path=self.ARCHIVE_PATH, tags=["tag1", "tag2"]) as builder:
            builder.make()

        gse_package = GsePackages.objects.first()
        gse_package.created_at = "admin"
        gse_package.save()

    @classmethod
    def clear_agent_data(cls):
        GsePackages.objects.all().delete()
        GsePackageDesc.objects.all().delete()
        Tag.objects.all().delete()

    @patch("apps.node_man.permissions.package_manage.PackageManagePermission.has_permission", return_value=True)
    def test_list(self, *args, **kwargs):
        # 和之前的builder.make加起来100
        create_gse_package(99, start_id=1000, project="gse_proxy")

        result = self.client.get(path="/api/agent/package/", data={"project": "gse_proxy"})
        self.assertEqual(result["result"], True)
        self.assertEqual(result["data"]["total"], 100)
        self.assertEqual(len(result["data"]["list"]), 100)

        result = self.client.get(path="/api/agent/package/", data={"page": 1, "pagesize": 2, "project": "gse_proxy"})
        self.assertEqual(result["result"], True)
        self.assertEqual(result["data"]["total"], 100)
        self.assertEqual(len(result["data"]["list"]), 2)

    @patch("apps.node_man.permissions.package_manage.PackageManagePermission.has_permission", return_value=True)
    def test_list_with_filter_condition(self, *args, **kwargs):
        # 不筛选
        result = self.client.get(path="/api/agent/package/", data={"project": "gse_proxy"})
        self.assertEqual(result["data"]["total"], 1)
        self.assertEqual(len(result["data"]["list"]), 1)

        gse_package = GsePackages.objects.first()

        # 筛选tags
        result = self.client.get(path="/api/agent/package/", data={"tags": "tag1", "project": "gse_proxy"})
        self.assertEqual(len(result["data"]["list"]), 1)
        self.assertIn("tag1", self.collect_all_tag_names(result["data"]["list"][0]["tags"]))
        result = self.client.get(path="/api/agent/package/", data={"tags": "tag2", "project": "gse_proxy"})
        self.assertEqual(len(result["data"]["list"]), 1)
        self.assertIn("tag2", self.collect_all_tag_names(result["data"]["list"][0]["tags"]))
        result = self.client.get(path="/api/agent/package/", data={"tags": "tag3", "project": "gse_proxy"})
        self.assertEqual(len(result["data"]["list"]), 0)

        # 筛选os_cpu_arch
        os, cpu_arch = "linux", "x86_64"
        result = self.client.get(
            path="/api/agent/package/",
            data={"os_cpu_arch": f"{gse_package.os}_{gse_package.cpu_arch}", "project": "gse_proxy"},
        )
        self.assertEqual(len(result["data"]["list"]), 1)
        self.assertEqual(result["data"]["list"][0]["os"], os)
        self.assertEqual(result["data"]["list"][0]["cpu_arch"], cpu_arch)
        result = self.client.get(
            path="/api/agent/package/", data={"os_cpu_arch": "windows_x86_64", "project": "gse_proxy"}
        )
        self.assertEqual(len(result["data"]["list"]), 0)

        # 筛选created_by
        result = self.client.get(
            path="/api/agent/package/", data={"created_by": gse_package.created_by, "project": "gse_proxy"}
        )
        self.assertEqual(len(result["data"]["list"]), 1)
        self.assertEqual(result["data"]["list"][0]["created_by"], gse_package.created_by)
        result = self.client.get(path="/api/agent/package/", data={"created_by": "system", "project": "gse_proxy"})
        self.assertEqual(len(result["data"]["list"]), 0)

        # 筛选is_ready
        result = self.client.get(
            path="/api/agent/package/", data={"is_ready": str(gse_package.is_ready), "project": "gse_proxy"}
        )
        self.assertEqual(len(result["data"]["list"]), 1)
        self.assertEqual(result["data"]["list"][0]["is_ready"], True)
        result = self.client.get(path="/api/agent/package/", data={"is_ready": "false", "project": "gse_proxy"})
        self.assertEqual(len(result["data"]["list"]), 0)

        # 筛选version
        result = self.client.get(
            path="/api/agent/package/", data={"version": gse_package.version, "project": "gse_proxy"}
        )
        self.assertEqual(len(result["data"]["list"]), 1)
        self.assertEqual(result["data"]["list"][0]["version"], "1.0.1")
        result = self.client.get(path="/api/agent/package/", data={"version": "1.0.2", "project": "gse_proxy"})
        self.assertEqual(len(result["data"]["list"]), 0)

    @classmethod
    def collect_all_tag_names(cls, tags):
        """
        tags: [
            {
                "id": "builtin",
                "name": "内置标签",
                "children": [
                    {"id": "stable", "name": "稳定版本", "children": []},
                    {"id": "latest", "name": "最新版本", "children": []},
                ],
            },
            {
                "id": "custom",
                "name": "自定义标签",
                "children": [
                    {"id": "custom", "name": "自定义版本", "children": []}
                ]
            },
        ]
        """
        tag_name_set = set()
        for parent_tag in tags:
            for children_tag in parent_tag["children"]:
                tag_name_set.add(children_tag["name"])

        return tag_name_set

    @patch("apps.node_man.permissions.package_manage.PackageManagePermission.has_permission", return_value=True)
    def test_update(self, *args, **kwargs):
        first_gse_package = GsePackages.objects.first()
        self.assertEqual(first_gse_package.is_ready, True)
        self.client.put(
            path=f"/api/agent/package/{first_gse_package.id}/", data={"is_ready": False, "project": "gse_proxy"}
        )
        self.assertEqual(GsePackages.objects.first().is_ready, False)

        # 测试更新不存在的id是否服务器异常
        self.client.put(path="/api/agent/package/10000/", data={"is_ready": False})

    @patch("apps.node_man.permissions.package_manage.PackageManagePermission.has_permission", return_value=True)
    def test_destroy(self, *args, **kwargs):
        gse_packages = GsePackages.objects.all()
        self.assertEqual(len(gse_packages), 1)
        self.client.delete(path=f"/api/agent/package/{gse_packages.first().id}/", data={"project": "gse_proxy"})
        self.assertEqual(len(GsePackages.objects.all()), 0)

        # 测试删除存在的id是否服务器异常
        self.client.delete(path="/api/agent/package/10000/")

    @patch("apps.node_man.permissions.package_manage.PackageManagePermission.has_permission", return_value=True)
    def test_quick_search_condition(self, *args, **kwargs):
        result = self.client.get(path="/api/agent/package/quick_search_condition/", data={"project": "gse_proxy"})
        for condition in result["data"]:
            if condition["id"] == "os_cpu_arch":
                self.assertCountEqual(
                    condition["children"],
                    [
                        {"id": "ALL", "name": "ALL", "count": 1},
                        {"id": "linux_x86_64", "name": "linux_x86_64", "count": 1},
                    ],
                )
            elif condition["id"] == "version":
                self.assertCountEqual(
                    condition["children"],
                    [
                        {"id": "ALL", "name": "ALL", "count": 1},
                        {"id": "1.0.1", "name": "1.0.1", "count": 1},
                    ],
                )

    @patch("apps.node_man.permissions.package_manage.PackageManagePermission.has_permission", return_value=True)
    def test_filter_condition_with_agent_pkg_manage(self, *args, **kwargs):
        result = MetaHandler().filter_condition("agent_pkg_manage")
        self.assertEqual(len(GsePackages.objects.all()), 1)
        gse_package = GsePackages.objects.first()
        is_ready = gse_package.is_ready
        for condition in result:
            if condition["id"] == "version":
                self.assertCountEqual(
                    condition["children"],
                    [
                        {"id": gse_package.version, "name": gse_package.version},
                    ],
                )
            elif condition["id"] == "tags":
                self.assertCountEqual(
                    condition["children"],
                    [
                        {"id": "tag1", "name": ""},
                        {"id": "tag2", "name": ""},
                    ],
                )
            elif condition["id"] == "creator":
                self.assertCountEqual(
                    condition["children"],
                    [
                        {"id": gse_package.created_by, "name": gse_package.created_by},
                    ],
                )
            elif condition["id"] == "is_ready":
                self.assertCountEqual(
                    condition["children"],
                    [
                        {"id": is_ready, "name": GSE_PACKAGE_ENABLE_ALIAS_MAP.get(is_ready, is_ready)},
                    ],
                )
