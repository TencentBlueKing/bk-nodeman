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

from mock import MagicMock

from apps.backend.api.constants import GseDataErrCode

TASK_ID = 10000

GSE_CLIENT_MOCK_PATH = "apps.backend.api.gse.get_client_by_user"

GSE_TASK_RESULT = {
    "success": [
        {
            "content": "",
            "error_code": 0,
            "error_msg": "success",
            "bk_cloud_id": "0",
            "bk_supplier_id": "0",
            "ip": "127.0.0.1",
        }
    ],
    "pending": [],
    "failed": [
        {
            "content": "",
            "error_code": 850,
            "error_msg": "Fail to register, for the process info already exists.",
            "bk_cloud_id": "0",
            "bk_supplier_id": "0",
            "ip": "127.0.0.1",
        }
    ],
}

UPDATE_PROC_INFO_RETURN = {
    "result": True,
    "code": 0,
    "message": "success",
    "data": {
        "0:0:127.0.0.1:nodeman:sub_870_host_1_host_exp001": {
            "error_code": GseDataErrCode.SUCCESS,
            "error_msg": "success",
            "content": "",
        },
        "0:0:127.0.0.1:nodeman:sub_870_host_1_host_exp002": {
            "error_code": GseDataErrCode.ALREADY_REGISTERED,
            "error_msg": "Fail to register, for the process info already exists.",
            "content": "",
        },
    },
}

OPERATE_PROC_RETURN = {"result": True, "code": 0, "message": "success", "data": {"task_id": TASK_ID}}

GET_PROC_OPERATE_RESULT_RETURN = {
    "result": True,
    "code": 0,
    "message": "success",
    "data": {
        "0:0:127.0.0.1:nodeman:sub_870_host_1_host_exp001": {
            "error_code": GseDataErrCode.SUCCESS,
            "error_msg": "success",
            "content": "",
        },
        "0:0:127.0.0.1:nodeman:sub_870_host_1_host_exp002": {
            "error_code": GseDataErrCode.ALREADY_REGISTERED,
            "error_msg": "Fail to register, for the process info already exists.",
            "content": "",
        },
    },
}

MOCK_GET_PROC_STATUS = {
    "proc_infos": [
        {
            "host": {"ip": "127.0.0.1", "bk_cloud_id": 0},
            "status": 1,
            "version": "1.1.13",
            "isauto": True,
            "meta": {"name": "test_proc", "namespace": "nodeman", "labels": {"proc_name": "test_proc"}},
        }
    ]
}


class GseMockClient(object):
    def __init__(
        self,
        update_proc_info_return=None,
        unregister_proc_info_return=None,
        operate_proc_return=None,
        get_proc_operate_result_return=None,
        get_proc_status_return=None,
    ):
        self.gse = MagicMock()
        self.gse.update_proc_info = MagicMock(return_value=update_proc_info_return)
        self.gse.unregister_proc_info = MagicMock(return_value=unregister_proc_info_return)
        self.gse.operate_proc = MagicMock(return_value=operate_proc_return)
        self.gse.get_proc_operate_result = MagicMock(return_value=get_proc_operate_result_return)
        self.gse.get_proc_status = MagicMock(return_value=get_proc_status_return)
