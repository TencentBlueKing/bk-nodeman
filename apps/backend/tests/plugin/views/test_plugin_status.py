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

from apps.backend.tests.plugin import utils
from apps.node_man import constants, models
from apps.utils.unittest.testcase import CustomAPITestCase


class PluginStatusTestCase(CustomAPITestCase):
    def setUp(self):

        # 设置请求附加参数
        self.client.common_request_data = {
            "bk_app_code": settings.APP_CODE,
            "bk_username": settings.SYSTEM_USE_API_ACCOUNT,
        }

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
        response = self.client.post(
            path="/backend/api/plugin/release/",
            data={
                "id": [pkg_objs[0].id, pkg_objs[1].id],
                "md5_list": ["456", "123"],
            },
        )
        self.assertEquals(response["data"], [pkg_objs[0].id, pkg_objs[1].id])
        self.assertEquals(models.Packages.objects.filter(id__in=response["data"], is_release_version=True).count(), 2)

        models.Packages.objects.all().update(is_release_version=False)

        response = self.client.post(
            path="/backend/api/plugin/release/",
            data={
                "md5_list": ["456"],
                "version": "1.0.1",
                "name": utils.PLUGIN_NAME,
            },
        )
        self.assertEquals(response["data"], [pkg_objs[1].id])
        # 切换操作人
        self.assertTrue(models.Packages.objects.get(id=pkg_objs[1].id).is_release_version)

        # 测试未启用状态下不允许上下线变更
        pkg_objs.update(is_ready=False, is_release_version=True)

        response = self.client.post(
            path="/backend/api/plugin/release/",
            data={
                "id": [pkg_objs[0].id, pkg_objs[1].id],
                "operation": constants.PkgStatusOpType.offline,
                "md5_list": ["123", "456"],
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
            response = self.client.post(
                path="/backend/api/plugin/package_status_operation/",
                data={"id": [pkg_objs[0].id, pkg_objs[1].id], "operation": op, "md5_list": ["123", "456"]},
            )
            self.assertEquals(response["data"], [pkg_objs[0].id, pkg_objs[1].id])

        self.assertEquals(
            models.Packages.objects.filter(
                id__in=[pkg_objs[0].id, pkg_objs[1].id], is_release_version=True, is_ready=True
            ).count(),
            2,
        )

        # 下线1.0.0
        response = self.client.post(
            path="/backend/api/plugin/package_status_operation/",
            data={
                "name": utils.PLUGIN_NAME,
                "version": "1.0.0",
                "operation": constants.PkgStatusOpType.offline,
                "md5_list": ["123"],
            },
        )
        self.assertEquals(response["data"], [pkg_objs[0].id])
        # 状态操作人刷新
        pkg_obj = models.Packages.objects.get(id=pkg_objs[0].id)
        self.assertFalse(pkg_obj.is_release_version)
        self.assertTrue(pkg_obj.is_ready)

    def test_plugin_status_op(self):
        gse_plugin_objs = models.GsePluginDesc.objects.all()
        op_order = [
            constants.PluginStatusOpType.stop,
            constants.PluginStatusOpType.ready,
        ]
        for op in op_order:
            response = self.client.post(
                path="/backend/api/plugin/plugin_status_operation/",
                data={"operation": op, "id": [gse_plugin_objs[0].id]},
            )
            self.assertEquals(response["data"], [gse_plugin_objs[0].id])
        self.assertTrue(models.GsePluginDesc.objects.filter(id=gse_plugin_objs[0].id, is_ready=True).exists())
