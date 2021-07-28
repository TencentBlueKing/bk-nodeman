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
import json

from django.test import Client, TestCase
from django.test.client import MULTIPART_CONTENT

from apps.backend.tests.plugin import utils
from apps.node_man import constants, models


class TestApiBase(TestCase):
    test_client = Client()

    def success_assert(self, response):
        response_data = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response_data["result"])
        return response_data

    def get(self, path, data=None, follow=False, secure=False, success_assert=True, **extra):
        response = self.test_client.get(path, data, follow, secure, **extra)
        return self.success_assert(response)

    def post(
        self,
        path,
        data=None,
        content_type=MULTIPART_CONTENT,
        follow=False,
        secure=False,
        success_assert=True,
        is_json=True,
        **extra
    ):
        # 默认用json格式
        if is_json:
            content_type = "application/json"
            data = json.dumps(data) if isinstance(data, dict) else data
        response = self.test_client.post(path, data, content_type, follow, secure, **extra)
        if success_assert:
            return self.success_assert(response)
        else:
            return json.loads(response.content)


class TestPkgStatusChange(TestApiBase):
    def setUp(self):
        utils.PluginTestObjFactory.batch_create_plugin_desc([utils.PluginTestObjFactory.gse_plugin_desc_obj()])
        utils.PluginTestObjFactory.batch_create_pkg(
            [
                utils.PluginTestObjFactory.pkg_obj(
                    {"pkg_name": "test_plugin-1.0.0.tgz", "version": "1.0.0", "md5": "123"}
                ),
                utils.PluginTestObjFactory.pkg_obj(
                    {"pkg_name": "test_plugin-1.0.1.tgz", "version": "1.0.1", "md5": "456"}
                ),
            ]
        )
        models.Packages.objects.all().update(is_release_version=False)

    def test_pkg_release(self):
        pkg_objs = models.Packages.objects.all()
        response = self.post(
            path="/backend/api/plugin/release/",
            data={
                "id": [pkg_objs[0].id, pkg_objs[1].id],
                "md5_list": ["456", "123"],
                "bk_app_code": "test",
                "bk_username": "admin",
            },
        )
        self.assertEquals(response["data"], [pkg_objs[0].id, pkg_objs[1].id])
        self.assertEquals(models.Packages.objects.filter(id__in=response["data"], is_release_version=True).count(), 2)

        models.Packages.objects.all().update(is_release_version=False)

        response = self.post(
            path="/backend/api/plugin/release/",
            data={
                "md5_list": ["456"],
                "bk_app_code": "test",
                "bk_username": "test_person",
                "version": "1.0.1",
                "name": utils.DEFAULT_PLUGIN_NAME,
            },
        )
        self.assertEquals(response["data"], [pkg_objs[1].id])
        # 切换操作人
        self.assertTrue(models.Packages.objects.get(id=pkg_objs[1].id, creator="test_person").is_release_version)

        # 测试未启用状态下不允许上下线变更
        pkg_objs.update(is_ready=False, is_release_version=True)

        response = self.post(
            path="/backend/api/plugin/release/",
            data={
                "id": [pkg_objs[0].id, pkg_objs[1].id],
                "operation": constants.PkgStatusOpType.offline,
                "md5_list": ["123", "456"],
                "bk_app_code": "test",
                "bk_username": "admin",
            },
            success_assert=False,
        )
        self.assertEquals(
            response["message"], "ID{ids}的插件包未启用，无法执行更改状态操作（3802005）".format(ids=[pkg_objs[0].id, pkg_objs[1].id])
        )

    def test_pkg_status_op(self):
        pkg_objs = models.Packages.objects.all()
        op_order = [
            constants.PkgStatusOpType.stop,
            # constants.PkgStatusOpType.ready,
            constants.PkgStatusOpType.offline,
            constants.PkgStatusOpType.release,
        ]
        for op in op_order:
            response = self.post(
                path="/backend/api/plugin/package_status_operation/",
                data={
                    "id": [pkg_objs[0].id, pkg_objs[1].id],
                    "operation": op,
                    "md5_list": ["123", "456"],
                    "bk_app_code": "test",
                    "bk_username": "admin",
                },
            )
            self.assertEquals(response["data"], [pkg_objs[0].id, pkg_objs[1].id])

        self.assertEquals(
            models.Packages.objects.filter(
                id__in=[pkg_objs[0].id, pkg_objs[1].id], is_release_version=True, is_ready=True
            ).count(),
            2,
        )

        # 下线1.0.0
        response = self.post(
            path="/backend/api/plugin/package_status_operation/",
            data={
                "name": utils.DEFAULT_PLUGIN_NAME,
                "version": "1.0.0",
                "operation": constants.PkgStatusOpType.offline,
                "md5_list": ["123"],
                "bk_app_code": "test",
                "bk_username": "test_person",
            },
        )
        self.assertEquals(response["data"], [pkg_objs[0].id])
        # 状态操作人刷新
        pkg_obj = models.Packages.objects.get(id=pkg_objs[0].id, creator="test_person")
        self.assertFalse(pkg_obj.is_release_version)
        self.assertTrue(pkg_obj.is_ready)

    def test_plugin_status_op(self):
        gse_plugin_objs = models.GsePluginDesc.objects.all()
        op_order = [
            constants.PluginStatusOpType.stop,
            constants.PluginStatusOpType.ready,
        ]
        for op in op_order:
            response = self.post(
                path="/backend/api/plugin/plugin_status_operation/",
                data={"operation": op, "id": [gse_plugin_objs[0].id], "bk_app_code": "test", "bk_username": "admin"},
            )
            self.assertEquals(response["data"], [gse_plugin_objs[0].id])
        self.assertTrue(models.GsePluginDesc.objects.filter(id=gse_plugin_objs[0].id, is_ready=True).exists())
