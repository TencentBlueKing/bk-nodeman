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


from django.conf import settings

from apps.node_man import constants

from ... import utils

DEFAULT_JOB_INSTANCE_ID = 20012817742

DEFAULT_STEP_INSTANCE_ID = 20013319121

DEFAULT_JOB_INSTANCE_NAME = "NODE_MAN_1_TestService"

STEP_IP_RESULT = {
    "bk_cloud_id": constants.DEFAULT_CLOUD,
    "ip": utils.DEFAULT_IP,
    "status": constants.BkJobStatus.SUCCEEDED,
    # exit_code & error_code 为 0 表示正常
    "exit_code": 0,
    "error_code": 0,
    "tag": "",
    "total_time": 7888,
    "start_time": 1637135614160,
    "end_time": 1637135622048,
}

OP_DATA = {"job_instance_name": "job_test", "job_instance_id": DEFAULT_JOB_INSTANCE_ID}

GET_JOB_INSTANCE_STATUS_DATA = {
    "job_instance": {
        "job_instance_id": DEFAULT_JOB_INSTANCE_NAME,
        "bk_biz_id": settings.BLUEKING_BIZ_ID,
        "bk_scope_type": constants.BkJobScopeType.BIZ_SET.value,
        "bk_scope_id": settings.BLUEKING_BIZ_ID,
        "name": DEFAULT_JOB_INSTANCE_NAME,
        "start_time": 1637135613979,
        "create_time": 1637135613813,
        "status": constants.BkJobStatus.SUCCEEDED,
        "end_time": 1637135640958,
        "total_time": 26979,
    },
    "finished": True,
    "step_instance_list": [
        {
            "name": DEFAULT_JOB_INSTANCE_NAME,
            "status": constants.BkJobStatus.SUCCEEDED,
            "step_instance_id": DEFAULT_STEP_INSTANCE_ID,
            "total_time": 26884,
            "start_time": 1637135614127,
            "create_time": 1637135613813,
            "end_time": 1637135640894,
            "execute_count": 0,
            "type": 1,
            # 接口传入return_ip_result=True 时返回
            "step_ip_result_list": [STEP_IP_RESULT],
        },
    ],
}

GET_JOB_INSTANCE_IP_LOG_DATA = {
    "ip": utils.DEFAULT_IP,
    "log_content": "you can pass",
    "log_type": 1,
    "bk_cloud_id": constants.DEFAULT_CLOUD,
    "file_logs": None,
}
