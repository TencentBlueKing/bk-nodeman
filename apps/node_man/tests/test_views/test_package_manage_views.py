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
import uuid
from unittest.mock import patch

from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile

from apps.backend.plugin.handler import PluginHandler
from apps.backend.sync_task.constants import SyncTaskType
from apps.backend.tests.subscription.agent_adapter.test_adapter import (
    Proxy2StepAdapterTestCase,
)
from apps.core.files.storage import get_storage
from apps.core.tag.constants import TargetType
from apps.core.tag.models import Tag
from apps.node_man import constants
from apps.node_man.constants import (
    CPU_TUPLE,
    GSE_PACKAGE_ENABLE_ALIAS_MAP,
    OS_TYPE,
    CategoryType,
    GsePackageCode,
)
from apps.node_man.handlers.meta import MetaHandler
from apps.node_man.models import (
    GsePackageDesc,
    GsePackages,
    Host,
    ProcessStatus,
    UploadPackage,
)
from apps.node_man.tests.utils import create_gse_package, create_host
from apps.utils.files import md5sum
from common.api.modules.utils import add_esb_info_before_request


def delay(self, *args, **kwargs):
    self.task_func(*args, **kwargs)
    return "1"


class PackageManageViewsTestCaseUsingProxy(Proxy2StepAdapterTestCase):
    def init_tags(self):
        try:
            agent_target_id = GsePackageDesc.objects.get(
                project=GsePackageCode.AGENT.value, category=CategoryType.official
            ).id

            proxy_target_id = GsePackageDesc.objects.get(
                project=GsePackageCode.PROXY.value, category=CategoryType.official
            ).id
        except GsePackageDesc.DoesNotExist:
            agent_target_id = GsePackageDesc.objects.create(
                project=GsePackageCode.AGENT.value, category=CategoryType.official
            ).id

            proxy_target_id = GsePackageDesc.objects.create(
                project=GsePackageCode.PROXY.value, category=CategoryType.official
            ).id

        for target_id in [proxy_target_id, agent_target_id]:
            # 添加Tag记录
            Tag.objects.create(
                name="stable",
                description="稳定版本",
                target_id=target_id,
                target_type=TargetType.AGENT.value,
            )
            Tag.objects.create(
                name="latest",
                description="最新版本",
                target_id=target_id,
                target_type=TargetType.AGENT.value,
            )
            Tag.objects.create(
                name="test",
                description="测试版本",
                target_id=target_id,
                target_type=TargetType.AGENT.value,
            )

    def upload_file(self):
        with open(self.ARCHIVE_PATH, "rb") as f:
            file_content = f.read()

            memory_uploaded_file = InMemoryUploadedFile(
                file=io.BytesIO(file_content),
                field_name=None,
                name=os.path.basename(self.ARCHIVE_PATH),
                content_type="text/plain",
                size=len(file_content),
                charset=None,
            )

        self.storage = get_storage()
        with memory_uploaded_file.open("rb") as tf:
            self.md5 = md5sum(file_obj=tf, closed=False)
            self.storage_path = self.storage.save(name=os.path.join(settings.UPLOAD_PATH, tf.name), content=tf)

        self.file_name = tf.name

        params = {
            "md5": self.md5,
            "module": "agent",
            "file_name": tf.name,
            "file_path": self.storage_path,
            "download_url": self.storage.url(self.storage_path),
        }

        add_esb_info_before_request(params)

        PluginHandler.upload(
            md5=params["md5"],
            origin_file_name=params["file_name"],
            module=params["module"],
            operator=params["bk_username"],
            app_code=params["bk_app_code"],
            file_path=params.get("file_path"),
            download_url=params.get("download_url"),
        )

    def setUp(self, *args, **kwargs):
        super().setUp()

        self.init_tags()

        with self.ARTIFACT_BUILDER_CLASS(initial_artifact_path=self.ARCHIVE_PATH, tags=["stable", "latest"]) as builder:
            builder.make()

        self.upload_file()

        gse_package = GsePackages.objects.first()
        gse_package.created_at = "admin"
        gse_package.save()

        self.task_map = {}

    @classmethod
    def clear_agent_data(cls):
        GsePackages.objects.all().delete()
        GsePackageDesc.objects.all().delete()
        Tag.objects.all().delete()

    def tearDown(self):
        super().tearDown()

        if os.path.exists(self.storage_path):
            os.remove(self.storage_path)

    @patch("apps.node_man.permissions.package_manage.PackageManagePermission.has_permission", return_value=True)
    def test_list(self, *args, **kwargs):
        # 和之前的builder.make加起来100
        create_gse_package(99, start_id=1000, project="gse_proxy")

        result = self.client.get(path="/api/agent/package/", data={"project": "gse_proxy"})
        self.assertEqual(result["result"], True)
        self.assertEqual(len(result["data"]), 100)

        result = self.client.get(path="/api/agent/package/", data={"page": 1, "pagesize": 2, "project": "gse_proxy"})
        self.assertEqual(result["result"], True)
        self.assertEqual(result["data"]["total"], 100)
        self.assertEqual(len(result["data"]["list"]), 2)

    @patch("apps.node_man.permissions.package_manage.PackageManagePermission.has_permission", return_value=True)
    def test_list_with_filter_condition(self, *args, **kwargs):
        # 不筛选
        result = self.client.get(path="/api/agent/package/", data={"page": 1, "pagesize": 2, "project": "gse_proxy"})
        self.assertEqual(result["data"]["total"], 1)
        self.assertEqual(len(result["data"]["list"]), 1)

        gse_package = GsePackages.objects.first()

        # 筛选tags
        result = self.client.get(
            path="/api/agent/package/", data={"page": 1, "pagesize": 2, "tag_names": "stable", "project": "gse_proxy"}
        )
        self.assertEqual(len(result["data"]["list"]), 1)
        self.assertIn("stable", self.collect_all_tag_names(result["data"]["list"][0]["tags"]))
        result = self.client.get(
            path="/api/agent/package/", data={"page": 1, "pagesize": 2, "tag_names": "latest", "project": "gse_proxy"}
        )
        self.assertEqual(len(result["data"]["list"]), 1)
        self.assertIn("latest", self.collect_all_tag_names(result["data"]["list"][0]["tags"]))
        result = self.client.get(
            path="/api/agent/package/", data={"page": 1, "pagesize": 2, "tag_names": "test", "project": "gse_proxy"}
        )
        self.assertEqual(len(result["data"]["list"]), 0)

        # 筛选os_cpu_arch
        computer_os, cpu_arch = "linux", "x86_64"
        result = self.client.get(
            path="/api/agent/package/",
            data={
                "page": 1,
                "pagesize": 2,
                "os": gse_package.os,
                "cpu_arch": gse_package.cpu_arch,
                "project": "gse_proxy",
            },
        )
        self.assertEqual(len(result["data"]["list"]), 1)
        self.assertEqual(result["data"]["list"][0]["os"], computer_os)
        self.assertEqual(result["data"]["list"][0]["cpu_arch"], cpu_arch)
        result = self.client.get(
            path="/api/agent/package/",
            data={"page": 1, "pagesize": 2, "os": "windows", "cpu_arch": "x86_64", "project": "gse_proxy"},
        )
        self.assertEqual(len(result["data"]["list"]), 0)

        # 筛选created_by
        result = self.client.get(
            path="/api/agent/package/",
            data={"page": 1, "pagesize": 2, "created_by": gse_package.created_by, "project": "gse_proxy"},
        )
        self.assertEqual(len(result["data"]["list"]), 1)
        self.assertEqual(result["data"]["list"][0]["created_by"], gse_package.created_by)
        result = self.client.get(
            path="/api/agent/package/", data={"page": 1, "pagesize": 2, "created_by": "system", "project": "gse_proxy"}
        )
        self.assertEqual(len(result["data"]["list"]), 0)

        # 筛选is_ready
        result = self.client.get(
            path="/api/agent/package/",
            data={"page": 1, "pagesize": 2, "is_ready": str(gse_package.is_ready), "project": "gse_proxy"},
        )
        self.assertEqual(len(result["data"]["list"]), 1)
        self.assertEqual(result["data"]["list"][0]["is_ready"], True)
        result = self.client.get(
            path="/api/agent/package/", data={"page": 1, "pagesize": 2, "is_ready": "False", "project": "gse_proxy"}
        )
        self.assertEqual(len(result["data"]["list"]), 0)

        # 筛选version
        result = self.client.get(
            path="/api/agent/package/",
            data={"page": 1, "pagesize": 2, "version": gse_package.version, "project": "gse_proxy"},
        )
        self.assertEqual(len(result["data"]["list"]), 1)
        self.assertEqual(result["data"]["list"][0]["version"], "1.0.1")
        result = self.client.get(
            path="/api/agent/package/", data={"page": 1, "pagesize": 2, "version": "1.0.2", "project": "gse_proxy"}
        )
        self.assertEqual(len(result["data"]["list"]), 0)

    @classmethod
    def collect_all_tag_names(cls, tags, *args, **kwargs):
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
                        {"id": "linux_x86_64", "name": "Linux_x86_64", "count": 1, "description": "### 1.0.1\nchange"},
                    ],
                )
                self.assertEqual(condition["count"], 1)

            elif condition["id"] == "version":
                self.assertCountEqual(
                    condition["children"],
                    [
                        {"id": "1.0.1", "name": "1.0.1", "count": 1, "description": "### 1.0.1\nchange"},
                    ],
                )
                self.assertEqual(condition["count"], 1)

    @patch("apps.node_man.permissions.package_manage.PackageManagePermission.has_permission", return_value=True)
    def test_filter_condition_with_agent_pkg_manage(self, *args, **kwargs):
        result = MetaHandler().filter_condition("agent_pkg_manage", params={"project": "gse_proxy"})
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
                        {"id": "stable", "name": "稳定版本"},
                        {"id": "latest", "name": "最新版本"},
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

    @patch("apps.node_man.permissions.package_manage.PackageManagePermission.has_permission", return_value=True)
    def test_deployed_hosts_count(self, *args, **kwargs):
        data = {
            "items": [{"os_type": "linux", "cpu_arch": "x86_64"}, {"os_type": "windows", "cpu_arch": "x86_64"}],
            "project": "gse_agent",
        }

        # 100台主机都是LINUX，cpu_arch都为x86_64
        Host.objects.all().delete()
        ProcessStatus.objects.all().delete()
        create_host(100, os_type=constants.OsType.LINUX, node_type=constants.NodeType.AGENT)
        result = self.client.post(path="/api/agent/package/deployed_hosts_count/", data=data)
        self.assertEqual(
            result["data"],
            [
                {"os_type": "linux", "cpu_arch": "x86_64", "count": 100},
                {"os_type": "windows", "cpu_arch": "x86_64", "count": 0},
            ],
        )

        # 100台主机都是WINDOWS，cpu_arch都为x86_64
        Host.objects.all().delete()
        ProcessStatus.objects.all().delete()
        create_host(100, os_type=constants.OsType.WINDOWS, node_type=constants.NodeType.AGENT, start_idx=100)
        result = self.client.post(path="/api/agent/package/deployed_hosts_count/", data=data)
        self.assertEqual(
            result["data"],
            [
                {"os_type": "linux", "cpu_arch": "x86_64", "count": 0},
                {"os_type": "windows", "cpu_arch": "x86_64", "count": 100},
            ],
        )

        # 50台主机是WINDOWS，50台主机是LINUX，cpu_arch都为x86_64
        Host.objects.all().delete()
        ProcessStatus.objects.all().delete()
        create_host(50, os_type=constants.OsType.WINDOWS, node_type=constants.NodeType.AGENT, start_idx=200)
        create_host(50, os_type=constants.OsType.LINUX, node_type=constants.NodeType.AGENT, start_idx=250)
        result = self.client.post(path="/api/agent/package/deployed_hosts_count/", data=data)
        self.assertEqual(
            result["data"],
            [
                {"os_type": "linux", "cpu_arch": "x86_64", "count": 50},
                {"os_type": "windows", "cpu_arch": "x86_64", "count": 50},
            ],
        )

    @patch("apps.node_man.permissions.package_manage.PackageManagePermission.has_permission", return_value=True)
    def test_upload(self, *args, **kwargs):
        self.assertEqual(UploadPackage.objects.count(), 1)
        upload_package = UploadPackage.objects.first()
        self.assertEqual(upload_package.module, "agent")
        self.assertEqual(upload_package.file_path, self.storage_path)
        self.assertEqual(upload_package.md5, self.md5)
        self.assertEqual(upload_package.file_name, self.file_name)

    @patch("apps.node_man.permissions.package_manage.PackageManagePermission.has_permission", return_value=True)
    def test_parse(self, *args, **kwargs):
        res = self.client.post(
            path="/backend/api/agent/parse/",
            data={
                "file_name": self.file_name,
            },
        )
        self.assertEqual(res["result"], True)
        self.assertIn("description", res["data"])
        self.assertIn("packages", res["data"])

        for packages in res["data"]["packages"]:
            self.assertIn(packages["os"].upper(), OS_TYPE.values())
            self.assertIn(packages["project"], GsePackageCode.get_member_value__alias_map())
            self.assertIn(packages["cpu_arch"], CPU_TUPLE)

    @patch("apps.node_man.permissions.package_manage.PackageManagePermission.has_permission", return_value=True)
    @patch("apps.backend.sync_task.manager.AsyncTaskManager.delay", delay)
    def test_create_register_task(self, *args, **kwargs):
        file_name = kwargs.get("file_name") if "file_name" in kwargs else self.file_name
        task_id = str(uuid.uuid4())
        self.task_map[task_id] = "PENDING"

        res = self.client.post(
            path="/backend/api/sync_task/create/",
            data={
                "task_name": SyncTaskType.REGISTER_GSE_PACKAGE.value,
                "task_params": {
                    "file_name": file_name,
                    "tags": [],
                },
            },
        )
        if res["result"] is True:
            self.task_map[task_id] = "SUCCESS"
            self.assertIn("task_id", res["data"])
        else:
            self.task_map[task_id] = "FAILURE"

        return task_id

    @patch("apps.node_man.permissions.package_manage.PackageManagePermission.has_permission", return_value=True)
    @patch("apps.backend.sync_task.manager.AsyncTaskManager.delay", delay)
    def test_query_register_task(self, *args, **kwargs):
        task_id = self.test_create_register_task()
        self.assertEqual(self.task_map[task_id], "SUCCESS")

        wrong_task_id = self.test_create_register_task(file_name=self.file_name + "...")
        self.assertEqual(self.task_map[wrong_task_id], "FAILURE")
