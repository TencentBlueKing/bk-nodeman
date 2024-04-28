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
import typing

import mock

from apps.backend.tests.components.collections.plugin import utils
from apps.node_man import models
from apps.utils.unittest.testcase import CustomAPITestCase


class DebugPluginTestCase(utils.PluginTestObjFactory, CustomAPITestCase):

    INSTANCE_ID = 1

    def setUp(self):
        self.ids: typing.Dict[str, int] = self.init_db()
        self.plugin_id: int = models.Packages.objects.get(project=utils.PKG_PROJECT_NAME).id
        self.start_debug_path: str = "/backend/api/plugin/start_debug/"
        self.host_obj: models.Host = models.Host.objects.get(bk_host_id=self.ids["bk_host_id"])

        service_instance_result: typing.List[typing.Dict[str, typing.Union[str, int]]] = [
            {
                "bk_biz_id": utils.DEFAULT_BIZ_ID_NAME["bk_biz_id"],
                "id": self.INSTANCE_ID,
                "name": "127.0.0.1_bash",
                "labels": "",
                "bk_host_id": self.host_obj.bk_host_id,
                "creator": "admin",
                "modifier": "admin",
                "create_time": "2022-12-15T09:57:56.764Z",
                "last_time": "2022-12-15T09:57:56.764Z",
                "bk_supplier_account": "0",
            }
        ]

        mock.patch("apps.backend.plugin.views.get_service_instances", return_value=service_instance_result).start()

    def test_host_info_debug(self):
        base_host_info_data: typing.Dict[str, typing.Union[str, int]] = {
            "bk_username": "admin",
            "bk_app_code": "bk_nodeman",
            "plugin_id": self.plugin_id,
            "config_ids": [],
            "object_type": models.Subscription.ObjectType.HOST,
            "node_type": models.Subscription.NodeType.INSTANCE,
        }
        host_id_info: typing.Dict[str, typing.Dict[str, typing.Union[str, int]]] = {
            "host_info": {
                "bk_host_id": self.ids["bk_host_id"],
                "bk_supplier_id": 0,
                "bk_biz_id": utils.DEFAULT_BIZ_ID_NAME["bk_biz_id"],
            }
        }

        host_id_debug_result: typing.Dict[str, str] = self.client.post(
            path=self.start_debug_path,
            data={**base_host_info_data, **host_id_info},
        )

        without_host_id_info: typing.Dict[str, typing.Dict[str, typing.Union[str, int]]] = {
            "host_info": {
                "ip": self.host_obj.inner_ip,
                "bk_cloud_id": self.host_obj.bk_cloud_id,
                "bk_supplier_id": 0,
                "bk_biz_id": utils.DEFAULT_BIZ_ID_NAME["bk_biz_id"],
            }
        }

        without_host_id_debug_result: typing.Dict[str, str] = self.client.post(
            path=self.start_debug_path,
            data={**base_host_info_data, **without_host_id_info},
        )

        self.assertTrue(host_id_debug_result["result"])
        self.assertTrue(without_host_id_debug_result["result"])

    def test_instance_info_debug(self):
        base_instance_info_data: typing.Dict[str, typing.Union[str, int]] = {
            "bk_username": "admin",
            "bk_app_code": "bk_nodeman",
            "plugin_id": self.plugin_id,
            "config_ids": [],
            "object_type": models.Subscription.ObjectType.SERVICE,
            "node_type": models.Subscription.NodeType.INSTANCE,
        }

        plugin_id_info: typing.Dict[str, int] = {"plugin_id": self.plugin_id}

        instance_info: typing.Dict[str, typing.Dict[str, typing.Union[str, int]]] = {
            "instance_info": {"bk_biz_id": utils.DEFAULT_BIZ_ID_NAME["bk_biz_id"], "id": self.INSTANCE_ID}
        }

        instance_debug_result: typing.Dict[str, str] = self.client.post(
            path=self.start_debug_path, data={**base_instance_info_data, **instance_info, **plugin_id_info}
        )

        plugin_info: typing.Dict[str, str] = {
            "plugin_name": utils.PKG_PROJECT_NAME,
            "version": utils.PKG_INFO["version"],
        }

        instance_debug_without_plugin_id_result: typing.Dict[str, str] = self.client.post(
            path=self.start_debug_path, data={**base_instance_info_data, **instance_info, **plugin_info}
        )
        self.assertTrue(instance_debug_result["result"])
        self.assertTrue(instance_debug_without_plugin_id_result["result"])
