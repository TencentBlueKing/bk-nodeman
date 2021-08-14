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
from unittest.mock import patch

from django.test import TestCase

from apps.node_man import constants, models
from apps.node_man.handlers.plugin_v2 import PluginV2Handler
from apps.node_man.tests.utils import NodeApi, cmdb_or_cache_biz, create_host


def upload_package_return(url, data, files):
    class response:
        content = (
            '{"result": true, "message": "", "code": "00", "data": '
            '{"id": 21, "name": "test-0.01.tgz", "pkg_size": "23412434"}}'
        )

    return response


class TesetPluginV2(TestCase):
    @patch("common.api.NodeApi.plugin_list", NodeApi.plugin_list)
    def test_list_plugin(self):
        process_to_create = []
        for i in range(0, 100):
            process_to_create.append(
                models.ProcessStatus(
                    bk_host_id=i, name="basereport", source_type=models.ProcessStatus.SourceType.DEFAULT, is_latest=True
                )
            )
        # bulk_create创建进程状态
        models.ProcessStatus.objects.bulk_create(process_to_create)

        page_size = 10
        result = PluginV2Handler().list_plugin(
            {
                "search": "",
                "pagesize": page_size,
                "page": 1,
            }
        )
        self.assertEqual(
            result,
            {
                "total": 1,
                "list": [
                    {
                        "id": 1,
                        "description": "系统基础信息采集",
                        "name": "basereport",
                        "category": "官方插件",
                        "source_app_code": "bk_nodeman",
                        "scenario": "CMDB上的实时数据，蓝鲸监控里的主机监控，包含CPU，内存，磁盘等",
                        "deploy_type": "整包部署",
                        "permissions": {"operate": True},
                    }
                ],
            },
        )

    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    def test_list_plugin_host(self):
        # 构造数据
        number = 100
        create_host(number)
        process_to_create = []
        for i in range(0, number):
            process_to_create.append(
                models.ProcessStatus(
                    bk_host_id=i,
                    name="basereport",
                    proc_type=constants.ProcType.PLUGIN,
                    source_type=models.ProcessStatus.SourceType.DEFAULT,
                    is_latest=True,
                )
            )
        # bulk_create创建进程状态
        models.ProcessStatus.objects.bulk_create(process_to_create)

        result = PluginV2Handler().list_plugin_host(params={"project": "basereport", "page": 1, "pagesize": -1})
        self.assertEqual(result["total"], number)

    def test_fetch_config_variables(self):
        models.PluginConfigTemplate.objects.create(
            id=1, is_release_version=True, name="test", version="1.0", creator="admin", content="content"
        )
        result = PluginV2Handler().fetch_config_variables(config_tpl_ids=[1])
        self.assertEqual(
            result,
            [
                {
                    "id": 1,
                    "name": "test",
                    "version": "1.0",
                    "is_main": False,
                    "creator": "admin",
                    "variables": {"type": "object", "properties": {}},
                }
            ],
        )

    @patch("common.api.NodeApi.plugin_history", NodeApi.plugin_history)
    def test_history(self):
        result = PluginV2Handler().history(query_params={"os": "linux", "cpu_arch": "x86", "pkg_ids": [1]})
        self.assertEqual(
            result,
            [
                {
                    "id": 1,
                    "pkg_name": "basereport-1.0.tgz",
                    "project": "basereport",
                    "version": "1.0",
                    "os": "linux",
                    "cpu_arch": "x86",
                    "nodes_number": 0,
                },
                {
                    "id": 2,
                    "pkg_name": "basereport-1.1.tgz",
                    "module": "gse_plugin",
                    "project": "basereport",
                    "version": "1.1",
                    "os": "linux",
                    "cpu_arch": "x86",
                    "nodes_number": 0,
                },
            ],
        )
