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

from django.test import TestCase
from django.utils import timezone

from apps.node_man import constants as const
from apps.node_man import tools
from apps.node_man.exceptions import (
    AliveProxyNotExistsError,
    AllIpFiltered,
    JobDostNotExistsError,
    MixedOperationError,
)
from apps.node_man.handlers.job import JobHandler
from apps.node_man.models import Host, Job
from apps.node_man.tests.utils import (
    SEARCH_BUSINESS,
    MockClient,
    NodeApi,
    Subscription,
    create_cloud_area,
    create_host,
    create_job,
    gen_install_accept_list,
    gen_job_data,
    gen_update_accept_list,
)


class TestJob(TestCase):
    @classmethod
    def setUpTestData(cls):
        # 生成公私钥并存储到DB
        tools.HostTools.get_rsa_util()
        super().setUpTestData()

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_job_list(self):
        number = 1000
        create_job(number)

        # 正常查询
        JobHandler().list({"page": 1, "pagesize": 10, "job_type": const.JOB_TUPLE}, "admin")

        # 带业务参数查询
        JobHandler().list(
            {
                "page": 1,
                "pagesize": 10,
                "bk_biz_id": [2],
                "sort": {"sort_type": "ASC", "head": "total_number"},
                "category": "agent",
            },
            "admin",
        )

        # 带endtime查询
        create_job(1, id=9999, end_time=timezone.now())

        JobHandler().list(
            {
                "page": 1,
                "pagesize": 10,
                "job_id": [9999],
                "sort": {"sort_type": "DEC", "head": "total_number"},
                "category": "agent",
            },
            "admin",
        )

        # 全业务查询
        JobHandler().list(
            {
                "page": 1,
                "pagesize": 10,
                "bk_biz_id": [biz["bk_biz_id"] for biz in SEARCH_BUSINESS],
                "category": "agent",
            },
            "admin",
        )

    def test_job_list_no_biz_scope(self):
        number = 10

        # 创建没有业务的Job
        create_job(number, bk_biz_scope={})

        # 查询是否不显示
        result = JobHandler().list({"page": 1, "pagesize": 10, "category": "agent"}, "admin")
        self.assertEqual(result["total"], 0)

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_host_install(self):
        # 测试AGENT/P-AGENT/PROXY的job安装任务
        test_count = 1000

        # 创建云区域信息
        pagent_upstream_nodes = {0: [], 1: [1, 2, 3, 4, 5]}

        def get_cloud_info(_accept_list):
            cloud_info = {
                0: {
                    "bk_cloud_name": "直连区域",
                    "ap_id": 1,
                    "bk_biz_scope": list({host["bk_biz_id"] for host in _accept_list}),
                },
                1: {
                    "bk_cloud_name": "蓝鲸",
                    "ap_id": -1,
                    "bk_biz_scope": list({host["bk_biz_id"] for host in _accept_list}),
                },
                2: {
                    "bk_cloud_name": "蓝鲸2",
                    "ap_id": -1,
                    "bk_biz_scope": list({host["bk_biz_id"] for host in _accept_list}),
                },
            }
            return cloud_info

        # 生成存入表
        node_type = "PROXY"
        accept_list = gen_install_accept_list(test_count, node_type)
        JobHandler().subscription_install(accept_list, node_type, get_cloud_info(accept_list), pagent_upstream_nodes)
        node_type = "AGENT"
        accept_list.extend(gen_install_accept_list(test_count, node_type))
        JobHandler().subscription_install(accept_list, node_type, get_cloud_info(accept_list), pagent_upstream_nodes)
        node_type = "PAGENT"
        accept_list.extend(gen_install_accept_list(test_count, node_type, bk_cloud_id=2))
        JobHandler().subscription_install(accept_list, node_type, get_cloud_info(accept_list), pagent_upstream_nodes)
        # 测试注册失败
        accept_list.extend(gen_install_accept_list(1, node_type, bk_cloud_id=999))
        JobHandler().subscription_install(accept_list, node_type, get_cloud_info(accept_list), pagent_upstream_nodes)
        # 测试tjj ticket
        node_type = "AGENT"
        accept_list.extend(gen_install_accept_list(test_count, node_type, auth_type="TJJ_PASSWORD", ticket="test"))
        JobHandler().subscription_install(accept_list, node_type, get_cloud_info(accept_list), pagent_upstream_nodes)

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_host_update(self):
        # 创建host
        number = 1000
        host_to_create, process_to_create, identity_to_create = create_host(number)
        # 创建完毕，进行修改
        accept_list = gen_update_accept_list(host_to_create, identity_to_create)
        host_ids, _ = JobHandler().update(accept_list, [])
        self.assertEqual(len(host_ids), number)

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    @patch("apps.node_man.handlers.job.JobHandler.create_subscription", Subscription.create_subscription)
    def test_host_operate(self):
        # 创建host
        number = 100
        create_cloud_area(3)
        host_to_create, process_to_create, identity_to_create = create_host(number)

        proxies_ids = [host.bk_host_id for host in host_to_create if host.node_type == const.NodeType.PROXY]
        agent_or_pagent_ids = [host.bk_host_id for host in host_to_create if host.node_type != const.NodeType.PROXY]
        bk_biz_scope = [host.bk_biz_id for host in host_to_create]
        # 执行任务
        job_types = ["RESTART_PROXY", "RESTART_AGENT"]
        for job_type in job_types:
            node_filter_type = job_type.split("_")[1]
            bk_host_ids = proxies_ids if node_filter_type == const.NodeType.PROXY else agent_or_pagent_ids
            JobHandler().operate(job_type, bk_host_ids, bk_biz_scope)

    # 以下测试Job安装接口

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    @patch("apps.node_man.handlers.job.JobHandler.create_subscription", Subscription.create_subscription)
    def test_job_install_PROXY(self):
        # 创建云区域
        number = 100
        create_cloud_area(number)

        # 安装代理
        data = gen_job_data("INSTALL_PROXY", number, ap_id=-1)
        JobHandler().install(data["hosts"], data["op_type"], data["node_type"], data["job_type"], "ticket")

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    @patch("apps.node_man.handlers.job.JobHandler.create_subscription", Subscription.create_subscription)
    def test_job_install_mixed_op(self):
        # 创建云区域
        number = 100
        create_cloud_area(number)
        # 执行任务
        data = gen_job_data("INSTALL_AGENT", number)
        # 混合安装
        data["hosts"][0]["is_manual"] = True
        data["hosts"][1]["is_manual"] = False
        self.assertRaises(
            MixedOperationError,
            JobHandler().install,
            data["hosts"],
            data["op_type"],
            data["node_type"],
            data["job_type"],
            "ticket",
        )

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    @patch("apps.node_man.handlers.job.JobHandler.create_subscription", Subscription.create_subscription)
    def test_job_install_AGENT(self):
        # 创建云区域
        number = 100
        create_cloud_area(number)

        # 执行任务
        data = gen_job_data("INSTALL_AGENT", number)
        JobHandler().install(data["hosts"], data["op_type"], data["node_type"], data["job_type"], "ticket")

    # 测试不存在可用代理异常分支
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    @patch("apps.node_man.handlers.job.JobHandler.create_subscription", Subscription.create_subscription)
    def test_job_install_PAGENT(self):
        # 创建云区域
        number = 100
        create_cloud_area(number)

        # 执行任务
        data = gen_job_data("INSTALL_PAGENT", number, bk_cloud_id=2)
        self.assertRaises(
            AliveProxyNotExistsError,
            JobHandler().install,
            data["hosts"],
            data["op_type"],
            data["node_type"],
            data["job_type"],
            "ticket",
        )

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    @patch("apps.node_man.handlers.job.JobHandler.create_subscription", Subscription.create_subscription)
    def test_job_replace_PROXY(self):
        # 创建云区域
        bk_cloud_ids = create_cloud_area(1)
        # 执行任务
        data = gen_job_data("REPLACE_PROXY", 1, bk_cloud_id=bk_cloud_ids[0], ap_id=const.DEFAULT_AP_ID)
        JobHandler().install(data["hosts"], data["op_type"], data["node_type"], data["job_type"], "ticket")

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    @patch("apps.node_man.handlers.job.JobHandler.create_subscription", Subscription.create_subscription)
    def test_job_test_filter(self):
        # 创建云区域
        number = 100
        create_cloud_area(number)

        # 测试【全部被过滤】
        ip = "255.255.255.254"
        data = gen_job_data("INSTALL_AGENT", 1, ip=ip)
        JobHandler().install(data["hosts"], data["op_type"], data["node_type"], data["job_type"], "ticket")
        host = Host.objects.get(inner_ip=ip)
        self.assertEqual(host.inner_ip, ip)
        self.assertRaises(
            AllIpFiltered,
            JobHandler().install,
            data["hosts"],
            data["op_type"],
            data["node_type"],
            data["job_type"],
            "ticket",
        )

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    @patch("common.api.NodeApi.create_subscription", NodeApi.create_subscription)
    def test_job_reinstall(self):
        # 创建云区域
        number = 1000
        host_to_create, process_to_create, identity_to_create = create_host(number)
        create_cloud_area(number)

        # 安装
        data = gen_job_data(
            "INSTALL_AGENT", number, host_to_create, identity_to_create, bk_cloud_id=const.DEFAULT_CLOUD
        )
        JobHandler().install(data["hosts"], data["op_type"], data["node_type"], data["job_type"], "ticket")

        # 执行任务
        data = gen_job_data(
            "REINSTALL_AGENT", number, host_to_create, identity_to_create, bk_cloud_id=const.DEFAULT_CLOUD
        )
        JobHandler().install(data["hosts"], data["op_type"], data["node_type"], data["job_type"], "ticket")

        # 执行任务
        data = gen_job_data("INSTALL_PROXY", number, host_to_create, identity_to_create, ap_id=const.DEFAULT_AP_ID)
        JobHandler().install(data["hosts"], data["op_type"], data["node_type"], data["job_type"], "ticket")

        # 执行任务
        data = gen_job_data("REINSTALL_PROXY", number, host_to_create, identity_to_create, ap_id=const.DEFAULT_AP_ID)
        JobHandler().install(data["hosts"], data["op_type"], data["node_type"], data["job_type"], "ticket")

        # 全部被过滤
        host_to_create, process_to_create, identity_to_create = create_host(
            1, bk_host_id=9999, auth_type="PASSWORD", ip="1.1.1.1"
        )
        data = gen_job_data(
            "REINSTALL_AGENT", 1, host_to_create, identity_to_create, ap_id=const.DEFAULT_AP_ID, ip="1.1.1.1"
        )
        data["hosts"][0].pop("password")
        data["hosts"][0]["auth_type"] = "KEY"
        self.assertRaises(
            AllIpFiltered,
            JobHandler().install,
            data["hosts"],
            data["op_type"],
            data["node_type"],
            data["job_type"],
            "ticket",
        )

    @staticmethod
    def init_job():
        # 初始化一个任务
        number = 1
        host_to_create, process_to_create, identity_to_create = create_host(number)
        create_cloud_area(number)
        data = gen_job_data(
            "INSTALL_AGENT", number, host_to_create, identity_to_create, bk_cloud_id=const.DEFAULT_CLOUD
        )
        job_id = JobHandler().install(data["hosts"], data["op_type"], data["node_type"], data["job_type"], "ticket")[
            "job_id"
        ]
        return job_id

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    @patch("apps.node_man.handlers.job.JobHandler.create_subscription", Subscription.create_subscription)
    @patch("common.api.NodeApi.retry_subscription_task", NodeApi.retry_subscription_task)
    def test_job_retry(self):
        # 测试retry接口
        job_id = self.init_job()

        # 有instance的分支
        self.assertIsInstance(JobHandler(job_id=job_id).retry(["1"]), list)

        # 无instance的分支
        self.assertIsInstance(JobHandler(job_id=job_id).retry([]), list)

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    @patch("apps.node_man.handlers.job.JobHandler.create_subscription", Subscription.create_subscription)
    @patch("common.api.NodeApi.revoke_subscription_task", NodeApi.revoke_subscription_task)
    def test_job_revoke(self):
        # 测试revoke接口
        job_id = self.init_job()
        # 有instance的分支
        self.assertIsInstance(JobHandler(job_id=job_id).revoke(["1"]), list)

        # 无instance的分支
        self.assertIsInstance(JobHandler(job_id=job_id).revoke([]), list)

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    @patch("apps.node_man.handlers.job.JobHandler.create_subscription", Subscription.create_subscription)
    @patch("common.api.NodeApi.get_subscription_task_status", NodeApi.get_subscription_task_status)
    def test_job_retrieve(self):
        # 测试revoke接口
        job_id = self.init_job()
        # 测试参数
        params = {
            "page": 1,
            "pagesize": 10,
            "conditions": [{"key": "ip", "value": "1.1.1.1"}, {"key": "status", "value": "SUCCESS"}],
        }
        # SUCCESS
        job = Job.objects.get(id=job_id)
        job.subscription_id = 1
        job.save()
        self.assertEqual(JobHandler(job_id=job_id).retrieve(params)["status"], "SUCCESS")
        # FAILED
        job = Job.objects.get(id=job_id)
        job.subscription_id = 2
        job.save()
        self.assertEqual(JobHandler(job_id=job_id).retrieve(params)["status"], "FAILED")
        # RUNNING
        job = Job.objects.get(id=job_id)
        job.subscription_id = 3
        job.save()
        self.assertEqual(JobHandler(job_id=job_id).retrieve(params).get("statistics").get("running_count"), 1)
        # PENDING
        job = Job.objects.get(id=job_id)
        job.subscription_id = 4
        job.save()
        JobHandler(job_id=job_id).retrieve(params)
        # 异常分支
        job = Job.objects.get(id=job_id)
        job.subscription_id = 0
        job.save()
        self.assertEqual(JobHandler(job_id=job_id).retrieve(params)["status"], "FAILED")
        # PART_FAILED
        job = Job.objects.get(id=job_id)
        job.subscription_id = 6
        job.save()
        self.assertEqual(JobHandler(job_id=job_id).retrieve(params)["status"], "PART_FAILED")

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    @patch("apps.node_man.handlers.job.JobHandler.create_subscription", Subscription.create_subscription)
    @patch("common.api.NodeApi.get_subscription_task_detail", NodeApi.get_subscription_task_detail)
    def test_get_log(self):
        # 测试get_log接口
        job_id = self.init_job()
        self.assertIsInstance(JobHandler(job_id=job_id).get_log(instance_id="1"), list)

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    @patch("apps.node_man.handlers.job.JobHandler.create_subscription", Subscription.create_subscription)
    @patch("common.api.NodeApi.collect_subscription_task_detail", NodeApi.collect_subscription_task_detail)
    def test_collect_log(self):
        # 测试 collect_log 接口
        # 初始化一个任务
        number = 1
        host_to_create, process_to_create, identity_to_create = create_host(number)
        create_cloud_area(number)
        data = gen_job_data(
            "INSTALL_AGENT", number, host_to_create, identity_to_create, bk_cloud_id=const.DEFAULT_CLOUD
        )
        result = JobHandler().install(data["hosts"], data["op_type"], data["node_type"], data["job_type"], "ticket")
        job_id = result["job_id"]
        self.assertEqual(JobHandler(job_id=job_id).collect_log(1), "SUCCESS")

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    @patch("apps.node_man.handlers.job.JobHandler.create_subscription", Subscription.create_subscription)
    @patch("common.api.NodeApi.get_subscription_task_detail", NodeApi.get_subscription_task_detail)
    def test_get_data(self):
        # 测试get_data接口
        job_id = self.init_job()
        # 测试
        self.assertEqual(JobHandler(job_id=job_id)._get_data().id, job_id)

        # 任务不存在
        self.assertRaises(JobDostNotExistsError, JobHandler(job_id=21312312)._get_data)

    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    @patch("apps.node_man.handlers.job.JobHandler.create_subscription", Subscription.create_subscription)
    @patch("common.api.NodeApi.fetch_commands", NodeApi.fetch_commands)
    @patch("common.api.NodeApi.get_subscription_task_status", NodeApi.get_subscription_task_status)
    def test_gen_commands(self):
        # 测试gen_commands接口
        number = 1
        host_to_create, process_to_create, identity_to_create = create_host(number, bk_cloud_id=0, bk_host_id=1)
        create_cloud_area(number)
        data = gen_job_data(
            "INSTALL_AGENT", number, host_to_create, identity_to_create, bk_cloud_id=const.DEFAULT_CLOUD
        )
        result = JobHandler().install(data["hosts"], data["op_type"], data["node_type"], data["job_type"], "ticket")

        job_id = result["job_id"]
        job = Job.objects.get(id=job_id)
        job.subscription_id = 5
        job.save()

        commands = JobHandler(job_id=job_id).get_commands(-1, False)

        # 测试
        self.assertEqual(len(commands[0]["ips_commands"]), 1)
        self.assertEqual(commands[0]["ips_commands"][0]["command"], "test")
