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

from apps.node_man import constants
from apps.node_man.models import ProcessStatus

MOCK_PROC_NAME = "test_proc"
MOCK_HOST = {
    "bk_biz_id": 0,
    "bk_host_id": 2147483640,
    "inner_ip": "127.0.0.1",
    "bk_cloud_id": 0,
}
MOCK_PROC_STATUS = {
    "status": constants.ProcStateType.TERMINATED,
    "is_latest": True,
    "bk_host_id": MOCK_HOST["bk_host_id"],
    "name": MOCK_PROC_NAME,
    "source_type": ProcessStatus.SourceType.DEFAULT,
    "proc_type": constants.ProcType.PLUGIN,
}
MOCK_GET_PROC_STATUS = {
    "proc_infos": [
        {
            "host": {"ip": MOCK_HOST["inner_ip"], "bk_cloud_id": MOCK_HOST["bk_cloud_id"]},
            "status": 1,
            "version": "1.1.13",
            "isauto": True,
            "meta": {"name": MOCK_PROC_NAME, "namespace": "nodeman", "labels": {"proc_name": MOCK_PROC_NAME}},
        }
    ]
}
