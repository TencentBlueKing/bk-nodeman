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

from apps.node_man import constants

JOB_MODEL_DATA = {
    "id": 1295,
    "created_by": "admin",
    "job_type": constants.JobType.MAIN_INSTALL_PLUGIN,
    "subscription_id": 1,
    "task_id_list": [1, 2],
    "start_time": "2021-07-09 05:03:40.842797+00:00",
    "end_time": "2021-07-09 05:03:49.226500+00:00",
    "status": constants.JobStatusType.SUCCESS,
    "global_params": {},
    "statistics": {
        "total_count": 5,
        "failed_count": 0,
        "ignored_count": 0,
        "pending_count": 0,
        "running_count": 0,
        "success_count": 5,
    },
    "bk_biz_scope": [1, 2, 3],
    "error_hosts": [],
    "is_auto_trigger": False,
}
