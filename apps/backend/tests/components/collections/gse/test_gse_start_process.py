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

from django.test import TestCase

from apps.backend.api.constants import OS
from apps.backend.components.collections.gse import GseStartProcessComponent
from apps.backend.tests.components.collections.gse import utils
from pipeline.component_framework.test import (
    ComponentTestCase,
    ComponentTestMixin,
    ExecuteAssertion,
    Patcher,
    ScheduleAssertion,
)


class GseStartProcessComponentTestCase(TestCase, ComponentTestMixin):
    GSE_CLIENT = {"username": "admin", "os_type": OS.LINUX}
    GSE_START_PROCESS = {
        "gse_client": GSE_CLIENT,
        "proc_name": "sub_870_host_1_host_exp002",
        "hosts": [{"ip": "127.0.0.1", "bk_supplier_id": 0, "bk_cloud_id": 0}],
        "control": {
            "stop_cmd": "./stop.sh",
            "health_cmd": "",
            "reload_cmd": "./reload.sh",
            "start_cmd": "./start.sh",
            "version_cmd": "cat VERSION",
            "kill_cmd": "",
            "restart_cmd": "./restart.sh",
        },
        "exe_name": "host_exp002",
        "setup_path": "/usr/local/gse/external_plugins/sub_870_host_1/host_exp002",
        "pid_path": "/var/run/gse/sub_870_host_1/host_exp002.pid",
    }

    GSE_TASK_RESULT = {
        "success": [
            {"ip": "127.0.0.1", "bk_cloud_id": 0, "bk_supplier_id": 0, "error_code": 0, "error_msg": "", "content": ""}
        ],
        "pending": [],
        "failed": [],
    }

    def setUp(self):
        self.gse_client = utils.GseMockClient(
            update_proc_info_return=utils.UPDATE_PROC_INFO_RETURN,
            operate_proc_return=utils.OPERATE_PROC_RETURN,
            get_proc_operate_result_return=utils.GET_PROC_OPERATE_RESULT_RETURN,
        )

    def component_cls(self):
        # return the component class which should be tested
        return GseStartProcessComponent

    def cases(self):
        # return your component test cases here
        return [
            ComponentTestCase(
                name="测试开启主机进程失败",
                inputs=self.GSE_START_PROCESS,
                parent_data={},
                execute_assertion=ExecuteAssertion(success=True, outputs={"task_id": utils.TASK_ID, "polling_time": 0}),
                schedule_assertion=ScheduleAssertion(
                    success=False,
                    outputs={
                        "task_id": utils.TASK_ID,
                        "polling_time": 0,
                        "task_result": utils.GSE_TASK_RESULT,
                        "ex_data": "以下主机操作进程失败：[127.0.0.1] 错误信息: Fail to register,"
                        " for the process info already exists.",
                    },
                    callback_data=None,
                    schedule_finished=True,
                ),
                patchers=[Patcher(target=utils.GSE_CLIENT_MOCK_PATH, return_value=self.gse_client)],
            )
        ]
