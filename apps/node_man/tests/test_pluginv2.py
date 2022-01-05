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

from django.core.cache import cache

from apps.node_man import constants, models
from apps.node_man.handlers.plugin_v2 import PluginV2Handler
from apps.node_man.tests.utils import NodeApi, cmdb_or_cache_biz, create_host
from apps.utils.unittest.testcase import CustomBaseTestCase


def upload_package_return(url, data, files):
    class response:
        content = (
            '{"result": true, "message": "", "code": "00", "data": '
            '{"id": 21, "name": "test-0.01.tgz", "pkg_size": "23412434"}}'
        )

    return response


def mock_batch_call(func, params_list, get_data):
    """
    mock掉并发接口为单线程接口
    并发接口会出现测试数据丢失情况
    """
    result = []
    for params in params_list:
        result.append(get_data(func(**params)))

    return result


class TesetPluginV2(CustomBaseTestCase):
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

    @patch("common.api.NodeApi.create_subscription", NodeApi.create_subscription)
    @patch("apps.node_man.handlers.permission.IamHandler.is_superuser", lambda x: True)
    def test_operate(self):
        job_type = constants.JobType.MAIN_INSTALL_PLUGIN
        plugin = "exceptionbeat"
        scope = {"nodes": [{"bk_biz_id": 1}, {"bk_biz_id": 2}]}
        steps = [{"id": "exceptionbeat", "type": "PLUGIN", "configs": {}, "params": {}}]

        result = PluginV2Handler().operate(job_type, plugin, scope, steps)["param"]
        self.assertEqual(result["plugin_name"], plugin)
        self.assertEqual(result["steps"][0]["config"]["job_type"], job_type)

        job_type = constants.JobType.MAIN_DELEGATE_PLUGIN
        result = PluginV2Handler().operate(job_type, plugin, scope, steps)["param"]
        self.assertEqual(result["plugin_name"], plugin)
        self.assertEqual(result["steps"][0]["config"]["job_type"], job_type)

    @patch("apps.node_man.handlers.plugin_v2.batch_call", mock_batch_call)
    def test_fetch_package_deploy_info(self):
        host_num = 10
        create_host(host_num)

        # 验证是否拿到正确的插件包部署信息
        models.ProcessStatus.objects.all().update(is_latest=True)
        result = PluginV2Handler().fetch_package_deploy_info(["gseagent"], ["project"] + ["os"])
        nodes_num = sum([node["nodes_number"] for key, node in result.items()])
        self.assertEqual(nodes_num, host_num)

        # 验证cache是否成功缓存
        cache_deploy_number_template = "plugin_v2:fetch_package_deploy_info:{project}:{keys_combine_str}"
        result = cache.get(cache_deploy_number_template.format(project="gseagent", keys_combine_str="project|os"))
        nodes_num = sum([node_num for key, node_num in result.items()])
        self.assertEqual(nodes_num, host_num)
