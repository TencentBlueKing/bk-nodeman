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
import mock
from django.test import TestCase

from apps.backend.api.constants import OS
from apps.backend.api.job import JobClient


class TestJob(TestCase):
    JOB_INIT = {"bk_biz_id": 2, "username": "admin", "os_type": OS.LINUX}
    PUSH_CONFIG_FILE = {
        "ip_list": [{"ip": "127.0.0.1", "bk_supplier_id": 0, "bk_cloud_id": 0}],
        "file_target_path": "/data",
        "file_list": [{"name": "dev_pipeline_unit_test", "content": "unit test"}],
    }

    PUSH_CONFIG_FILE_JOB_RESPONSE = {
        "message": "success",
        "code": 0,
        "data": {"job_instance_id": 25209, "job_instance_name": "API GSE PUSH FILE1565598068887"},
        "result": True,
        "request_id": "68bd5224bebe4bec9bd018a09f6b115c",
    }

    PUSH_CONFIG_FILE_JOB_INSTANCE_LOG = {
        "message": "success",
        "code": 0,
        "data": [
            {
                "status": 3,
                "step_results": [
                    {
                        "tag": "",
                        "ip_logs": [
                            {
                                "total_time": 0.001,
                                "ip": "127.0.0.1",
                                "start_time": "2019-08-12 16:24:36 +0800",
                                "log_content": "\u30102019-08-12 16:24:37.027\u3011 \u3010Upload source files\u3011"
                                "FileName\uff1adev_pipeline_unit_test  FileSize\uff1a9.0 Byte  "
                                "State\uff1aupload  Speed\uff1a1KB/s  Progress\uff1a100%  Detail"
                                "\uff1aSuccess\n\u30102019-08-12 16:24:37.027\u3011 FileName\uff1a"
                                "/data/dev_pipeline_unit_test  FileSize\uff1a9.0 Byte  State\uff1a"
                                "download  Speed\uff1a1KB/s  Progress\uff1a100%  Detail\uff1asucc\n",
                                "exit_code": 0,
                                "bk_cloud_id": 0,
                                "retry_count": 0,
                                "end_time": "2019-08-12 16:24:36 +0800",
                                "error_code": 0,
                            }
                        ],
                        "ip_status": 9,
                    }
                ],
                "is_finished": True,
                "step_instance_id": 33075,
                "name": "API GSE PUSH FILE1565598275635",
            }
        ],
        "result": True,
        "request_id": "cd4b97a55e394f67893048f947895396",
    }

    FAST_EXECUTE_SCRIPT = {
        "ip_list": [{"ip": "127.0.0.1", "bk_supplier_id": 0, "bk_cloud_id": 0}],
        "script_content": "ls",
        "script_param": "./",
        "script_timeout": 3000,
    }

    FAST_EXECUTE_SCRIPT_JOB_RESPONSE = {
        "message": "success",
        "code": 0,
        "data": {
            "job_instance_id": 25239,
            "job_instance_name": "\u5185\u7f6e\u4efb\u52a1\u6a21\u677f|Monitor System Task",
        },
        "result": True,
        "request_id": "20f539ce06504644b63f66f88824b4ff",
    }

    FAST_EXECUTE_SCRIPT_JOB_INSTANCE_LOG = {
        "message": "success",
        "code": 0,
        "data": [
            {
                "status": 3,
                "step_results": [
                    {
                        "tag": "",
                        "ip_logs": [
                            {
                                "total_time": 0.0,
                                "ip": "127.0.0.1",
                                "log_content": "",
                                "exit_code": 0,
                                "bk_cloud_id": 0,
                                "retry_count": 0,
                                "error_code": 0,
                            }
                        ],
                        "ip_status": 9,
                    }
                ],
                "is_finished": True,
                "step_instance_id": 33119,
                "name": "monitor_script",
            }
        ],
        "result": True,
        "request_id": "945e985a043b4d66b88fde1e596ed7a4",
    }

    FAST_PUSH_FILE = {
        "ip_list": [{"ip": "127.0.0.1", "bk_supplier_id": 0, "bk_cloud_id": 0}],
        "file_target_path": "/data/",
        "file_source": [
            {
                "files": ["/data/dev_pipeline_unit_test"],
                "account": "root",
                "ip_list": [{"bk_cloud_id": 0, "ip": "127.0.0.1", "bk_supplier_id": 0}],
            }
        ],
    }

    FAST_PUSH_FILE_JOB_RESPONSE = {
        "message": "success",
        "code": 0,
        "data": {"job_instance_id": 25250, "job_instance_name": "API Quick Distribution File1565607846461"},
        "result": True,
        "request_id": "abb328ad2db1480f97a6cfc6295a7ac5",
    }

    FAST_PUSH_FILE_JOB_INSTANCE_LOG = {
        "message": "success",
        "code": 0,
        "data": [
            {
                "status": 3,
                "step_results": [
                    {
                        "tag": "",
                        "ip_logs": [
                            {
                                "total_time": 0.001,
                                "ip": "127.0.0.1",
                                "start_time": "2019-08-12 19:04:07 +0800",
                                "log_content": "\u30102019-08-12 19:04:07.757\u3011 FileName\uff1a/data/dev_"
                                "pipeline_unit_test  FileSize\uff1a9.0 Byte  State\uff1adownload"
                                "  Speed\uff1a1KB/s  Progress\uff1a100%  Detail\uff1asucc\n\u3010"
                                "2019-08-12 19:04:07.757\u3011 FileName\uff1a/data/dev_pipeline_"
                                "unit_test  FileSize\uff1a9.0 Byte  State\uff1aupload  Speed\uff1a"
                                "1KB/s  Progress\uff1a100%  Detail\uff1aSuccess\n",
                                "exit_code": 0,
                                "bk_cloud_id": 0,
                                "retry_count": 0,
                                "end_time": "2019-08-12 19:04:07 +0800",
                                "error_code": 0,
                            }
                        ],
                        "ip_status": 9,
                    }
                ],
                "is_finished": True,
                "step_instance_id": 33148,
                "name": "API Quick Distribution File1565607846461",
            }
        ],
        "result": True,
        "request_id": "7ef168e42a384e90a38e2d1966858ee5",
    }

    def test_push_config_file(self):
        job = JobClient(**self.JOB_INIT)
        job.client.job.push_config_file = mock.MagicMock(return_value=self.PUSH_CONFIG_FILE_JOB_RESPONSE)
        job.client.job.get_job_instance_log = mock.MagicMock(return_value=self.PUSH_CONFIG_FILE_JOB_INSTANCE_LOG)

        job_instance_id = job.push_config_file(**self.PUSH_CONFIG_FILE)
        assert job_instance_id
        is_finished, task_result = job.poll_task_result(job_instance_id)
        assert is_finished
        assert len(task_result["success"]) == 1
        assert set(task_result["success"][0].keys()) == {
            "ip",
            "log_content",
            "bk_cloud_id",
            "error_code",
            "exit_code",
        }
        assert task_result["pending"] == []
        assert task_result["failed"] == []

    def test_fast_execute_script(self):
        job = JobClient(**self.JOB_INIT)
        job.client.job.execute_platform_job = mock.MagicMock(return_value=self.FAST_EXECUTE_SCRIPT_JOB_RESPONSE)
        job.client.job.fast_execute_script = mock.MagicMock(return_value=self.FAST_EXECUTE_SCRIPT_JOB_RESPONSE)
        job.client.job.get_job_instance_log = mock.MagicMock(return_value=self.FAST_EXECUTE_SCRIPT_JOB_INSTANCE_LOG)

        job_instance_id = job.fast_execute_script(**self.FAST_EXECUTE_SCRIPT)
        assert job_instance_id
        is_finished, task_result = job.poll_task_result(job_instance_id)
        assert is_finished
        assert len(task_result["success"]) == 1
        assert set(task_result["success"][0].keys()) == {
            "ip",
            "log_content",
            "bk_cloud_id",
            "error_code",
            "exit_code",
        }
        assert task_result["pending"] == []
        assert task_result["failed"] == []

    @mock.patch(
        "apps.core.files.base.JobApi.fast_transfer_file",
        mock.MagicMock(return_value=FAST_PUSH_FILE_JOB_RESPONSE["data"]),
    )
    def test_fast_push_file(self):
        job = JobClient(**self.JOB_INIT)
        job.client.job.execute_platform_job = mock.MagicMock(return_value=self.FAST_PUSH_FILE_JOB_RESPONSE)
        job.client.job.get_job_instance_log = mock.MagicMock(return_value=self.FAST_PUSH_FILE_JOB_INSTANCE_LOG)

        job_instance_id = job.fast_push_file(**self.FAST_PUSH_FILE)
        assert job_instance_id
        is_finished, task_result = job.poll_task_result(job_instance_id)
        assert is_finished
        assert len(task_result["success"]) == 1
        assert set(task_result["success"][0].keys()) == {
            "ip",
            "log_content",
            "bk_cloud_id",
            "error_code",
            "exit_code",
        }
        assert task_result["pending"] == []
        assert task_result["failed"] == []
