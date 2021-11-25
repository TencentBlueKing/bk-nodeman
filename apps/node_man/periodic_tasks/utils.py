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
import logging
import time
from collections import defaultdict

import ujson as json
from django.conf import settings

from apps.backend.api.constants import POLLING_INTERVAL, POLLING_TIMEOUT, JobIPStatus
from apps.backend.api.errors import JobPollTimeout
from common.api import JobApi

logger = logging.getLogger("app")


class JobDemand(object):
    @classmethod
    def poll_task_result(cls, job_instance_id: int):
        """
        轮询直到任务完成
        :param job_instance_id: job任务id
        :return: 与 get_task_result 同
        """
        polling_time = 0
        result = cls.get_task_result(job_instance_id)
        while not result["is_finished"]:
            if polling_time > POLLING_TIMEOUT:
                logger.error(
                    "user->[{}] called api->[get_task_result] but got JobExecuteTimeout.".format(
                        settings.BACKEND_JOB_OPERATOR
                    )
                )
                raise JobPollTimeout({"job_instance_id": job_instance_id})

            # 每次查询后，睡觉
            polling_time += POLLING_INTERVAL
            time.sleep(POLLING_INTERVAL)

            result = cls.get_task_result(job_instance_id)

        return result

    @classmethod
    def get_task_result(cls, job_instance_id: int):
        """
        获取执行结果
        :param job_instance_id: job任务id
        :return: example: {
                    "success": [
                        {
                            'ip': 127.0.0.1,
                            'bk_cloud_id': 0,
                            'log_content': 'xx',
                        }
                    ],
                    "pending": [],
                    "failed": []
                }
        """
        params = {
            "job_instance_id": job_instance_id,
            "bk_biz_id": settings.BLUEKING_BIZ_ID,
            "bk_username": settings.BACKEND_JOB_OPERATOR,
            "return_ip_result": True,
        }
        job_status = JobApi.get_job_instance_status(params)
        is_finished = job_status["finished"]
        host_infos__gby_job_status = defaultdict(list)
        step_instance_id = job_status["step_instance_list"][0]["step_instance_id"]
        for instance in job_status["step_instance_list"][0]["step_ip_result_list"]:
            host_info = {"ip": instance["ip"], "bk_cloud_id": instance["bk_cloud_id"]}
            host_infos__gby_job_status[instance["status"]].append(host_info)
        logger.info(
            "user->[{}] called api->[{}] and got response->[{}].".format(
                settings.BACKEND_JOB_OPERATOR, job_instance_id, json.dumps(job_status)
            )
        )

        task_result = {
            "success": [],
            "pending": [],
            "failed": [],
        }
        for status, hosts in host_infos__gby_job_status.items():
            if status == JobIPStatus.SUCCESS:
                key = "success"
            elif status in (
                JobIPStatus.WAITING_FOR_EXEC,
                JobIPStatus.RUNNING,
            ):
                key = "pending"
            else:
                key = "failed"

            for host in hosts:
                log_params = {
                    "job_instance_id": job_instance_id,
                    "bk_biz_id": settings.BLUEKING_BIZ_ID,
                    "bk_username": settings.BACKEND_JOB_OPERATOR,
                    "step_instance_id": step_instance_id,
                    "ip": host["ip"],
                    "bk_cloud_id": host["bk_cloud_id"],
                }
                log_result = JobApi.get_job_instance_ip_log(log_params)
                task_result[key].append(
                    {
                        "ip": host["ip"],
                        "bk_cloud_id": host["bk_cloud_id"],
                        "log_content": log_result["log_content"],
                    }
                )
        return {"is_finished": is_finished, "task_result": task_result}
