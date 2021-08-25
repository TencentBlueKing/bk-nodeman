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

from django.conf import settings
from django.utils import timezone
from mock import patch

from apps.backend.components.collections.bulk_job import SchedulePollType
from apps.backend.components.collections.bulk_job_redis import (
    REDIS_INST,
    JobBulkPushFileV2Component,
    JobBulkPushFileV2Service,
)
from apps.backend.tests.components.collections.bulk_job import test_bulk_push_file
from apps.backend.tests.components.collections.job import utils
from apps.node_man import constants
from pipeline.component_framework.test import (
    ComponentTestCase,
    ExecuteAssertion,
    Patcher,
    ScheduleAssertion,
)


class JobBulkPushFileV2ComponentTestCase(test_bulk_push_file.JobBulkPushFileComponentTestCase):
    """
    该单测需要依赖Redis验证批量分发功能
    运行该测试请确保环境已运行Redis
    """

    ACTION_NAME = "BULK_PUSH_FILE_V2"
    REDIS_CACHE_PREFIX = f"nodeman:v2:{ACTION_NAME.lower()}"

    def setUp(self):
        self.job_client = utils.JobMockClient(
            fast_push_file_return=utils.JOB_EXECUTE_TASK_RETURN,
            get_job_instance_log_return=test_bulk_push_file.JOB_GET_INSTANCE_LOG_RETURN,
        )
        patch(utils.JOB_VERSION_MOCK_PATH, "V3").start()
        # 设置小阈值，直接触发批量分发
        patch(self.POLLING_TIMEOUT_MOCK_PATH, 2).start()
        patch(utils.CORE_FILES_JOB_API_PATH, utils.JobV3MockApi()).start()

        self.task_id = test_bulk_push_file.push_file_record_params["task_id"]
        self.hash_ip_status_key = f"{self.REDIS_CACHE_PREFIX}:task_id:{self.task_id}:ip:status"
        self.hash_ip_job_instance_id_key = f"{self.REDIS_CACHE_PREFIX}:task_id:{self.task_id}:ip:job_instance_id"
        self.hash_job_last_poll_time_key = f"{self.REDIS_CACHE_PREFIX}:task_id:{self.task_id}:last_poll_time"

        file_paths_md5 = JobBulkPushFileV2Service.get_md5(
            "|".join(sorted(self.JOB_FAST_PUSH_FILE["file_source"][0]["files"]))
        )
        self.zset_source_files_wait_key = (
            f"{self.REDIS_CACHE_PREFIX}:bk_biz_id:{settings.BLUEKING_BIZ_ID}"
            f":task_id:{self.task_id}:file_paths_md5:{file_paths_md5}:wait"
        )

        REDIS_INST.delete(
            self.hash_ip_status_key,
            self.hash_ip_job_instance_id_key,
            self.hash_job_last_poll_time_key,
            self.zset_source_files_wait_key,
        )

        # 分发文件存量
        for index, ip in enumerate(self.IP_LIST):
            # 初始化等待分发ip状态
            ip_info_str = JobBulkPushFileV2Service.ip_info_str({"ip": ip, "bk_cloud_id": 0})
            REDIS_INST.hset(name=self.hash_ip_status_key, key=ip_info_str, value=constants.JobIpStatusType.not_job)
            REDIS_INST.zadd(self.zset_source_files_wait_key, timezone.now().timestamp(), ip_info_str)

        # 验证存量
        self.assertEqual(REDIS_INST.zcard(self.zset_source_files_wait_key), 2)

    def tearDown(self):
        # 检查等待队列是否清空
        self.assertEqual(REDIS_INST.zcard(self.zset_source_files_wait_key), 0)
        REDIS_INST.delete(
            self.hash_ip_status_key,
            self.hash_ip_job_instance_id_key,
            self.hash_job_last_poll_time_key,
            self.zset_source_files_wait_key,
        )

    def component_cls(self):
        # return the component class which should be tested
        return JobBulkPushFileV2Component

    def cases(self):
        # return your component test cases here
        return [
            ComponentTestCase(
                name="测试批量分发文件[Redis优化版本]执行成功",
                inputs=self.JOB_FAST_PUSH_FILE,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=True,
                    outputs={
                        "polling_time": 0,
                        "schedule_poll_type": SchedulePollType.TRIGGER_JOB,
                        "bk_biz_id": settings.BLUEKING_BIZ_ID,
                    },
                ),
                schedule_assertion=[
                    ScheduleAssertion(
                        # 触发下发文件，此时轮询时间重置并切换到轮询作业状态
                        success=True,
                        outputs={
                            "polling_time": 0,
                            "schedule_poll_type": SchedulePollType.POLL_FILE_PUSH_STATUS,
                            "bk_biz_id": settings.BLUEKING_BIZ_ID,
                        },
                        schedule_finished=False,
                        callback_data=None,
                    ),
                    ScheduleAssertion(
                        success=True,
                        outputs={
                            "polling_time": 5,
                            "schedule_poll_type": SchedulePollType.POLL_FILE_PUSH_STATUS,
                            "bk_biz_id": settings.BLUEKING_BIZ_ID,
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
                            "bk_biz_id": settings.BLUEKING_BIZ_ID,
                            "task_result": self.TASK_RESULT,
                        },
                        schedule_finished=True,
                        callback_data=None,
                    ),
                ],
                patchers=[Patcher(target=utils.JOB_CLIENT_MOCK_PATH, return_value=self.job_client)],
            )
        ]
