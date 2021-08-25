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
from typing import Dict

from mock import MagicMock

from apps.backend.api.constants import JobDataStatus, JobIPStatus


def api_success_return(data):
    return {"result": True, "data": data}


TASK_ID = 10000

JOB_CLIENT_MOCK_PATH = "apps.backend.api.job.get_client_by_user"

JOB_VERSION_MOCK_PATH = "apps.backend.api.job.settings.JOB_VERSION"

CORE_FILES_JOB_API_PATH = "apps.core.files.base.JobApi"

JOB_EXECUTE_TASK_RETURN = {
    "result": True,
    "code": 0,
    "message": "success",
    "data": {"job_instance_name": "API Quick Distribution File1521101427176", "job_instance_id": TASK_ID},
}

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
                            "retry_count": 0,
                            "total_time": 60.599,
                            "start_time": "2020-08-05 14:39:30 +0800",
                            "end_time": "2020-08-05 14:40:31 +0800",
                            "ip": "127.0.0.1",
                            "bk_cloud_id": 0,
                            "error_code": 0,
                            "exit_code": 0,
                            "log_content": "success",
                        }
                    ],
                }
            ],
        }
    ],
}


class JobMockClient(object):
    def __init__(
        self,
        push_config_file_return=None,
        get_job_instance_log_return=None,
        fast_execute_script_return=None,
        fast_push_file_return=None,
    ):
        self.job = MagicMock()
        self.job.push_config_file = MagicMock(return_value=push_config_file_return)
        self.job.get_job_instance_log = MagicMock(return_value=get_job_instance_log_return)
        self.job.fast_execute_script = MagicMock(return_value=fast_execute_script_return)
        self.job.fast_push_file = MagicMock(return_value=fast_push_file_return)


# JobApi Mock
# 和 JobMockClient 的区别：1. 获取接口方式-client.job.api / JobApi.api  2.JobApi 仅返回 data
class JobV3MockApi:
    fast_transfer_file_return = JOB_EXECUTE_TASK_RETURN["data"]

    def __init__(self, fast_transfer_file_return: Dict = None):
        self.fast_transfer_file = MagicMock(return_value=fast_transfer_file_return or self.fast_transfer_file_return)
