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
from mock import patch

from apps.backend.api.constants import OS
from apps.backend.components.collections.job import JobPushConfigFileComponent
from apps.backend.tests.components.collections.job import utils
from pipeline.component_framework.test import (
    ComponentTestCase,
    ComponentTestMixin,
    ExecuteAssertion,
    Patcher,
    ScheduleAssertion,
)


class JobPushConfigFileComponentTestCase(TestCase, ComponentTestMixin):
    JOB_CLIENT = {"bk_biz_id": 2, "username": "admin", "os_type": OS.LINUX}

    TASK_RESULT = {
        "success": [{"ip": "127.0.0.1", "bk_cloud_id": 0, "log_content": "success", "error_code": 0, "exit_code": 0}],
        "pending": [],
        "failed": [],
    }
    JOB_PUSH_CONFIG_FILE = {
        "job_client": JOB_CLIENT,
        "ip_list": [{"ip": "127.0.0.1", "bk_supplier_id": 0, "bk_cloud_id": 0}],
        "file_target_path": "/data",
        "file_list": [{"name": "dev_pipeline_unit_test", "content": "unit test"}],
    }

    def setUp(self):
        self.job_client = utils.JobMockClient(
            push_config_file_return=utils.JOB_EXECUTE_TASK_RETURN,
            get_job_instance_log_return=utils.JOB_GET_INSTANCE_LOG_RETURN,
        )
        patch(utils.JOB_VERSION_MOCK_PATH, "V3").start()

    def component_cls(self):
        # return the component class which should be tested
        return JobPushConfigFileComponent

    def cases(self):
        # return your component test cases here
        return [
            ComponentTestCase(
                name="测试成功上传本地文件",
                inputs=self.JOB_PUSH_CONFIG_FILE,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=True,
                    outputs={"job_instance_id": utils.TASK_ID, "polling_time": 0},
                ),
                schedule_assertion=ScheduleAssertion(
                    success=True,
                    outputs={"polling_time": 0, "task_result": self.TASK_RESULT, "job_instance_id": utils.TASK_ID},
                    callback_data=None,
                    schedule_finished=True,
                ),
                patchers=[Patcher(target=utils.JOB_CLIENT_MOCK_PATH, return_value=self.job_client)],
            )
        ]
