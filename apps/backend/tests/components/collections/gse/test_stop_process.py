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

from apps.backend.api.constants import OS, POLLING_INTERVAL, GseDataErrCode
from apps.backend.components.collections.gse import GseStopProcessComponent
from apps.backend.tests.components.collections.gse import utils
from pipeline.component_framework.test import (
    ComponentTestCase,
    ComponentTestMixin,
    ExecuteAssertion,
    Patcher,
    ScheduleAssertion,
)


class GseStopProcessComponentTestCase(TestCase, ComponentTestMixin):
    GSE_CLIENT = {"username": "admin", "os_type": OS.LINUX}
    STOP_PROCESS_INPUTS = {
        "gse_client": GSE_CLIENT,
        "proc_name": "sub_870_host_1_host_exp002",
        "hosts": [{"ip": "127.0.0.1", "bk_supplier_id": 0, "bk_cloud_id": 0}],
    }
    GSE_UNREGISTER_RESULT = {
        "0:0:127.0.0.1:nodeman:sub_870_host_1_host_exp002": {"content": "", "error_code": 0, "error_msg": ""}
    }

    GSE_TASK_RESULT = {
        "success": [
            {
                "content": "",
                "error_code": 0,
                "error_msg": "",
                "bk_cloud_id": "0",
                "bk_supplier_id": "0",
                "ip": "127.0.0.1",
            }
        ],
        "pending": [],
        "failed": [],
    }

    STOP_PROCESS_RESPONSE = {
        "message": "success",
        "code": 0,
        "data": {
            "0:0:127.0.0.1:nodeman:sub_870_host_1_host_exp002": {
                "content": "",
                "error_code": GseDataErrCode.SUCCESS,
                "error_msg": "",
            }
        },
        "result": True,
        "request_id": "1aebe780547a4ee296a15f4a19018aad",
    }

    def setUp(self):
        self.gse_client = utils.GseMockClient(
            update_proc_info_return=self.STOP_PROCESS_RESPONSE,
            unregister_proc_info_return=self.STOP_PROCESS_RESPONSE,
            operate_proc_return=utils.OPERATE_PROC_RETURN,
            get_proc_operate_result_return=self.STOP_PROCESS_RESPONSE,
        )

    def component_cls(self):
        # return the component class which should be tested
        return GseStopProcessComponent

    def cases(self):
        # return your component test cases here

        return [
            ComponentTestCase(
                name="测试成功关闭并注销进程",
                inputs=self.STOP_PROCESS_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(success=True, outputs={"task_id": utils.TASK_ID, "polling_time": 0}),
                schedule_assertion=ScheduleAssertion(
                    success=True,
                    outputs={
                        "task_id": utils.TASK_ID,
                        "polling_time": POLLING_INTERVAL,
                        "task_result": self.GSE_TASK_RESULT,
                    },
                    callback_data=None,
                    schedule_finished=True,
                ),
                patchers=[Patcher(target=utils.GSE_CLIENT_MOCK_PATH, return_value=self.gse_client)],
            )
        ]
