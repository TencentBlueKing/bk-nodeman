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
import copy
from collections import defaultdict

import mock
import ujson as json
from django.test import Client, TestCase

from apps.backend.plugin.manager import PluginManager
from apps.backend.subscription.tasks import run_subscription_task_and_create_instance
from apps.backend.tests.subscription.utils import (
    DEFAULT_AP_ID,
    CmdbClient,
    list_biz_hosts_without_info_client,
)
from apps.mock_data.backend_mkd.subscription.unit import GSE_PLUGIN_DESC_DATA
from apps.node_man.models import (
    GsePluginDesc,
    Host,
    Packages,
    PluginConfigTemplate,
    ProcControl,
    ProcessStatus,
    Subscription,
    SubscriptionStep,
    SubscriptionTask,
)

DEFEAULT_CREATE_SUBSCRIPTION_DATA = {
    "bk_username": "admin",
    "bk_app_code": "blueking",
    "scope": {
        "bk_biz_id": 2,
        "node_type": "TOPO",
        "object_type": "HOST",
        "nodes": [
            {
                "ip": "127.0.0.1",
                "bk_cloud_id": 0,
                "bk_supplier_id": 0,
                "bk_obj_id": "biz",
                "bk_inst_id": 32,
            }
        ],
    },
    "steps": [
        {
            "id": "my_first",
            "type": "PLUGIN",
            "config": {
                "plugin_name": "mysql_exporter",
                "plugin_version": "2.3",
                "config_templates": [
                    {"name": "config.yaml", "version": "2"},
                    {"name": "env.yaml", "version": "2"},
                ],
            },
            "params": {"url": "asdfasdfs"},
        }
    ],
}


class TestPolicy(TestCase):
    """
    在策略场景下的测试订阅相关的接口
    """

    CREATE_SUBSCRIPTION_DATA = copy.deepcopy(DEFEAULT_CREATE_SUBSCRIPTION_DATA)

    client = Client()

    def setUp(self):
        mock.patch.stopall()
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
        self.run_subscription_task_and_create_instance_client = mock.patch(
            "apps.backend.subscription.handler.tasks.run_subscription_task_and_create_instance",
            delay=run_subscription_task_and_create_instance,
        )

        self.tools_client.start()
        self.commons_client.start()
        self.handlers_client.start()
        self.get_host_object_attribute_client.start()
        self.get_process_by_biz_id_client.start()
        self.batch_request_client.start()

        self.run_subscription_task_and_create_instance_client.start()

        self.run_task = mock.patch("apps.backend.subscription.tasks.run_subscription_task").start()

    def tearDown(self):
        mock.patch.stopall()

    def _test_create_subscription(self):
        r = self.client.post(
            path="/backend/api/subscription/create/",
            content_type="application/json",
            data=json.dumps(
                {
                    "bk_username": "admin",
                    "bk_app_code": "blueking",
                    "scope": {"bk_biz_id": 2, "node_type": "TOPO", "object_type": "HOST", "nodes": [{"id": 123}]},
                    "steps": [
                        {
                            "id": "my_first",
                            "type": "PLUGIN",
                            "config": {
                                "plugin_name": "mysql_exporter",
                                "plugin_version": "2.3",
                                "config_templates": [
                                    {"name": "config.yaml", "version": "2"},
                                    {"name": "env.yaml", "version": "2"},
                                ],
                            },
                            "params": {"url": "asdfasdfs"},
                        }
                    ],
                }
            ),
        )
        assert r.status_code == 200
        assert r.data["result"]

        subscription_id = r.data["data"]["subscription_id"]

        # 探测数据库是否创建了对应的记录
        Subscription.objects.get(id=r.data["data"]["subscription_id"])
        SubscriptionStep.objects.get(step_id="my_first", subscription_id=subscription_id)

        return subscription_id

    def _test_get_subscription(self, policy_id):
        r = self.client.post(
            path="/backend/api/subscription/info/",
            content_type="application/json",
            data=json.dumps({"bk_username": "admin", "bk_app_code": "blueking", "subscription_id_list": [policy_id]}),
        )

        assert r.status_code == 200
        assert r.data["result"]

        assert len(r.data["data"]) == 1
        for subscription in r.data["data"]:
            assert isinstance(subscription["scope"], dict)
            assert isinstance(subscription["steps"], list)

    def _test_update_subscription(self, subscription_id):
        r = self.client.post(
            path="/backend/api/subscription/update/",
            content_type="application/json",
            data=json.dumps(
                {
                    "bk_username": "admin",
                    "bk_app_code": "blueking",
                    "subscription_id": subscription_id,
                    "scope": {"node_type": "TOPO", "nodes": [{"bk_host_id": 100}]},
                    "steps": [
                        {
                            "id": "my_first",
                            "params": {
                                "--web.listen-host": "${cmdb_instance.host}",
                                "--web.listen-port": "${cmdb_instance.port}",
                            },
                        }
                    ],
                }
            ),
        )

        assert r.status_code == 200
        assert r.data["result"]

        subscription = Subscription.objects.get(id=subscription_id)
        step = subscription.steps[0]

        assert subscription.node_type == "TOPO"
        assert subscription.nodes[0]["bk_host_id"] == 100
        assert step.params["--web.listen-host"] == "${cmdb_instance.host}"
        assert step.params["--web.listen-port"] == "${cmdb_instance.port}"

    def _test_switch_subscription(self, subscription_id):
        # 测试停用
        r = self.client.post(
            path="/backend/api/subscription/switch/",
            content_type="application/json",
            data=json.dumps(
                {
                    "bk_username": "admin",
                    "bk_app_code": "blueking",
                    "subscription_id": subscription_id,
                    "action": "disable",
                }
            ),
        )

        assert r.status_code == 200
        assert r.data["result"]

        subscription = Subscription.objects.get(id=subscription_id)
        assert not subscription.enable

        # 测试启用
        r = self.client.post(
            path="/backend/api/subscription/switch/",
            content_type="application/json",
            data=json.dumps(
                {
                    "bk_username": "admin",
                    "bk_app_code": "blueking",
                    "subscription_id": subscription_id,
                    "action": "enable",
                }
            ),
        )

        assert r.status_code == 200
        assert r.data["result"]

        subscription = Subscription.objects.get(id=subscription_id)
        assert subscription.enable

    def test_subscription_update(self):
        subscription_id = self._test_create_subscription()
        self._test_get_subscription(subscription_id)
        self._test_update_subscription(subscription_id)

    def _test_run_subscription(self):
        self.run_task.apply_async.call_count = 0
        plugin_desc_data = dict(GSE_PLUGIN_DESC_DATA, **{"name": "mysql_exporter", "config_file": "config.yaml"})
        GsePluginDesc.objects.create(**plugin_desc_data)
        pac = Packages(
            pkg_name="test1.tar",
            version="2.3",
            module="gse_plugin",
            project="mysql_exporter",
            pkg_size=10255,
            pkg_path="/data/bkee/miniweb/download/windows/x86_64",
            location="http://127.0.0.1/download/windows/x86_64",
            md5="a95c530a7af5f492a74499e70578d150",
            pkg_ctime="2019-05-05 11:54:28.070771",
            pkg_mtime="2019-05-05 11:54:28.070771",
            os="linux",
            cpu_arch="x86_64",
            is_release_version=False,
            is_ready=True,
        )
        pac.save()
        PluginConfigTemplate.objects.create(
            plugin_name="mysql_exporter",
            plugin_version="*",
            name="config.yaml",
            version="2.3",
            format="yaml",
            file_path="etc",
            os="linux",
            cpu_arch="x86_64",
            content="sss",
            is_release_version=0,
            creator="admin",
            create_time="2019-06-25 15:26:25.051187",
            source_app_code="bk_monitor",
        )
        PluginConfigTemplate.objects.create(
            plugin_name="mysql_exporter",
            plugin_version="*",
            name="env.yaml",
            version="2.3",
            format="yaml",
            file_path="etc",
            content="sss",
            is_release_version=0,
            creator="admin",
            create_time="2019-06-25 15:26:25.051187",
            source_app_code="bk_monitor",
        )
        ProcControl.objects.create(
            id=142,
            module="gse_plugin",
            project="exp_1123",
            plugin_package_id=pac.id,
            install_path="/ usr / local / gse",
            log_path="/ var / log / gse",
            data_path="/ var / lib / gse",
            pid_path="/ var / run / gse / exp_1123.pid",
            start_cmd="./ start.sh",
            stop_cmd="./ stop.sh",
            restart_cmd="./ restart.sh",
            reload_cmd="./ reload.sh",
            kill_cmd="./kill.sh",
            version_cmd="cat VERSION",
            health_cmd="./heath.sh",
            debug_cmd="./ debug.sh",
            os="linux",
            process_name="",
            port_range="1-65535",
            need_delegate=True,
        )
        host = Host(
            bk_host_id=31,
            bk_biz_id=2,
            bk_cloud_id=0,
            inner_ip="127.0.0.1",
            outer_ip=None,
            login_ip="127.0.0.1",
            data_ip="127.0.0.1",
            os_type="LINUX",
            cpu_arch="x86_64",
            node_type="AGENT",
            ap_id=DEFAULT_AP_ID,
        )
        host.save()

        r = self.client.post(
            path="/backend/api/subscription/create/",
            content_type="application/json",
            data=json.dumps(self.CREATE_SUBSCRIPTION_DATA),
        )

        subscription_id = r.data["data"]["subscription_id"]
        manager = PluginManager(subscription_instance_ids=subscription_id, step=None)
        plugin_manager = mock.patch("apps.backend.plugin.manager.PluginManager").start()
        plugin_manager.return_value = manager

        # 确认创建订阅步骤
        SubscriptionStep.objects.get(subscription_id=subscription_id)

        status = ProcessStatus(
            id=324,
            name="mysql_exporter",
            status="RUNNING",
            is_auto="AUTO",
            version=3.3,
            proc_type="AGENT",
            configs=[
                {
                    "instance_id": 206,
                    "content": "# \u901a\u7528\u914d\u7f6e\nGSE_AGENT_HOME: /usr/local/gse\nBK_PLUGIN_LOG_PATH: "
                    "u53c2\u6570\nBK_CMD_ARGS: --web.listen-address127.0.0",
                    "file_path": "/usr/test",
                    "name": "test",
                }
            ],
            listen_ip="127.0.0.1",
            listen_port=9947,
            setup_path="/usr/local/gse/external_plugins/sub_458_service_31/exp_1123",
            log_path="/var/log/gse/sub_458_service_31",
            data_path="/var/lib/gse/sub_458_service_31",
            pid_path="/var/run/gse/sub_458_service_31/exp_1123.pid",
            group_id="sub_458_service_31",
            source_type="subscription",
            source_id=subscription_id,
            bk_host_id=host.bk_host_id,
        )
        status.save()

        r = self.client.post(
            path="/backend/api/subscription/run/",
            content_type="application/json",
            data=json.dumps(
                {
                    "bk_username": "admin",
                    "bk_app_code": "blueking",
                    "scope": {
                        "node_type": "INSTANCE",
                        "nodes": [
                            {
                                "ip": "127.0.0.1",
                                "bk_cloud_id": "0",
                                "bk_supplier_id": "0",
                                "bk_obj_id": "biz",
                                "bk_inst_id": 32,
                            }
                        ],
                    },
                    "actions": {"my_first": "INSTALL"},
                    "subscription_id": subscription_id,
                }
            ),
        )
        # self.assertEqual(run_task.apply_async.call_count, 1)
        # 确认订阅任务创建
        task = SubscriptionTask.objects.get(subscription_id=subscription_id)
        # Host已存在bk_host_id优先用于生成实例id
        assert task.actions["host|instance|host|1"]["my_first"] == "INSTALL"
        task_id = r.data["data"]["task_id"]
        return subscription_id, task_id

    def _test_task_result(self, subscription_id, task_id):
        r = self.client.post(
            path="/backend/api/subscription/task_result/",
            content_type="application/json",
            data=json.dumps(
                {
                    "bk_username": "admin",
                    "bk_app_code": "blueking",
                    "subscription_id": subscription_id,
                    "task_id_list": [task_id],
                }
            ),
        )

        self.assertEqual(len(r.data["data"]), 1)
        data = r.data["data"][0]
        self.assertEqual(data["instance_id"], "host|instance|host|1")

    def _test_instance_status(self, subscription_id):
        r = self.client.post(
            path="/backend/api/subscription/instance_status/",
            content_type="application/json",
            data=json.dumps(
                {"subscription_id_list": [subscription_id], "bk_username": "admin", "bk_app_code": "blueking"}
            ),
        )
        self.assertEqual(r.data["data"][0]["subscription_id"], subscription_id)

    def test_run_task(self):
        subscription_id, task_id = self._test_run_subscription()
        self._test_task_result(subscription_id, task_id)
        self._test_instance_status(subscription_id)

    def test_delete_subscription(self):
        subscription_id = self._test_create_subscription()

        subscription = Subscription.objects.get(id=subscription_id)
        self.assertEqual(subscription.is_deleted, False)

        r = self.client.post(
            path="/backend/api/subscription/delete/",
            content_type="application/json",
            data=json.dumps({"bk_username": "admin", "bk_app_code": "blueking", "subscription_id": subscription_id}),
        )

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["result"], True)

        subscription = Subscription.objects.get(id=subscription_id, is_deleted=True)
        self.assertEqual(subscription.is_deleted, True)


class TestPolicyWithLatestVersion(TestPolicy):

    CREATE_SUBSCRIPTION_DATA = copy.deepcopy(DEFEAULT_CREATE_SUBSCRIPTION_DATA)
    for step in CREATE_SUBSCRIPTION_DATA["steps"]:
        step["config"]["plugin_version"] = "latest"
        for config_template in step["config"]["config_templates"]:
            config_template["version"] = "latest"
