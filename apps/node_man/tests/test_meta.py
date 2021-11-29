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
import random
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase

from apps.node_man import constants as const
from apps.node_man import tools
from apps.node_man.handlers.meta import MetaHandler
from apps.node_man.models import Cloud, GlobalSettings, Host, Job, ProcessStatus
from apps.node_man.tests.utils import (
    SEARCH_BUSINESS,
    MockClient,
    cmdb_or_cache_biz,
    create_cloud_area,
    create_host,
    create_job,
)


class TestMeta(TestCase):
    def fetch_host_unique_col_count(self, col):
        """
        返回Host中指定列的唯一值
        :param col: 列名
        :return: 唯一值得数量
        """
        host_condition = (
            Host.objects.filter(node_type__in=[const.NodeType.AGENT, const.NodeType.PAGENT])
            .extra(
                select={
                    "status": f"{ProcessStatus._meta.db_table}.status",
                    "version": f"{ProcessStatus._meta.db_table}.version",
                },
                tables=[ProcessStatus._meta.db_table],
            )
            .values_list(col, flat=True)
            .distinct()
        )
        return set(host_condition)

    def fetch_cloud_unique_col_count(self, col):
        """
        返回Cloud中指定列的唯一值
        :param col: 列名
        :return: 唯一值得数量
        """
        return Cloud.objects.values_list(col, flat=True).distinct().count()

    def fetch_Job_unique_col_count(self):
        """
        返回Job中指定列的唯一值
        :return: 唯一值的数量
        """
        # 获得4列的所有值
        job_condition = list(Job.objects.values("created_by", "job_type", "status", "bk_biz_scope").distinct())

        # 初始化各个条件集合
        created_bys = set()
        job_types = set()
        statuses = set()

        for job in job_condition:
            # 判断权限
            if set(job["bk_biz_scope"]) - {biz["bk_biz_id"] for biz in SEARCH_BUSINESS} == set():
                created_bys.add(job["created_by"])
                job_types.add(job["job_type"])
                statuses.add(job["status"])

        return created_bys, job_types, statuses

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_search(self):
        # 服务商搜索接口
        isp_list = [
            {"isp": "Amazon", "isp_icon": "", "isp_name": "AWS"},
            {"isp": "MicroSoft", "isp_icon": "", "isp_name": "Azure"},
            {"isp": "Google", "isp_icon": "", "isp_name": "GCP"},
            {"isp": "SalesForce", "isp_icon": "", "isp_name": "SalesForce"},
            {"isp": "Oracle", "isp_icon": "", "isp_name": "Oracle Cloud"},
            {"isp": "IBM", "isp_icon": "", "isp_name": "IBM Cloud"},
            {"isp": "Aliyun", "isp_icon": "", "isp_name": "阿里云"},
            {"isp": "Tencent", "isp_icon": "", "isp_name": "腾讯云"},
            {"isp": "ECloud", "isp_icon": "", "isp_name": "中国电信"},
            {"isp": "UCloud", "isp_icon": "", "isp_name": "UCloud"},
            {"isp": "MOS", "isp_icon": "", "isp_name": "美团云"},
            {"isp": "KSCLOUD", "isp_icon": "", "isp_name": "金山云"},
            {"isp": "baidu", "isp_icon": "", "isp_name": "百度云"},
            {"isp": "capitalonline", "isp_icon": "", "isp_name": "首都云"},
        ]
        gs = GlobalSettings(key="isp", v_json=isp_list)
        gs.save()
        settings = MetaHandler().search("isp")
        self.assertListEqual(settings["isp"], isp_list)

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_filter_condition(self):
        # Host表头接口
        number = 100
        create_cloud_area(number)
        create_job(number)
        create_host(number, node_type="AGENT")
        # 测试
        filter_condition = MetaHandler().filter_condition("host")
        id__filter_item_map = {filter_item["id"]: filter_item for filter_item in filter_condition}

        os_types = {child["id"] for child in id__filter_item_map["os_type"]["children"] if child["id"] != "none"}
        statuses = {child["id"] for child in id__filter_item_map["status"]["children"]}
        versions = {child["id"] for child in id__filter_item_map["version"]["children"]}

        self.assertEqual(os_types, self.fetch_host_unique_col_count("os_type"))
        self.assertEqual(statuses, self.fetch_host_unique_col_count("status"))
        self.assertEqual(versions, self.fetch_host_unique_col_count("version"))

        filter_condition = MetaHandler().filter_condition("job")
        id__filter_item_map = {filter_item["id"]: filter_item for filter_item in filter_condition}

        api_statuses = {child["id"] for child in id__filter_item_map["status"]["children"]}
        api_op_types = {child["id"] for child in id__filter_item_map["op_type"]["children"]}
        api_step_types = {child["id"] for child in id__filter_item_map["step_type"]["children"]}
        api_created_bys = {child["id"] for child in id__filter_item_map["created_by"]["children"]}

        created_bys, job_types, statuses = self.fetch_Job_unique_col_count()

        job_type_infos = [tools.JobTools.unzip_job_type(job_type) for job_type in job_types]

        self.assertEqual(id__filter_item_map["job_id"], {"name": "任务ID", "id": "job_id"})
        self.assertEqual(api_op_types, {job_type_info["op_type"] for job_type_info in job_type_infos})
        self.assertEqual(api_step_types, {job_type_info["step_type"] for job_type_info in job_type_infos})
        self.assertEqual(api_created_bys, created_bys)
        self.assertEqual(api_statuses, statuses)

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_fetch_plugin_list_condition(self):
        # 插件表头接口
        number = 100
        create_cloud_area(number)
        create_job(number)
        host_to_create, _, _ = create_host(number)
        process_to_create = []
        for host in host_to_create:
            process_to_create.append(
                ProcessStatus(
                    bk_host_id=host.bk_host_id,
                    proc_type=const.ProcType.PLUGIN,
                    version=f"{random.randint(1, 10)}",
                    name=settings.HEAD_PLUGINS[random.randint(0, len(settings.HEAD_PLUGINS) - 1)],
                    status="RUNNING",
                )
            )
        # 测试
        MetaHandler().filter_condition("plugin")

    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    @patch("apps.node_man.handlers.cmdb.get_request_username", return_value="special_test")
    def test_fetch_plugin_list_condition_no_permission(self, *args, **kwargs):
        self.maxDiff = None
        # 插件表头接口
        number = 100
        create_cloud_area(number)
        create_job(number)
        host_to_create, _, _ = create_host(number)
        process_to_create = []
        for host in host_to_create:
            process_to_create.append(
                ProcessStatus(
                    bk_host_id=host.bk_host_id,
                    proc_type=const.ProcType.PLUGIN,
                    version=f"{random.randint(1, 10)}",
                    name=settings.HEAD_PLUGINS[random.randint(0, len(settings.HEAD_PLUGINS) - 1)],
                    status="RUNNING",
                )
            )

        default_cloud_num = 1
        generated_cloud_area_num = 100
        total_cloud_num = default_cloud_num + generated_cloud_area_num

        result = MetaHandler().filter_condition("plugin_host")
        self.assertEqual(result[0], {"name": "IP", "id": "inner_ip"})
        self.assertEqual(len(result[1]["children"]), total_cloud_num)
        self.assertEqual(
            result[2],
            {
                "name": "操作系统",
                "id": "os_type",
                "children": MetaHandler.fetch_os_type_children(),
            },
        )
        self.assertEqual(
            result[3],
            {
                "id": "status",
                "name": "Agent状态",
                "children": [
                    {"id": status, "name": const.PROC_STATUS_CHN[status]} for status in const.PROC_STATUS_DICT.values()
                ],
            },
        )

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_job_setting(self):
        # 相关参数保存接口
        MetaHandler().job_setting({"test": 123})

    def test_regular_agent_version(self):
        result = MetaHandler().regular_agent_version(agent_versions=["1.26.58", "V0.01R060P42", "1.60.79"])
        self.assertEqual(result, ["1.26.58", "1.60.79", "V0.01R060P42"])

    def test_fetch_plugin_condition(self):
        result = MetaHandler().fetch_plugin_list_condition()
        self.assertEqual(len(result), 13)

    def test_fetch_plugin_version_condition(self):
        host_to_create, _, _ = create_host(10)
        process_to_create = []
        for host in host_to_create:
            process_to_create.append(
                ProcessStatus(
                    bk_host_id=host.bk_host_id,
                    proc_type=const.ProcType.PLUGIN,
                    version=f"{random.randint(1, 10)}",
                    name=settings.HEAD_PLUGINS[random.randint(0, len(settings.HEAD_PLUGINS) - 1)],
                    status="RUNNING",
                )
            )
        result = MetaHandler().fetch_plugin_version_condition()

        self.assertEqual(len(result), 13)
        self.assertEqual(len(result[0]["children"]), 10)
