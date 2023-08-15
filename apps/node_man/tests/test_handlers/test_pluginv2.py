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

import mock
from django.core.cache import cache

from apps.mock_data import api_mkd, common_unit, utils
from apps.node_man import constants, models, tools
from apps.node_man.handlers.plugin_v2 import PluginV2Handler
from apps.node_man.tests.utils import MockClient, NodeApi, create_host
from apps.utils import basic
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


class TestPluginV2(CustomBaseTestCase):
    def init_mock_clients(self):
        self.cmdb_mock_client = api_mkd.cmdb.utils.CMDBMockClient(
            find_host_by_service_template_return=utils.MockReturn(
                return_type=utils.MockReturnType.RETURN_VALUE.value,
                return_obj={"count": 3, "info": [{"bk_host_id": 1}, {"bk_host_id": 2}, {"bk_host_id": 3}]},
            )
        )

    def setUp(self) -> None:
        self.init_mock_clients()
        mock.patch("apps.node_man.handlers.plugin_v2.client_v2", self.cmdb_mock_client).start()
        super().setUp()

    @staticmethod
    def init_process_statuses(number=100):
        process_to_create = []
        for bk_host_id in range(0, number):
            process_to_create.append(
                models.ProcessStatus(
                    bk_host_id=bk_host_id,
                    name="basereport",
                    source_type=models.ProcessStatus.SourceType.DEFAULT,
                    proc_type=constants.ProcType.PLUGIN,
                    is_latest=True,
                    status=(constants.ProcStateType.TERMINATED, constants.ProcStateType.RUNNING)[bk_host_id % 2],
                )
            )
        # bulk_create创建进程状态
        models.ProcessStatus.objects.bulk_create(process_to_create)

    @patch("common.api.NodeApi.plugin_list", NodeApi.plugin_list)
    def test_list_plugin(self):
        self.init_process_statuses()

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

    def test_fetch_config_variables(self):
        models.PluginConfigTemplate.objects.create(
            id=1,
            is_release_version=True,
            name="test",
            version="1.0",
            creator="admin",
            content="content",
            variables="variables",
        )
        result = PluginV2Handler().fetch_config_variables(config_tpl_ids=[1])
        self.assertEqual(
            result,
            [{
                "id": 1,
                "name": "test",
                "version": "1.0",
                "is_main": False,
                "creator": "admin",
                "content": "content",
                "variables": "variables",
            }],
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

    @patch("common.api.NodeApi.create_subscription", NodeApi.create_subscription)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    @patch("apps.node_man.handlers.permission.IamHandler.is_superuser", lambda x: True)
    def test_resource_policy(self):
        self.init_process_statuses()
        bk_biz_id = 2
        has_been_set_service_template = 1
        non_set_service_template = 2
        result = PluginV2Handler.set_resource_policy(
            bk_biz_id,
            constants.CmdbObjectId.SERVICE_TEMPLATE,
            has_been_set_service_template,
            [
                {"plugin_name": "bkmonitorbeat", "cpu": 10, "mem": 20},
                {"plugin_name": "bkunifylogbeat", "cpu": 30, "mem": 10},
                {
                    "plugin_name": "basereport",
                    "cpu": constants.PLUGIN_DEFAULT_CPU_LIMIT,
                    "mem": constants.PLUGIN_DEFAULT_MEM_LIMIT,
                },
            ],
        )
        self.assertEqual(len(result["job_id_list"]), 2)

        # 非默认资源配额
        resource_policy = PluginV2Handler.fetch_resource_policy(
            bk_biz_id, constants.CmdbObjectId.SERVICE_TEMPLATE, has_been_set_service_template
        )
        self.assertFalse(resource_policy["is_default"])
        for policy in resource_policy["resource_policy"]:
            if policy["plugin_name"] == "bkmonitorbeat":
                self.assertEqual(policy["cpu"], 10)
                self.assertEqual(policy["mem"], 20)
            elif policy["plugin_name"] == "bkunifylogbeat":
                self.assertEqual(policy["cpu"], 30)
                self.assertEqual(policy["mem"], 10)
            else:
                self.assertEqual(policy["cpu"], constants.PLUGIN_DEFAULT_CPU_LIMIT)
                self.assertEqual(policy["mem"], constants.PLUGIN_DEFAULT_MEM_LIMIT)

        # 默认资源配额
        resource_policy = PluginV2Handler.fetch_resource_policy(
            bk_biz_id, constants.CmdbObjectId.SERVICE_TEMPLATE, non_set_service_template
        )
        self.assertTrue(resource_policy["is_default"])
        for policy in resource_policy["resource_policy"]:
            self.assertEqual(policy["cpu"], constants.PLUGIN_DEFAULT_CPU_LIMIT)
            self.assertEqual(policy["mem"], constants.PLUGIN_DEFAULT_MEM_LIMIT)

        resource_policy_status = PluginV2Handler.fetch_resource_policy_status(
            bk_biz_id, constants.CmdbObjectId.SERVICE_TEMPLATE
        )
        self.assertEqual(
            resource_policy_status,
            [
                {"bk_inst_id": has_been_set_service_template, "is_default": False},
                {"bk_inst_id": non_set_service_template, "is_default": True},
            ],
        )

    def test_create_config_template(self):
        pkg_obj = models.Packages.objects.create(
            **basic.remove_keys_from_dict(origin_data=common_unit.plugin.PACKAGES_MODEL_DATA, keys=["id"])
        )
        self.client.post(
            path="/backend/api/plugin/create_config_template/",
            data={
                "bk_username": "admin",
                "bk_app_code": "blueking",
                "plugin_name": pkg_obj.project,
                "plugin_version": pkg_obj.version,
                "name": "env.yaml",
                "file_path": "etc",
                "format": "yaml",
                "content": "R1NFX0FHRU5UX0hPTUU6IHt7IGNvbnRyb2xfaW5mby5nc2VfYWdlbnRfaG9tZSB9fQpCS19QTFVHSU5fTE9HX1B"
                "BVEg6IHt7IGNvbnRyb2xfaW5mby5sb2dfcGF0aCB9fQpCS19QTFVHSU5fUElEX1BBVEg6IHt7IGNvbnRyb2xfaW"
                "5mby5waWRfcGF0aCB9fQoKCgpCS19DTURfQVJHUzoge3sgY21kX2FyZ3MgfX0=",
                "md5": "49a11211fa91dd7fee4fed3fcefc5919",
                "version": "1",
                "is_release_version": False,
            },
        )
        template_num = models.PluginConfigTemplate.objects.filter(plugin_name=pkg_obj.project).count()
        self.assertEqual(template_num, len(constants.CPU_CHOICES) * len(constants.OS_CHOICES))

    def test_head_plugins_change_case(self):
        mock_plugins_name = "processbeat"
        models.GsePluginDesc.objects.update_or_create(
            name=mock_plugins_name,
            description="description",
            source_app_code="nodeman",
            category=constants.CategoryType.official,
            auto_launch=True,
        )

        self.assertEqual(tools.PluginV2Tools.fetch_head_plugins(), [mock_plugins_name])

        models.GsePluginDesc.objects.filter(name=mock_plugins_name).delete()
        # 没有可用插件时，返回全部
        self.assertEqual(tools.PluginV2Tools.fetch_head_plugins(), constants.HEAD_PLUGINS)
