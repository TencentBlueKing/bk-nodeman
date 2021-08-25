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
import uuid
from copy import deepcopy

from mock import patch

from apps.backend.api.constants import OS, JobDataStatus, JobIPStatus
from apps.backend.components.collections.bulk_job import (
    JobBulkPushFileComponent,
    SchedulePollType,
)
from apps.backend.tests.components.collections.agent import utils as agent_utils
from apps.backend.tests.components.collections.job import utils
from apps.node_man import constants, models
from apps.utils.unittest.testcase import CustomBaseTestCase
from pipeline.component_framework.test import (
    ComponentTestCase,
    ComponentTestMixin,
    ExecuteAssertion,
    Patcher,
    ScheduleAssertion,
)

JOB_GET_INSTANCE_LOG_RETURN = {
    "result": True,
    "code": 0,
    "message": "",
    "data": [
        {
            "is_finished": True,
            "step_instance_id": 90000,
            "name": "test",
            "status": JobDataStatus.SUCCESS,
            "step_results": [
                {
                    "ip_status": JobIPStatus.SUCCESS,
                    "tag": "xxx",
                    "ip_logs": [
                        {
                            "ip": "127.0.0.1",
                            "bk_cloud_id": 0,
                            "error_code": 0,
                            "exit_code": 0,
                            "log_content": "success",
                        },
                        {
                            "ip": "127.0.0.2",
                            "bk_cloud_id": 0,
                            "error_code": 0,
                            "exit_code": 0,
                            "log_content": "success",
                        },
                        {
                            "ip": "127.0.0.3",
                            "bk_cloud_id": 0,
                            "error_code": 0,
                            "exit_code": 0,
                            "log_content": "success",
                        },
                    ],
                }
            ],
        }
    ],
}

push_file_record_params = {
    "subscription_id": 1,
    "task_id": 1,
    "bk_cloud_id": 0,
    "os_type": constants.OsType.LINUX,
    "file_source_path": "/data/dev_pipeline_unit_test",
    # 可变参数
    "ip": "127.0.0.2",
    "record_id": 1,
}


class RedisMockLock:
    def __init__(self, lock_name):
        self.lock_name = lock_name

    def __enter__(self):
        return str(uuid)

    def __exit__(self, exc_type, exc_val, exc_tb):
        return True


class JobBulkPushFileComponentTestCase(CustomBaseTestCase, ComponentTestMixin):

    PUSH_FILE_RECORD_ID = 1

    JOB_CLIENT = {"bk_biz_id": 2, "username": "admin", "os_type": OS.LINUX}

    IP_LIST = ["127.0.0.1", "127.0.0.2"]

    TASK_RESULT = {
        "success": [
            {"ip": "127.0.0.1", "bk_cloud_id": 0, "log_content": "success", "error_code": 0, "exit_code": 0},
            {"ip": "127.0.0.2", "bk_cloud_id": 0, "log_content": "success", "error_code": 0, "exit_code": 0},
            {"ip": "127.0.0.3", "bk_cloud_id": 0, "log_content": "success", "error_code": 0, "exit_code": 0},
        ],
        "pending": [],
        "failed": [],
    }

    JOB_FAST_PUSH_FILE = {
        "subscription_id": 1,
        "task_id": 1,
        "instance_id": "host|instance|host|127.0.0.3-0-0",
        "os_type": constants.OsType.LINUX,
        "job_client": JOB_CLIENT,
        "host_info": {"ip": "127.0.0.3", "bk_supplier_id": 0, "bk_cloud_id": 0},
        "file_target_path": "/data/",
        "file_source": [{"files": ["/data/dev_pipeline_unit_test"]}],
    }

    POLLING_TIMEOUT_MOCK_PATH = "apps.backend.components.collections.bulk_job.TRIGGER_THRESHOLD"

    REDIS_LOCK_MOCK_PATH = "apps.backend.components.collections.bulk_job.RedisLock"

    def setUp(self):
        self.job_client = utils.JobMockClient(
            fast_push_file_return=utils.JOB_EXECUTE_TASK_RETURN,
            get_job_instance_log_return=JOB_GET_INSTANCE_LOG_RETURN,
        )
        patch(utils.CORE_FILES_JOB_API_PATH, utils.JobV3MockApi()).start()
        patch(utils.JOB_VERSION_MOCK_PATH, "V3").start()
        # 设置小阈值，直接触发批量分发
        patch(self.POLLING_TIMEOUT_MOCK_PATH, 2).start()
        patch(self.REDIS_LOCK_MOCK_PATH, RedisMockLock).start()
        inst_record_params = agent_utils.AgentTestObjFactory.subscription_instance_record_obj(
            obj_attr_values={"subscription_id": 1, "task_id": 1, "instance_id": "host|instance|host|127.0.0.3-0-0"}
        )

        inst_record_obj = models.SubscriptionInstanceRecord.objects.create(**inst_record_params)

        # 分发文件存量
        for index, ip in enumerate(self.IP_LIST):
            record_params = deepcopy(push_file_record_params)
            record_params["record_id"] = index + inst_record_obj.id
            record_params["ip"] = ip
            record = models.PushFileRecord.objects.create(**record_params)
            self.PUSH_FILE_RECORD_ID = record.id + 1

    def component_cls(self):
        # return the component class which should be tested
        return JobBulkPushFileComponent

    def cases(self):
        # return your component test cases here
        return [
            ComponentTestCase(
                name="测试批量分发文件执行成功",
                inputs=self.JOB_FAST_PUSH_FILE,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=True,
                    outputs={
                        "polling_time": 0,
                        "push_file_record_id": self.PUSH_FILE_RECORD_ID,
                        "schedule_poll_type": SchedulePollType.TRIGGER_JOB,
                    },
                ),
                schedule_assertion=[
                    ScheduleAssertion(
                        # 触发下发文件，此时轮询时间重置并切换到轮询作业状态
                        success=True,
                        outputs={
                            "polling_time": 0,
                            "schedule_poll_type": SchedulePollType.POLL_FILE_PUSH_STATUS,
                            "push_file_record_id": self.PUSH_FILE_RECORD_ID,
                        },
                        schedule_finished=False,
                        callback_data=None,
                    ),
                    ScheduleAssertion(
                        success=True,
                        outputs={
                            "polling_time": 5,
                            "schedule_poll_type": SchedulePollType.POLL_FILE_PUSH_STATUS,
                            "push_file_record_id": self.PUSH_FILE_RECORD_ID,
                            "task_result": self.TASK_RESULT,
                        },
                        schedule_finished=False,
                        callback_data=None,
                    ),
                    ScheduleAssertion(
                        success=True,
                        outputs={
                            "polling_time": 5,
                            "schedule_poll_type": SchedulePollType.POLL_FILE_PUSH_STATUS,
                            "push_file_record_id": self.PUSH_FILE_RECORD_ID,
                            "task_result": self.TASK_RESULT,
                        },
                        schedule_finished=True,
                        callback_data=None,
                    ),
                ],
                patchers=[Patcher(target=utils.JOB_CLIENT_MOCK_PATH, return_value=self.job_client)],
            )
        ]
