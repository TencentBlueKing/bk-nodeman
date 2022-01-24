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

import logging
import time

import ujson as json
from blueapps.utils.esbclient import get_client_by_user
from django.conf import settings

from . import constants
from .errors import EmptyResponseError, FalseResultError, GsePollTimeout

logger = logging.getLogger("app")


class GseClient(object):
    """
    GSE客户端封装类
    """

    DEFAULT_NAMESPACE = "nodeman"

    def __init__(self, username, os_type, _logger=None, **kwargs):
        """
        :param username: 用户名
        :param os_type: example: OS.LINUX
        """
        self.username = username
        self.os_type = os_type
        self.client = get_client_by_user(settings.BACKEND_GSE_OPERATOR)
        self.account = constants.ACCOUNT_MAP.get(os_type, "root")
        if _logger:
            self.logger = _logger
        else:
            self.logger = logger

    def _response_exception_filter(self, api_name, params, response):
        """
        响应异常过滤器
        :param api_name: example: client.gse.register_proc_info
        :param params: api参数
        :param response: 响应
        :return: response['result']
        """
        self.logger.info("call GSE api [{}] with params:\n[{}]".format(api_name, json.dumps(params, indent=2)))
        if not response:
            self.logger.error(
                "call GSE api [{}] with params:\n[{}]\nbut got no response.".format(
                    api_name, json.dumps(params, indent=2)
                )
            )
            raise EmptyResponseError({"api_name": api_name})
        if not response["result"]:
            if response["code"] == constants.GSE_RUNNING_TASK_CODE:
                # 查询的任务等待执行中，还未入到redis
                # 返回mock的IP数据，代表此任务正在运行中
                return {"0:0:127.0.0.1:nodeman:proc": {"content": "", "error_code": 115, "error_msg": "handling"}}
            self.logger.error(
                "call GSE api [{}] with params:\n[{}]\nbut an error:\n[FalseResultError] occurred."
                "Full response:\n[{}].".format(params, api_name, json.dumps(response, indent=2))
            )
            raise FalseResultError({"api_name": api_name, "error_message": response["message"]})
        return response["data"]

    def register_process(
        self, hosts, control, setup_path, pid_path, proc_name, exe_name=None, namespace="nodeman", start_check_secs=None
    ):
        """
        注册进程
        :param proc_name: 进程名
        :param hosts: 主机列表
               example: [
                   {
                       'ip': '127.0.0.1',
                       'bk_supplier_id': 0,
                       'bk_cloud_id': 0
                   }
               ]
        :param control: 进程控制信息
               example: {
                  "start_cmd": "./start.sh",
                  "stop_cmd": "./stop.sh",
                  "restart_cmd": "./restart.sh",
                  "reload_cmd": "./reload.sh",
                  "kill_cmd": "./kill.sh",
                  "version_cmd": "./version.sh",
                  "health_cmd": "./health.sh"
                }
        :param setup_path: 工作路径
        :param pid_path: pid文件全路径
        :param exe_name: 进程二进制文件名
        :param namespace: 命名空间，用于进程分组管理
        :param start_check_secs: 进程启动检查时间
        :return example: {
            'success': [{
                        'ip': '127.0.0.1'
                        'bk_cloud_id': 0,
                        'bk_supplier_id': 0,
                        'error_code': 0,
                        'error_msg': '',
                        'content': ''
                }],
            'failed': [{
                'ip': '127.0.0.1',
                'bk_cloud_id': 0,
                'bk_supplier_id': 0,
                'error_code': 850,
                'error_msg':' Fail to register, for the process info already exists.',
                'content': ''
            }]
        }
        """
        if not exe_name:
            exe_name = proc_name
        params = {
            "meta": {"labels": {"proc_name": proc_name}, "namespace": namespace, "name": proc_name},
            "hosts": hosts,
            "spec": {
                "control": control,
                "monitor_policy": {"auto_type": 1},
                "resource": {"mem": 10, "cpu": 10},
                "identity": {
                    "user": self.account,
                    "proc_name": exe_name,
                    "setup_path": setup_path,
                    "pid_path": pid_path,
                },
            },
        }

        # 上云windows适配
        if start_check_secs:
            params["spec"]["monitor_policy"]["start_check_secs"] = start_check_secs

        response = self.client.gse.update_proc_info(**params)
        data = self._response_exception_filter("client.gse.update_proc_info", params, response)
        result = {
            "success": [],
            "pending": [],
            "failed": [],
        }
        for key, value in data.items():
            bk_cloud_id, bk_supplier_id, ip = key.split(":")[:3]
            result_type = constants.GSE_TASK_RESULT_MAP.get(value["error_code"], "failed")
            if value["error_code"] == constants.GseDataErrCode.ALREADY_REGISTERED:
                result_type = "success"
            result_content = dict(value, bk_cloud_id=bk_cloud_id, bk_supplier_id=bk_supplier_id, ip=ip)
            result[result_type].append(result_content)

        return result

    def unregister_process(self, hosts, proc_name, namespace="nodeman"):
        params = {
            "meta": {"labels": {"proc_name": proc_name}, "namespace": namespace, "name": proc_name},
            "hosts": hosts,
        }
        response = self.client.gse.unregister_proc_info(**params)
        data = self._response_exception_filter("client.gse.unregister_proc_info", params, response)
        result = {
            "success": [],
            "pending": [],
            "failed": [],
        }
        for key, value in data.items():
            bk_cloud_id, bk_supplier_id, ip = key.split(":")[:3]
            result_type = constants.GSE_TASK_RESULT_MAP.get(value["error_code"], "failed")
            if value["error_code"] == constants.GseDataErrCode.PROC_NO_RUNNING:
                result_type = "success"
            result_content = dict(value, bk_cloud_id=bk_cloud_id, bk_supplier_id=bk_supplier_id, ip=ip)
            result[result_type].append(result_content)
        return result

    def operate_process(self, op_type, hosts, proc_name, namespace="nodeman"):
        """
        操作进程
        :param proc_name: 进程名称
        :param op_type: 操作类型 example: GseOpType.RESTART
        :param hosts: 主机列表
               example: [
                   {
                       'ip': '127.0.0.1',
                       'bk_supplier_id': 0,
                       'bk_cloud_id': 0
                   }
               ]
        :param namespace: 进程命名空间
        :return: task_id
        """
        params = {
            "meta": {"labels": {"proc_name": proc_name}, "namespace": namespace, "name": proc_name},
            "hosts": hosts,
            "op_type": op_type,
        }
        response = self.client.gse.operate_proc(**params)
        result = self._response_exception_filter("client.gse.operate_proc", params, response)
        return result["task_id"]

    def get_task_result(self, task_id):
        """
        获取GSE任务信息
        :param task_id: GSE任务id
        :return: example: True, {
                            'success': [{
                                'ip': '127.0.0.1'
                                'bk_cloud_id': 0
                                'bk_supplier_id': 0
                                'error_code': 0
                                'error_msg': ''
                                'content': ''
                            }],
                            'pending': [],
                            'failed': []
                          }
        """
        params = {"task_id": task_id}
        response = self.client.gse.get_proc_operate_result(**params)
        result = self._response_exception_filter("client.get_proc_operate_result", params, response)
        # logger.info('user->[{}] get task[{}] and got response->[{}].'.format(self.username,
        #                                                                      task_id, json.dumps(response, indent=2)))
        task_result = {
            "success": [],
            "pending": [],
            "failed": [],
        }
        for key, value in result.items():
            bk_cloud_id, bk_supplier_id, ip = key.split(":")[:3]
            result_type = constants.GSE_TASK_RESULT_MAP.get(value["error_code"], "failed")
            result_content = dict(value, bk_cloud_id=bk_cloud_id, bk_supplier_id=bk_supplier_id, ip=ip)
            task_result[result_type].append(result_content)
        if task_result["pending"]:
            is_finished = False
        else:
            is_finished = True
        return is_finished, task_result

    def poll_task_result(self, task_id):
        """
        轮询GSE任务，参数与返回值同get_task_result
        """
        polling_time = 0
        is_finished, task_result = self.get_task_result(task_id)
        while not is_finished:
            if polling_time > constants.POLLING_TIMEOUT:
                self.logger.error(
                    "call api [get_task_result] with task_id [{}] but got GsePollTimeout.".format(task_id)
                )
                raise GsePollTimeout({"task_id": task_id})

            # 每次查询后，睡觉
            polling_time += constants.POLLING_INTERVAL
            time.sleep(constants.POLLING_INTERVAL)

            is_finished, task_result = self.get_task_result(task_id)

        return is_finished, task_result

    def start_process(self, hosts, proc_name, namespace="nodeman"):
        """
        启动进程
        :param proc_name: 进程名称
        :param hosts: 主机列表
               example: [
                   {
                       'ip': '127.0.0.1',
                       'bk_supplier_id': 0,
                       'bk_cloud_id': 0
                   }
               ]
        :param namespace: 进程命名空间
        :return: task_id
        """
        return self.operate_process(constants.GseOpType.START, hosts, proc_name, namespace)

    def stop_process(self, hosts, proc_name, namespace="nodeman"):
        """
        关闭进程，参数和返回值同start_process
        """
        return self.operate_process(constants.GseOpType.STOP, hosts, proc_name, namespace)

    def restart_process(self, hosts, proc_name, namespace="nodeman"):
        """
        重启进程，参数和返回值同start_process
        """
        return self.operate_process(constants.GseOpType.RESTART, hosts, proc_name, namespace)

    def reload_process(self, hosts, proc_name, namespace="nodeman"):
        """
        重载进程，参数和返回值同start_process
        """
        return self.operate_process(constants.GseOpType.RELOAD, hosts, proc_name, namespace)

    def delegate_process(self, hosts, proc_name, namespace="nodeman"):
        """
        托管进程，参数和返回值同start_process
        """
        return self.operate_process(constants.GseOpType.DELEGATE, hosts, proc_name, namespace)

    def undelegate_process(self, hosts, proc_name, namespace="nodeman"):
        """
        取消托管进程，参数和返回值同start_process
        """
        return self.operate_process(constants.GseOpType.UNDELEGATE, hosts, proc_name, namespace)

    def check_process(self, hosts, proc_name, namespace="nodeman"):
        """
        检查进程状态，参数和返回值同start_process
        """
        return self.operate_process(constants.GseOpType.STATUS, hosts, proc_name, namespace)


class DummyGseClient(GseClient):
    TASK_RESULT = {
        "success": [{"ip": "127.0.0.1", "bk_cloud_id": 0, "content": "dummy-gse-task-content"}],
        "pending": [],
        "failed": [],
    }

    def register_process(
        self,
        hosts,
        control,
        setup_path,
        pid_path,
        proc_name,
        exe_name=None,
        namespace="nodeman",
    ):
        return self.TASK_RESULT

    def unregister_process(self, hosts, proc_name, namespace="nodeman"):
        return self.TASK_RESULT

    def operate_process(self, op_type, hosts, proc_name, namespace="nodeman"):
        return "dummy-gse-task-id"

    def get_task_result(self, task_id):
        return True, self.TASK_RESULT

    def start_process(self, hosts, proc_name, namespace="nodeman"):
        """
        启动进程
        :param proc_name: 进程名称
        :param hosts: 主机列表
               example: [
                   {
                       'ip': '127.0.0.1',
                       'bk_supplier_id': 0,
                       'bk_cloud_id': 0
                   }
               ]
        :param namespace: 进程命名空间
        :return: task_id
        """
        return self.operate_process(constants.GseOpType.START, hosts, proc_name, namespace)

    def stop_process(self, hosts, proc_name, namespace="nodeman"):
        """
        关闭进程，参数和返回值同start_process
        """
        return self.operate_process(constants.GseOpType.STOP, hosts, proc_name, namespace)

    def restart_process(self, hosts, proc_name, namespace="nodeman"):
        """
        重启进程，参数和返回值同start_process
        """
        return self.operate_process(constants.GseOpType.RESTART, hosts, proc_name, namespace)

    def reload_process(self, hosts, proc_name, namespace="nodeman"):
        """
        重载进程，参数和返回值同start_process
        """
        return self.operate_process(constants.GseOpType.RELOAD, hosts, proc_name, namespace)

    def check_process(self, hosts, proc_name, namespace="nodeman"):
        """
        检查进程状态，参数和返回值同start_process
        """
        return self.operate_process(constants.GseOpType.STATUS, hosts, proc_name, namespace)


# GseClient = DummyGseClient
