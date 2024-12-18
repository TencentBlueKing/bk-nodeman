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

import datetime
import math
import os
from functools import wraps

import mock
from django.test import TestCase
from six.moves import range

from apps.backend.subscription.tasks import (
    run_subscription_task,
    run_subscription_task_and_create_instance,
)
from apps.backend.subscription.tools import get_subscription_task_instance_status
from apps.backend.utils.pipeline_parser import PipelineParser
from apps.mock_data.backend_mkd.subscription.unit import (
    GSE_PLUGIN_DESC_DATA,
    SUBSCRIPTION_DATA,
)
from apps.node_man import models
from common.log import logger

IS_OPEN_PERFORMANCE_UNITTEST = os.environ.get("IS_OPEN_PERFORMANCE_UNITTEST", False)

mocked_instance = {
    "process": {
        "gse_task": {
            "bk_func_id": "",
            "protocol": "1",
            "create_time": "2019-07-09T13:06:54.209+08:00",
            "bind_ip": "",
            "proc_num": 0,
            "last_time": "2019-07-09T13:06:54.209+08:00",
            "description": "",
            "port": ",48668,48671,48329",
            "priority": 0,
            "pid_file": "",
            "auto_time_gap": 0,
            "stop_cmd": "",
            "timeout": 0,
            "bk_process_id": 115,
            "bk_process_name": "gse_task",
            "start_cmd": "",
            "user": "",
            "face_stop_cmd": "",
            "bk_biz_id": 2,
            "bk_func_name": "gse_task",
            "work_path": "/data/bkee",
            "reload_cmd": "",
            "auto_start": False,
            "bk_supplier_account": "0",
            "metadata": {"label": {"bk_biz_id": "2"}},
            "restart_cmd": "",
        }
    },
    "scope": [{"bk_obj_id": "test", "bk_inst_id": 2}],
    "host": {
        "bk_cpu": 8,
        "bk_isp_name": "1",
        "bk_os_name": "linux centos",
        "bk_province_name": "440000",
        "bk_host_id": 1,
        "import_from": "2",
        "bk_os_version": "7.4.1708",
        "bk_disk": 245,
        "operator": "",
        "docker_server_version": "1.12.4",
        "create_time": "2019-05-17T12:40:29.212+08:00",
        "bk_mem": 32012,
        "bk_host_name": "VM_1_10_centos",
        "last_time": "2019-05-17T15:53:10.164+08:00",
        "bk_host_innerip": "127.0.0.1",
        "bk_comment": "",
        "docker_client_version": "1.12.4",
        "bk_os_bit": "64-bit",
        "bk_outer_mac": "",
        "bk_asset_id": "",
        "bk_service_term": None,
        "bk_cloud_id": 0,
        "bk_sla": None,
        "bk_cpu_mhz": 2499,
        "bk_host_outerip": "",
        "bk_sn": "",
        "bk_os_type": "1",
        "bk_mac": "52:54:00:0a:ac:26",
        "bk_bak_operator": "",
        "bk_supplier_account": "0",
        "bk_state_name": "CN",
        "bk_cpu_module": "Intel(R) Xeon(R) Gold 61xx CPU",
    },
    "service": {
        "bk_module_id": 50,
        "name": "gse_task",
        "creator": "cc_system",
        "service_category_id": 10,
        "bk_host_id": 1,
        "last_time": "2019-07-09T13:06:54.207+08:00",
        "create_time": "2019-07-09T13:06:54.207+08:00",
        "bk_supplier_account": "0",
        "service_template_id": 9,
        "modifier": "cc_system",
        "id": 5,
        "metadata": {"label": {"bk_biz_id": "2"}},
    },
}


class SubscriptionRunner(object):
    def __init__(self, params=None, subscription_id=None):
        self.params = params
        if not subscription_id:
            self.subscription = self.create_subscription(params)
        else:
            self.subscription = models.Subscription.objects.get(id=subscription_id)
        models.ProcessStatus.objects.filter(source_id=self.subscription.id, source_type="subscription").delete()
        models.SubscriptionInstanceRecord.objects.filter(subscription_id=self.subscription.id).delete()
        # 创建订阅任务记录
        self.subscription_task = models.SubscriptionTask.objects.create(
            subscription_id=self.subscription.id, scope=self.subscription.scope, actions={}
        )
        run_subscription_task_and_create_instance(self.subscription, self.subscription_task)
        # from django.db import connection
        # q = connection.queries
        self.instance_records = models.SubscriptionInstanceRecord.objects.filter(task_id=self.subscription_task.id)

    @classmethod
    def create_subscription(cls, params):
        scope = params["scope"]
        subscription = models.Subscription.objects.create(
            bk_biz_id=scope["bk_biz_id"],
            object_type=scope["object_type"],
            node_type=scope["node_type"],
            nodes=scope["nodes"],
            target_hosts=params.get("target_hosts"),
            from_system="blueking",
            enable=False,
            creator="admin",
        )
        models.SubscriptionStep.objects.filter(subscription_id=subscription.id).delete()

        # 创建订阅步骤
        steps = params["steps"]
        for index, step in enumerate(steps):
            models.SubscriptionStep.objects.create(
                subscription_id=subscription.id,
                index=index,
                step_id=step["id"],
                type=step["type"],
                config=step["config"],
                params=step["params"],
            )

        return subscription

    def run_subscription(self):
        run_subscription_task.delay(self.subscription_task)
        # time.sleep(1)

    def get_task_result(self):
        # 查询这些任务下的全部instance记录
        pipeline_ids = [r.pipeline_id for r in self.instance_records]
        pipeline_parser = PipelineParser(pipeline_ids)
        result = []
        for instance_record in self.instance_records:
            result.append(get_subscription_task_instance_status(instance_record, pipeline_parser))
        return result


def run_subscription(runners):
    # from multiprocessing import Pool
    # pool = Pool(processes=100)
    # pool = dummy.Pool(processes=1)
    for runner in runners:
        # pool.apply_async(runner.run_subscription)
        runner.run_subscription()


def print_with_time(msg):
    print("[{}] {}".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg))


def get_percentile(data, percentile):
    size = len(data)
    return sorted(data)[int(math.ceil((size * percentile) / 100)) - 1]


def unitest_operation(is_open):
    def inner_task(func):
        @wraps(func)
        def inner(*args, **kwargs):
            if is_open in [True, "True", "true"]:
                func(*args, **kwargs)
            else:
                logger.info(f"escape [{func.__str__()}] unitest")

        return inner

    return inner_task


class TestPerformance(TestCase):
    get_instances_by_scope_patch = mock.patch("apps.backend.subscription.tasks.tools.get_instances_by_scope")
    run_pipeline_patch = mock.patch("pipeline.service.task_service.run_pipeline")

    @classmethod
    def mock_get_instance_by_scope(cls, instance_num):
        def get_instances_by_scope(scope, data_backend, *args, **kwargs):
            if scope["nodes"]:
                mocked_instances = {}
                for i in range(instance_num):
                    mocked_instances["service|instance|service|%s" % i] = mocked_instance
                return mocked_instances
            return {}

        # mock
        instance_scope_function = cls.get_instances_by_scope_patch.start()
        instance_scope_function.side_effect = get_instances_by_scope

    @classmethod
    def mock_run_pipeline(cls):
        # mock
        run_pipeline_function = cls.run_pipeline_patch.start()
        run_pipeline_function.side_effect = lambda x: None

    def setUp(self):
        desc_params = dict(GSE_PLUGIN_DESC_DATA, **{"name": "nodeman_performance_test", "config_file": "config.yaml"})
        models.GsePluginDesc.objects.create(**desc_params)
        desc_params["name"] = "bkmonitorbeat"
        models.GsePluginDesc.objects.create(**desc_params)

        pkg = models.Packages.objects.create(
            pkg_name="test1.tar",
            version="1.1",
            module="gse_plugin",
            project="nodeman_performance_test",
            pkg_size=10255,
            pkg_path="/data/bkee/miniweb/download/windows/x86_64",
            location="http://127.0.0.1/download/windows/x86_64",
            md5="a95c530a7af5f492a74499e70578d150",
            pkg_ctime="2019-05-05 11:54:28.070771",
            pkg_mtime="2019-05-05 11:54:28.070771",
            os="windows",
            cpu_arch="x86_64",
            is_release_version=False,
            is_ready=True,
        )
        pkg2 = models.Packages.objects.create(
            pkg_name="bkmonitorbeat.tar",
            version="1.2",
            module="gse_plugin",
            project="bkmonitorbeat",
            pkg_size=10255,
            pkg_path="/data/bkee/miniweb/download/windows/x86_64",
            location="http://127.0.0.1/download/windows/x86_64",
            md5="a95c530a7af5f492a74499e70578d150",
            pkg_ctime="2019-05-05 11:54:28.070771",
            pkg_mtime="2019-05-05 11:54:28.070771",
            os="windows",
            cpu_arch="x86_64",
            is_release_version=False,
            is_ready=True,
        )

        template_params = dict(
            plugin_name="nodeman_performance_test",
            plugin_version="*",
            is_main=False,
            is_release_version=True,
            creator="admin",
            source_app_code="bk_nodeman",
            name="env.yaml",
            version="1",
            format="yaml",
            file_path="1/1",
            content="",
        )
        models.PluginConfigTemplate.objects.create(**template_params)
        template_params.update(plugin_name="bkmonitorbeat", name="bkmonitorbeat_script.conf")
        models.PluginConfigTemplate.objects.create(**template_params)

        models.Host.objects.create(
            bk_host_id=1,
            bk_biz_id=2,
            bk_cloud_id=0,
            inner_ip="127.0.0.1",
            outer_ip=None,
            login_ip="127.0.0.1",
            data_ip="127.0.0.1",
            os_type="WINDOWS",
            node_type="AGENT",
            ap_id=1,
        )

        ctrl_params = dict(
            module="gse_plugin",
            project="exp_1123",
            plugin_package_id=pkg.id,
            install_path="/usr/local/gse",
            log_path="/var/log/gse",
            data_path="/var/lib/gse",
            pid_path="/var/run/gse/exp_1123.pid",
            start_cmd="./start.sh",
            stop_cmd="./stop.sh",
            restart_cmd="./restart.sh",
            reload_cmd="./reload.sh",
            kill_cmd="./kill.sh",
            version_cmd="cat VERSION",
            health_cmd="./heath.sh",
            debug_cmd="./debug.sh",
            os="linux",
            process_name="",
            port_range="1-65535",
            need_delegate=True,
        )
        models.ProcControl.objects.create(**ctrl_params)
        ctrl_params["plugin_package_id"] = pkg2.id
        models.ProcControl.objects.create(**ctrl_params)

    # 性能单元测试停止，这里的teardown也应该同步停止
    @unitest_operation(is_open=IS_OPEN_PERFORMANCE_UNITTEST)
    def tearDown(self):
        # 关闭mock，避免对其他单测造成干扰
        self.get_instances_by_scope_patch.stop()
        self.run_pipeline_patch.stop()

    @unitest_operation(is_open=IS_OPEN_PERFORMANCE_UNITTEST)
    def test_performance(self):
        task_num = 1
        instance_num = 100000

        begin_time = datetime.datetime.now()
        self.mock_get_instance_by_scope(instance_num)
        self.mock_run_pipeline()

        runners = []

        print_with_time("Creating Task...")

        for subscription_id in range(task_num):
            runner = SubscriptionRunner(SUBSCRIPTION_DATA)
            runners.append(runner)

        end_time = datetime.datetime.now()

        print(f"创建TASK[{task_num}], INSTANCE[{instance_num}] 耗时： {end_time - begin_time}s.")
