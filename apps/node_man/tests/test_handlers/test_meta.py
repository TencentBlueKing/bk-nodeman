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
import os
import random
from unittest.mock import patch

from django.conf import settings
from django.test import override_settings
from django.utils.translation import ugettext as _

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
from apps.utils.unittest import testcase

FILTER_CONDITION_JOB_COUNT_FOR_TEST = int(os.environ.get("FILTER_CONDITION_JOB_COUNT_FOR_TEST", 100000))


class TestMeta(testcase.CustomAPITestCase):
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

    def fetch_job_unique_col_count(self, search_business=None):
        """
        返回Job中指定列的唯一值
        :return: 唯一值的数量
        """
        search_business = search_business or SEARCH_BUSINESS

        # 获得4列的所有值
        job_condition = list(Job.objects.values("created_by", "job_type", "status", "bk_biz_scope").distinct())

        # 初始化各个条件集合
        created_bys = set()
        job_types = set()
        statuses = set()

        for job in job_condition:
            # 判断权限
            bk_biz_scope = set(job["bk_biz_scope"])
            search_bk_biz_ids = {biz["bk_biz_id"] for biz in search_business}
            if any(biz_id in search_bk_biz_ids for biz_id in bk_biz_scope):
                created_bys.add(job["created_by"])
                job_types.add(job["job_type"])
                statuses.add(job["status"])

        return created_bys, job_types, statuses

    @staticmethod
    def generate_random_biz_scope(sample_biz_ids, min_biz_count=1, max_biz_count=5):
        """
        从业务列表中随机获取其中几个业务
        :param sample_biz_ids: 业务列表
        :param min_biz_count: 最少获取几个业务
        :param max_biz_count: 最多获取几个业务
        :return: 子业务列表
        """

        def wrapper():
            return random.sample(sample_biz_ids, k=random.randint(min_biz_count, max_biz_count))

        return wrapper

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

        created_bys, job_types, statuses = self.fetch_job_unique_col_count()

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

        # 验证不传业务ID的情况；即返回用户所有权限的筛选项key
        result = MetaHandler().filter_condition("plugin_host", params={"bk_biz_ids": []})
        self.assertEqual(result[0], {"name": "IP", "id": "ip"})
        self.assertEqual(result[1], {"name": "管控区域ID:IP", "id": "bk_cloud_ip"})

        self.assertEqual(
            result[5],
            {
                "name": "操作系统",
                "id": "os_type",
                "children": MetaHandler.fetch_os_type_children(),
            },
        )
        self.assertEqual(
            result[6],
            {
                "id": "status",
                "name": "Agent状态",
                "children": [
                    {"id": status, "name": const.PROC_STATUS_CHN[status]} for status in const.PROC_STATUS_DICT.values()
                ],
            },
        )
        plugin_bt_or_compress_condition_value = [0, 1]
        condition_key = ["停用", "启用"]
        self.assertEqual(
            result[7],
            {
                "id": "bt_node_detection",
                "name": "BT节点探测",
                "children": [
                    {"name": condition_key[condition], "id": condition}
                    for condition in plugin_bt_or_compress_condition_value
                ],
            },
        )
        if settings.BKAPP_ENABLE_DHCP:
            self.assertEqual(
                result[8],
                {
                    "id": "enable_compression",
                    "name": "数据压缩",
                    "children": [
                        {"name": condition_key[condition], "id": str(bool(condition))}
                        for condition in plugin_bt_or_compress_condition_value
                    ],
                },
            )

        # 验证传入部分业务ID的情况
        result = MetaHandler().filter_condition("plugin_host", params={"bk_biz_ids": [27]})
        # 验证管控区域的数量
        self.assertLessEqual(len(result[4]["children"]), 2)

        # 验证传入没有的业务ID的情况
        result = MetaHandler().filter_condition("plugin_host", params={"bk_biz_ids": [43225, 189731]})
        self.assertEqual(len(result), 3)

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_job_setting(self):
        # 相关参数保存接口
        MetaHandler().job_setting({"test": 123})

    def test_regular_agent_version(self):
        result = MetaHandler().regular_agent_version(agent_versions=["1.26.58", "V0.01R060P42", "1.60.79"])
        self.assertEqual(result, ["1.26.58", "1.60.79", "V0.01R060P42"])

    def test_fetch_plugin_condition(self):
        result = MetaHandler().fetch_plugin_list_condition()
        self.assertEqual(len(result), 11)

    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
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
        ProcessStatus.objects.bulk_create(process_to_create)
        # 验证不传业务ID的情况；即返回用户所有权限的业务ID
        result = MetaHandler().fetch_plugin_version_condition(params={"bk_biz_ids": []})
        self.assertEqual(len(result), 11)
        self.assertEqual(len(result[0]["children"]), 10)
        # 验证传入部分业务ID的情况
        result = MetaHandler().fetch_plugin_version_condition(params={"bk_biz_ids": [27, 30]})
        self.assertLessEqual(len(result), 11)
        # 验证传入没有的业务ID的情况
        result = MetaHandler().fetch_plugin_version_condition(params={"bk_biz_ids": [789987]})
        # 无法预知线上GLOBAL_SETTINGS中HEAD_PLUGINS数量，故取一个较大的值
        self.assertLessEqual(len(result), 30)

    @override_settings(BKAPP_DEFAULT_SSH_PORT=22)
    def test_global_settings__install_default_values(self):

        GlobalSettings.set_config(
            GlobalSettings.KeyEnum.INSTALL_DEFAULT_VALUES.value,
            value={"COMMON": {"auth_type": const.AuthType.KEY}, "WINDOWS": {"auth": const.AuthType.PASSWORD}},
        )
        kv = self.client.get(
            "/api/meta/global_settings/", {"key": GlobalSettings.KeyEnum.INSTALL_DEFAULT_VALUES.value}
        )["data"]

        expect_install_default_values = {
            "COMMON": {"auth_type": const.AuthType.KEY},
            **{
                os_type: {
                    "port": settings.BKAPP_DEFAULT_SSH_PORT,
                    "auth_type": const.AuthType.KEY,
                    "account": const.LINUX_ACCOUNT,
                }
                for os_type in const.OS_TUPLE
                if os_type not in [const.OsType.WINDOWS]
            },
            "WINDOWS": {
                "port": const.WINDOWS_PORT,
                "auth_type": const.AuthType.KEY,
                "account": const.WINDOWS_ACCOUNT,
                "auth": const.AuthType.PASSWORD,
            },
        }
        self.assertDictEqual(kv, {GlobalSettings.KeyEnum.INSTALL_DEFAULT_VALUES.value: expect_install_default_values})

    @patch(
        "apps.node_man.handlers.cmdb.CmdbHandler.biz_id_name_without_permission",
        return_value={1: "A", 2: "B", 3: "C", 4: "D", 5: "E"},
    )
    @patch(
        "apps.node_man.handlers.cmdb.CmdbHandler.biz_id_name",
        return_value={1: "A", 2: "B", 3: "C", 4: "D", 5: "E"},
    )
    @patch("apps.node_man.handlers.cmdb.get_request_username", return_value="admin")
    def test_job_filter_condition_with_large_biz_and_job(self, *args, **kwargs):
        biz_count = 4000
        biz_ids = list(range(1, biz_count + 1))
        create_job(
            FILTER_CONDITION_JOB_COUNT_FOR_TEST,
            generate_bk_biz_scope_func=self.generate_random_biz_scope(sample_biz_ids=biz_ids),
        )

        create_job(
            FILTER_CONDITION_JOB_COUNT_FOR_TEST // 10, start_id=FILTER_CONDITION_JOB_COUNT_FOR_TEST + 1, bk_biz_scope={}
        )

        kwargs = {"bk_biz_ids": random.sample(biz_ids, k=random.randint(3000, 3900))}
        filter_condition = MetaHandler().filter_condition("job", kwargs)

        id__filter_item_map = {filter_item["id"]: filter_item for filter_item in filter_condition}

        api_statuses = {child["id"] for child in id__filter_item_map["status"]["children"]}
        api_op_types = {child["id"] for child in id__filter_item_map["op_type"]["children"]}
        api_step_types = {child["id"] for child in id__filter_item_map["step_type"]["children"]}
        api_created_bys = {child["id"] for child in id__filter_item_map["created_by"]["children"]}

        created_bys, job_types, statuses = self.fetch_job_unique_col_count(
            search_business=[{"bk_biz_id": bk_biz_id, "bk_biz_name": ""} for bk_biz_id in set(range(1, 4001))]
        )

        job_type_infos = [tools.JobTools.unzip_job_type(job_type) for job_type in job_types]

        self.assertEqual(id__filter_item_map["job_id"], {"name": "任务ID", "id": "job_id"})
        self.assertEqual(api_op_types, {job_type_info["op_type"] for job_type_info in job_type_infos})
        self.assertEqual(api_step_types, {job_type_info["step_type"] for job_type_info in job_type_infos})
        self.assertEqual(api_created_bys, created_bys)
        self.assertEqual(api_statuses, statuses)

    @patch(
        "apps.node_man.handlers.cmdb.CmdbHandler.biz_id_name_without_permission",
        return_value={1: "A", 2: "B", 3: "C", 4: "D", 5: "E"},
    )
    @patch(
        "apps.node_man.handlers.cmdb.CmdbHandler.biz_id_name",
        return_value={1: "A", 2: "B", 3: "C", 4: "D", 5: "E"},
    )
    @patch("apps.node_man.handlers.cmdb.get_request_username", return_value="admin")
    def test_job_filter_condition_with_time_filter(self, *args, **kwargs):
        create_job(1, created_by="test1")
        create_job(1, created_by="test2", start_id=2)

        # created_job中手动指定start_time无效，具体原因不清楚
        Job.objects.filter(id=1).update(start_time="2023-10-01 12:00:00")
        Job.objects.filter(id=2).update(start_time="2023-10-03 12:00:00")

        kwargs_list = [
            {
                "start_time": "2023-10-01 12:00:00",
                "end_time": "2023-10-02 12:00:00",
            },
            {
                "start_time": "2023-10-02 12:00:00",
                "end_time": "2023-10-03 12:00:00",
            },
            {
                "start_time": "2023-10-01 12:00:00",
                "end_time": "2023-10-03 12:00:00",
            },
            {},
        ]
        expected_created_by_lens = [1, 1, 2, 2]
        expected_created_by_names = ["test1", "test2", ["test1", "test2"], ["test1", "test2"]]

        for kwargs, expected_created_by_len, expected_created_by_name in zip(
            kwargs_list, expected_created_by_lens, expected_created_by_names
        ):
            filter_condition = MetaHandler().filter_condition("job", params=kwargs)
            created_by_info = [
                single_condition for single_condition in filter_condition if single_condition["id"] == "created_by"
            ][0]

            # 检验长度
            self.assertEqual(len(created_by_info["children"]), expected_created_by_len)

            # 检验created_by
            if expected_created_by_len > 1:
                self.assertEqual(
                    sorted(created_by["name"] for created_by in created_by_info["children"]), expected_created_by_name
                )
            else:
                self.assertEqual(created_by_info["children"][0]["name"], expected_created_by_name)

    @patch(
        "apps.node_man.handlers.cmdb.CmdbHandler.biz_id_name_without_permission",
        return_value={1: "A", 2: "B", 3: "C", 4: "D", 5: "E"},
    )
    @patch(
        "apps.node_man.handlers.cmdb.CmdbHandler.biz_id_name",
        return_value={1: "A", 2: "B", 3: "C", 4: "D", 5: "E"},
    )
    @patch("apps.node_man.handlers.cmdb.get_request_username", return_value="admin")
    def test_job_filter_condition_with_nonexistent_biz(self, *args, **kwargs):
        number = 1000

        create_job(
            number,
            generate_bk_biz_scope_func=self.generate_random_biz_scope(sample_biz_ids=[1, 2, 3, 4, 5], max_biz_count=3),
        )
        create_job(number // 10, bk_biz_scope={}, start_id=number + 1)

        result = MetaHandler().filter_condition("job", params={"bk_biz_ids": [-1, -2]})
        self.assertEqual(
            result,
            [
                {"name": _("任务ID"), "id": "job_id"},
                {"name": _("IP"), "id": "inner_ip_list"},
            ],
        )

    @patch(
        "apps.node_man.handlers.cmdb.CmdbHandler.biz_id_name_without_permission",
        return_value={1: "A", 2: "B", 3: "C", 4: "D", 5: "E"},
    )
    @patch(
        "apps.node_man.handlers.cmdb.CmdbHandler.biz_id_name",
        return_value={1: "A", 2: "B", 3: "C", 4: "D", 5: "E"},
    )
    @patch("apps.node_man.handlers.cmdb.get_request_username", return_value="admin")
    def test_job_filter_condition_with_reverse_query(self, *args, **kwargs):
        create_job(1, created_by="test1", bk_biz_scope=[1])
        create_job(1, created_by="test2", start_id=2, bk_biz_scope=[1, 2])
        create_job(1, created_by="test3", start_id=3, bk_biz_scope=[3, 2])
        create_job(1, created_by="test4", start_id=4, bk_biz_scope=[4])
        create_job(1, created_by="test5", start_id=5, bk_biz_scope=[5, 1])

        filter_condition = MetaHandler().filter_condition("job", params={"bk_biz_ids": [2, 3, 4]})
        created_by_info = [
            single_condition for single_condition in filter_condition if single_condition["id"] == "created_by"
        ][0]
        # 排除第一条和第五条
        self.assertEqual(len(created_by_info["children"]), 3)
        self.assertEqual(
            sorted(created_by["name"] for created_by in created_by_info["children"]), ["test2", "test3", "test4"]
        )

        filter_condition = MetaHandler().filter_condition("job", params={"bk_biz_ids": [2, 3, 4, 5]})
        created_by_info = [
            single_condition for single_condition in filter_condition if single_condition["id"] == "created_by"
        ][0]
        # 排除第一条
        self.assertEqual(len(created_by_info["children"]), 4)
        self.assertEqual(
            sorted(created_by["name"] for created_by in created_by_info["children"]),
            ["test2", "test3", "test4", "test5"],
        )

    @patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_fetch_host_list_condition_no_permission(self, *args, **kwargs):
        self.maxDiff = None
        number = 100
        host_to_create, _, _ = create_host(number)
        process_to_create = []
        for host in host_to_create:
            process_to_create.append(
                ProcessStatus(
                    bk_host_id=host.bk_host_id,
                    proc_type=const.ProcType.PLUGIN,
                    version=f"{random.randint(11, 20)}",
                    name=settings.HEAD_PLUGINS[random.randint(0, len(settings.HEAD_PLUGINS) - 1)],
                    status="RUNNING",
                )
            )

        # 验证不传业务ID的情况；即返回用户所有权限的筛选项key
        result = MetaHandler().filter_condition("host", params={"bk_biz_ids": []})
        self.assertEqual(len(result), 10)

        # 验证传入没有的业务ID的情况
        result = MetaHandler().filter_condition("host", params={"bk_biz_ids": [2, 4, 5]})
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], {"name": "IP", "id": "ip"})
        self.assertEqual(result[1], {"name": "管控区域ID:IP", "id": "bk_cloud_ip"})
        self.assertEqual(result[2], {"name": "主机名称", "id": "bk_host_name"})

        # 验证传入部分业务ID的情况
        result = MetaHandler().filter_condition("host", params={"bk_biz_ids": [27, 30, 31, 35]})
        # 验证管控区域的数量
        self.assertEqual(len(result[3].get("children")), 2)
        # 验证agent版本数量
        self.assertLessEqual(len(result[6].get("children")), 100)
