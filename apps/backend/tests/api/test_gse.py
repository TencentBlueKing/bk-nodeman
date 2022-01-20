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
import mock
from django.test import TestCase

from apps.backend.api.constants import OS, GseOpType
from apps.backend.api.gse import GseClient


class TestGse(TestCase):
    GSE_INIT = {"username": "admin", "os_type": OS.LINUX}

    REGISTER_PROCESS = {
        "proc_name": "sub_870_host_1_host_exp002",
        "hosts": [{"ip": "127.0.0.1", "bk_supplier_id": 0, "bk_cloud_id": 0}],
        "control": {
            "stop_cmd": "./stop.sh",
            "health_cmd": "",
            "reload_cmd": "./reload.sh",
            "start_cmd": "./start.sh",
            "version_cmd": "cat VERSION",
            "kill_cmd": "",
            "restart_cmd": "./restart.sh",
        },
        "exe_name": "host_exp002",
        "setup_path": "/usr/local/gse/external_plugins/sub_870_host_1/host_exp002",
        "pid_path": "/var/run/gse/sub_870_host_1/host_exp002.pid",
    }

    REGISTER_PROCESS_RESPONSE = {
        "message": "success",
        "code": 0,
        "data": {"0:0:127.0.0.1:nodeman:sub_870_host_1_host_exp002": {"content": "", "error_code": 0, "error_msg": ""}},
        "result": True,
        "request_id": "1aebe780547a4ee296a15f4a19018aad",
    }

    OPERATE_PROCESS = {
        "proc_name": "sub_870_host_1_host_exp002",
        "hosts": [{"ip": "127.0.0.1", "bk_supplier_id": 0, "bk_cloud_id": 0}],
        "op_type": GseOpType.START,
    }

    OPERATE_PROCESS_RESPONSE = {
        "result": True,
        "message": "success",
        "code": 0,
        "data": {"task_id": "GSETASK:XXXXXXXXXX"},
    }

    TASK_ID = "GSETASK:20190813145456:8"

    GET_PROC_OPERATE_RESULT = {
        "message": "",
        "code": 0,
        "data": {
            "0:0:127.0.0.1:nodeman:sub_870_host_1_host_exp002": {
                "content": '{\n   "value" : [\n      {\n         "funcID" : "",\n'
                '         "instanceID" : "",\n        '
                ' "procName" : "host_exp002",\n         "result" : "success",\n'
                '         "setupPath" : "/usr/local/gse/external_plugins/sub_870'
                '_host_1/host_exp002"\n      }\n   ]\n}\n',
                "error_code": 0,
                "error_msg": "success",
            }
        },
        "result": True,
        "request_id": "82db2b079a72466abfe719a1a2c1cad2",
    }

    UNREGISTER_PROCESS = {
        "proc_name": "sub_870_host_1_host_exp002",
        "hosts": [{"ip": "127.0.0.1", "bk_supplier_id": 0, "bk_cloud_id": 0}],
    }

    UNREGISTER_PROCESS_RESPONSE = {
        "message": "success",
        "code": 0,
        "data": {"0:0:127.0.0.1:nodeman:sub_870_host_1_host_exp002": {"content": "", "error_code": 0, "error_msg": ""}},
        "result": True,
        "request_id": "1aebe780547a4ee296a15f4a19018aad",
    }

    def test_register_process(self):
        gse = GseClient(**self.GSE_INIT)
        gse.client.gse.update_proc_info = mock.MagicMock(return_value=self.REGISTER_PROCESS_RESPONSE)

        result = gse.register_process(**self.REGISTER_PROCESS)
        assert result["success"][0]["ip"] == self.REGISTER_PROCESS["hosts"][0]["ip"]
        assert set(result["success"][0].keys()) == {
            "bk_cloud_id",
            "bk_supplier_id",
            "ip",
            "content",
            "error_code",
            "error_msg",
        }
        assert not result["failed"]

    def test_operate_process(self):
        gse = GseClient(**self.GSE_INIT)
        gse.client.gse.operate_proc = mock.MagicMock(return_value=self.OPERATE_PROCESS_RESPONSE)

        task_id = gse.operate_process(**self.OPERATE_PROCESS)
        assert task_id == self.OPERATE_PROCESS_RESPONSE["data"]["task_id"]

    def test_poll_task_result(self):
        gse = GseClient(**self.GSE_INIT)
        gse.client.gse.get_proc_operate_result = mock.MagicMock(return_value=self.GET_PROC_OPERATE_RESULT)

        is_finished, task_result = gse.poll_task_result(self.TASK_ID)
        assert is_finished
        assert not task_result["pending"]
        assert not task_result["failed"]
        assert set(task_result["success"][0].keys()) == {
            "bk_cloud_id",
            "bk_supplier_id",
            "ip",
            "content",
            "error_code",
            "error_msg",
        }

    def test_unregister_process(self):
        gse = GseClient(**self.GSE_INIT)
        gse.client.gse.unregister_proc_info = mock.MagicMock(return_value=self.UNREGISTER_PROCESS_RESPONSE)

        result = gse.unregister_process(**self.UNREGISTER_PROCESS)
        assert result["success"][0]["ip"] == self.REGISTER_PROCESS["hosts"][0]["ip"]
        assert set(result["success"][0].keys()) == {
            "bk_cloud_id",
            "bk_supplier_id",
            "ip",
            "content",
            "error_code",
            "error_msg",
        }
        assert not result["failed"]
