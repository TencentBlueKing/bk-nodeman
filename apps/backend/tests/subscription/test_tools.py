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
from collections import defaultdict

import mock
from django.test import TestCase

from apps.backend.subscription.tools import (
    get_instances_by_scope,
    parse_group_id,
    parse_host_key,
)
from apps.backend.tests.subscription.utils import (
    CmdbClient,
    list_biz_hosts_without_info_client,
)
from apps.node_man import constants, models

# 全局使用的mock
run_task = mock.patch("apps.backend.subscription.tasks.run_subscription_task").start()


class TestTools(TestCase):
    """
    测试tools.py下的函数
    """

    GROUP_ID = "sub_1_host_1"
    HOST_KEY = "127.0.0.1-0-tencent"
    HOST_ID_KEY = "1024"

    def setUp(self):
        self.get_host_object_attribute_client = mock.patch(
            "apps.backend.subscription.commons.get_host_object_attribute", lambda args: []
        )
        self.get_process_by_biz_id_client = mock.patch(
            "apps.backend.subscription.tools.get_process_by_biz_id", lambda args, bk_host_list: defaultdict(dict)
        )
        self.tools_client = mock.patch("apps.backend.subscription.tools.client_v2", CmdbClient)
        self.commons_client = mock.patch("apps.backend.subscription.commons.client_v2", CmdbClient)
        self.handlers_client = mock.patch("apps.node_man.handlers.cmdb.client_v2", CmdbClient)
        self.batch_request_client = mock.patch(
            "apps.backend.subscription.commons.batch_request", list_biz_hosts_without_info_client
        )

        self.tools_client.start()
        self.commons_client.start()
        self.handlers_client.start()
        self.get_host_object_attribute_client.start()
        self.get_process_by_biz_id_client.start()
        self.batch_request_client.start()

        models.Host.objects.create(
            bk_host_id=1,
            bk_biz_id=2,
            bk_cloud_id=0,
            inner_ip="127.0.0.1",
            outer_ip=None,
            login_ip="127.0.0.1",
            data_ip="127.0.0.1",
            os_type="LINUX",
            node_type="AGENT",
            ap_id=1,
        )
        models.ProcessStatus.objects.create(
            bk_host_id=1,
            name=models.ProcessStatus.GSE_AGENT_PROCESS_NAME,
            proc_type=constants.ProcType.AGENT,
            source_type=models.ProcessStatus.SourceType.DEFAULT,
        )

    def tearDown(self):
        self.tools_client.stop()
        self.commons_client.stop()
        self.handlers_client.stop()
        self.get_host_object_attribute_client.stop()
        self.get_process_by_biz_id_client.stop()
        self.batch_request_client.stop()

    def test_parse_group_id(self):
        res = parse_group_id(self.GROUP_ID)
        assert res["subscription_id"] == "1"
        assert res["object_type"] == "host"
        assert res["id"] == "1"

    def test_parse_host_key(self):
        res = parse_host_key(self.HOST_KEY)
        assert res["ip"] == "127.0.0.1"
        assert res["bk_cloud_id"] == "0"
        assert res["bk_supplier_id"] == "tencent"

        res = parse_host_key(self.HOST_ID_KEY)
        assert res["bk_host_id"] == 1024

    def test_get_host_instance_scope(self):
        instances = get_instances_by_scope(
            {
                "bk_biz_id": 2,
                "object_type": "HOST",
                "node_type": "INSTANCE",
                "nodes": [
                    {"ip": "127.0.0.1", "bk_cloud_id": 0, "bk_supplier_id": 0},
                    {"ip": "127.0.0.1", "bk_cloud_id": 0, "bk_supplier_id": 0},
                ],
            }
        )

        self.assertEqual(len(list(instances.keys())), 1)
        assert "host|instance|host|1" in instances

    def test_get_host_topo_scope(self):
        instances = get_instances_by_scope(
            {
                "bk_biz_id": 2,
                "object_type": "HOST",
                "node_type": "TOPO",
                "nodes": [
                    {"bk_obj_id": "module", "bk_inst_id": 1},
                    {"bk_obj_id": "set", "bk_inst_id": 2},
                    {"bk_obj_id": "test", "bk_inst_id": 1000},
                ],
            }
        )

        self.assertEqual(len(list(instances.keys())), 1)
        self.assertIn("host|instance|host|1", instances)

    def test_get_host_topo_scope_with_multi_biz(self):
        instances = get_instances_by_scope(
            {
                "object_type": "HOST",
                "node_type": "TOPO",
                "nodes": [
                    {"bk_obj_id": "module", "bk_inst_id": 1, "bk_biz_id": 2},
                    {"bk_obj_id": "set", "bk_inst_id": 2, "bk_biz_id": 2},
                    {"bk_obj_id": "test", "bk_inst_id": 1000, "bk_biz_id": 2},
                ],
            },
            get_cache=True,
        )

        self.assertEqual(len(list(instances.keys())), 1)

    def test_get_service_topo_scope(self):
        instances = get_instances_by_scope(
            {
                "bk_biz_id": 2,
                "object_type": "SERVICE",
                "node_type": "TOPO",
                "nodes": [{"bk_obj_id": "module", "bk_inst_id": 12}],
            }
        )

        self.assertEqual(len(list(instances.keys())), 1)
        for instance_id in instances:
            instance = instances[instance_id]
            self.assertEqual(instance["service"]["bk_module_id"], 12)
            self.assertSetEqual({"process", "scope", "host", "service"}, set(instance.keys()))

    def test_get_service_instance_scope(self):
        instances = get_instances_by_scope(
            {"bk_biz_id": 2, "object_type": "SERVICE", "node_type": "INSTANCE", "nodes": [{"id": 10}]}
        )

        self.assertEqual(len(list(instances.keys())), 1)
        for instance_id in instances:
            instance = instances[instance_id]
            self.assertEqual(instance["service"]["id"], 10)
            self.assertSetEqual({"process", "scope", "host", "service"}, set(instance.keys()))

    def test_get_instance_selector_scope(self):
        instances = get_instances_by_scope(
            {
                "bk_biz_id": 2,
                "object_type": "HOST",
                "node_type": "INSTANCE",
                "instance_selector": [{"key": "os_type", "value": ["WINDOWS"]}],
                "nodes": [
                    {"ip": "127.0.0.1", "bk_cloud_id": 0, "bk_supplier_id": 0},
                ],
            }
        )
        self.assertEqual(len(list(instances.keys())), 0)

    def test_get_empty_list_instance_selector_scope(self):
        instances = get_instances_by_scope(
            {
                "bk_biz_id": 2,
                "object_type": "HOST",
                "node_type": "INSTANCE",
                "instance_selector": [],
                "nodes": [
                    {"ip": "127.0.0.1", "bk_cloud_id": 0, "bk_supplier_id": 0},
                ],
            }
        )
        self.assertEqual(len(list(instances.keys())), 0)

    def test_sub_biz_priority(self):
        # 之前订阅优先使用 scope.bk_biz_id 作为整个订阅的业务范围，后面调整为优先使用 scope.nodes 内的业务范围
        instances = get_instances_by_scope(
            {
                "object_type": "HOST",
                "node_type": "INSTANCE",
                "bk_biz_id": 2,
                "nodes": [
                    {"ip": "127.0.0.1", "bk_cloud_id": 0, "bk_supplier_id": 0, "bk_biz_id": 2},
                    {"ip": "127.0.0.2", "bk_cloud_id": 0, "bk_supplier_id": 0, "bk_biz_id": 3},
                ],
            }
        )

        self.assertEqual(len(list(instances.keys())), 1)
        instances = get_instances_by_scope(
            {
                "object_type": "HOST",
                "node_type": "INSTANCE",
                "nodes": [
                    {"ip": "127.0.0.1", "bk_cloud_id": 0, "bk_supplier_id": 0, "bk_inst_id": 2, "bk_obj_id": "biz"},
                ],
            }
        )
        self.assertEqual(len(list(instances.keys())), 1)

        request_handler = mock.MagicMock(
            return_value=[
                {"ip": "127.0.0.1", "bk_cloud_id": 0, "bk_supplier_id": 0, "bk_inst_id": 2, "bk_obj_id": "biz"}
            ]
        )
        with mock.patch("apps.backend.subscription.tools.request_multi_thread", request_handler):
            get_instances_by_scope(
                {
                    "object_type": "HOST",
                    "node_type": "INSTANCE",
                    "nodes": [
                        {"ip": "127.0.0.1", "bk_cloud_id": 0, "bk_supplier_id": 0, "bk_inst_id": 2, "bk_obj_id": "biz"},
                        {"ip": "127.0.0.1", "bk_cloud_id": 0, "bk_supplier_id": 0, "bk_biz_id": 3},
                        {"ip": "127.0.0.4", "bk_cloud_id": 0, "bk_supplier_id": 0, "bk_biz_id": 3},
                        {"ip": "127.0.0.5", "bk_cloud_id": 0, "bk_supplier_id": 0, "bk_biz_id": 3},
                        {"ip": "127.0.0.2", "bk_cloud_id": 0, "bk_supplier_id": 0, "bk_biz_id": 4},
                        {"ip": "127.0.0.6", "bk_cloud_id": 0, "bk_supplier_id": 0, "bk_biz_id": 4},
                    ],
                }
            )

        self.assertEqual(len(request_handler.call_args[0][1]), 3)
        for instance in request_handler.call_args[0][1]:
            if instance["scope"]["bk_biz_id"] == 3:
                self.assertEqual(len(instance["scope"]["nodes"]), 3)
            if instance["scope"]["bk_biz_id"] == 4:
                self.assertEqual(len(instance["scope"]["nodes"]), 2)
