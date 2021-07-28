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

import abc
import logging

import six
import ujson as json

from apps.backend.api.constants import POLLING_INTERVAL, POLLING_TIMEOUT, GseDataErrCode
from apps.backend.api.gse import GseClient
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service, StaticIntervalGenerator

logger = logging.getLogger("app")


class GseBaseService(six.with_metaclass(abc.ABCMeta, Service)):
    """
    GSE Service 基类
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(POLLING_INTERVAL)

    ACTION = ""

    def _append_log_context(self, msg, log_context):
        prefix = ""
        if isinstance(log_context, dict):
            prefix = ", ".join("{}({})".format(key, value) for key, value in log_context.items())
            prefix += " "
        return prefix + msg

    def log_info(self, msg, log_context=None):
        logger.info(self._append_log_context(msg, log_context))
        self.logger.info(msg)

    def log_error(self, msg, log_context=None):
        logger.error(self._append_log_context(msg, log_context))
        self.logger.error(msg)

    def log_warning(self, msg, log_context=None):
        logger.warning(self._append_log_context(msg, log_context))
        self.logger.warning(msg)

    def log_debug(self, msg, log_context=None):
        logger.debug(self._append_log_context(msg, log_context))
        # self.logger.debug(msg)

    @staticmethod
    def format_error_msg(task_result):
        msg = []
        for host in task_result["failed"]:
            if host.get("error_code", -1) == 836:
                # 无法从注册的控制信息中读取到pidfile
                msg.append("[{}] 操作指引：请尝试更新至插件最新版本。 错误信息: {}".format(host["ip"], host.get("error_msg")))
            else:
                msg.append("[{}] 错误信息: {}".format(host["ip"], host.get("error_msg")))

        return ",".join(msg)

    def execute(self, data, parent_data):
        gse_client = GseClient(_logger=self.logger, **data.get_one_of_inputs("gse_client"))
        hosts = data.get_one_of_inputs("hosts")
        control = data.get_one_of_inputs("control")
        setup_path = data.get_one_of_inputs("setup_path")
        pid_path = data.get_one_of_inputs("pid_path")
        proc_name = data.get_one_of_inputs("proc_name")
        exe_name = data.get_one_of_inputs("exe_name")
        log_context = data.get_one_of_inputs("context")

        result = gse_client.register_process(hosts, control, setup_path, pid_path, proc_name, exe_name)
        if result["failed"]:
            data.outputs.result = result  # result字段存注册结果
            self.log_error(
                "GSE register process failed. result:\n[{}]".format(json.dumps(result, indent=2)),
                log_context,
            )
            data.outputs.ex_data = "以下主机注册进程失败：{}".format(
                ",".join(["[{}] {}".format(host["ip"], host.get("error_msg")) for host in result["failed"]])
            )
            return False
        # self.log_info('GSE register process success. result->[{}]'.format(json.dumps(result, indent=2)), log_context)
        self.log_info("GSE register process success.", log_context)
        # 从 GSE Client 获取相应的动作
        operate_method = getattr(gse_client, "{}_process".format(self.ACTION))
        task_id = operate_method(hosts, proc_name)
        self.log_info(
            "GSE {} Process and get task_id: [{}]".format(self.ACTION.upper(), task_id),
            log_context,
        )
        data.outputs.task_id = task_id
        data.outputs.polling_time = 0
        return True

    def schedule(self, data, parent_data, callback_data=None):
        task_id = data.get_one_of_outputs("task_id")
        gse_client = GseClient(_logger=self.logger, **data.get_one_of_inputs("gse_client"))
        polling_time = data.get_one_of_outputs("polling_time")
        log_context = data.get_one_of_inputs("context")

        is_finished, task_result = gse_client.get_task_result(task_id)
        self.log_debug(
            "GSE(task_id: [{}]) get schedule task result:\n[{}].".format(task_id, json.dumps(task_result, indent=2)),
            log_context,
        )
        if is_finished:
            data.outputs.task_result = task_result  # task_result字段保存轮询结果
            self.finish_schedule()
            if task_result["failed"]:
                self.log_error(
                    "gse task(task_id: [{}]) failed. task_result:\n[{}]".format(
                        task_id, json.dumps(task_result, indent=2)
                    ),
                    log_context,
                )
                data.outputs.ex_data = "以下主机操作进程失败：{}".format(self.format_error_msg(task_result))
                return False
            self.log_info(
                "GSE(task_id: [{}]) get schedule finished].".format(task_id),
                log_context,
            )
            return True
        elif polling_time + POLLING_INTERVAL > POLLING_TIMEOUT:
            data.outputs.ex_data = "任务轮询超时"
            self.log_error("GSE(task_id: [{}]) schedule timeout.".format(task_id), log_context)
            return False

        data.outputs.polling_time = polling_time + POLLING_INTERVAL
        return True

    def inputs_format(self):
        return [
            Service.InputItem(name="gse_client", key="gse_client", type="dict", required=True),
            Service.InputItem(name="hosts", key="hosts", type="list", required=True),
            Service.InputItem(name="control", key="control", type="dict", required=True),
            Service.InputItem(name="setup_path", key="setup_path", type="str", required=True),
            Service.InputItem(name="pid_path", key="pid_path", type="str", required=True),
            Service.InputItem(name="proc_name", key="proc_name", type="str", required=True),
            Service.InputItem(name="exe_name", key="exe_name", type="str", required=True),
        ]

    def outputs_format(self):
        return [
            Service.OutputItem(name="task_id", key="task_id", type="int"),
            Service.OutputItem(name="polling_time", key="polling_time", type="int"),
            Service.OutputItem(name="task_result", key="task_result", type="dict"),
            Service.OutputItem(name="result", key="result", type="dict"),
        ]


class GseStartProcessService(GseBaseService):
    """
    GSE Service 注册并启动进程
    """

    ACTION = "start"


class GseRestartProcessService(GseBaseService):
    """
    GSE Service 注册并重启进程
    """

    ACTION = "restart"


class GseDelegateProcessService(GseBaseService):
    """
    GSE Service 托管进程
    """

    ACTION = "delegate"


class GseUnDelegateProcessService(GseBaseService):
    """
    GSE Service 取消托管进程
    """

    ACTION = "undelegate"


class GseReloadProcessService(GseBaseService):
    """
    GSE Service 注册并重载进程
    """

    ACTION = "reload"

    def execute(self, data, parent_data):
        gse_client = GseClient(_logger=self.logger, **data.get_one_of_inputs("gse_client"))
        hosts = data.get_one_of_inputs("hosts")
        control = data.get_one_of_inputs("control")
        setup_path = data.get_one_of_inputs("setup_path")
        pid_path = data.get_one_of_inputs("pid_path")
        proc_name = data.get_one_of_inputs("proc_name")
        exe_name = data.get_one_of_inputs("exe_name")
        log_context = data.get_one_of_inputs("context")

        result = gse_client.register_process(hosts, control, setup_path, pid_path, proc_name, exe_name)
        if result["failed"]:
            data.outputs.result = result  # result字段存注册结果
            self.log_error(
                "GSE register process failed. result:\n[{}]".format(json.dumps(result, indent=2)),
                log_context,
            )
            data.outputs.ex_data = "以下主机注册进程失败：{}".format(
                ",".join(["[{}] {}".format(host["ip"], host.get("error_msg")) for host in result["failed"]])
            )
            return False
        self.log_info("GSE register process success.", log_context)
        # 再查询进程状态
        task_id = gse_client.check_process(hosts, proc_name)
        data.outputs.task_id = task_id
        data.outputs.polling_time = 0
        data.outputs.action = "check"
        return True

    # 重写轮询，此处需要注销进程
    def schedule(self, data, parent_data, callback_data=None):
        task_id = data.get_one_of_outputs("task_id")
        hosts = data.get_one_of_inputs("hosts")
        proc_name = data.get_one_of_inputs("proc_name")
        gse_client = GseClient(_logger=self.logger, **data.get_one_of_inputs("gse_client"))
        polling_time = data.get_one_of_outputs("polling_time")
        log_context = data.get_one_of_inputs("context")

        is_finished, task_result = gse_client.get_task_result(task_id)
        self.log_debug(
            "GSE(task_id: [{}]) get schedule task result:\n[{}].".format(task_id, json.dumps(task_result, indent=2)),
            log_context,
        )
        if not is_finished:
            if polling_time > POLLING_TIMEOUT:
                self.log_error(
                    "GSE(task_id: [{}]) schedule polling timeout.".format(task_id),
                    log_context,
                )
                data.outputs.ex_data = "任务轮询超时"
                return False

            data.outputs.polling_time = polling_time + POLLING_INTERVAL
            return True

        data.outputs.task_result = task_result

        if data.outputs.action == "check":
            # 在检查进程阶段
            not_exist_hosts = []
            for host in task_result["success"]:
                try:
                    log_data = json.loads(host["content"])
                    cmd_line = log_data["process"][0]["instance"][0]["cmdline"]
                    if not cmd_line:
                        # 对应的进程不存在则认为失败
                        not_exist_hosts.append(host)
                except Exception:
                    not_exist_hosts.append(host)
            not_exist_hosts.extend(task_result["failed"])

            if not_exist_hosts:
                self.log_info(
                    "GSE check process not exists. result:\n[{}]".format(json.dumps(task_result, indent=2)),
                    log_context,
                )
                # 进程不存在，则启动
                data.outputs.action = "restart"
            else:
                self.log_info(
                    "GSE check process exists. result:\n[{}]".format(json.dumps(task_result, indent=2)),
                    log_context,
                )
                # 进程存在，则重载
                data.outputs.action = "reload"

            # 从 GSE Client 获取相应的动作
            operate_method = getattr(gse_client, "{}_process".format(data.outputs.action))
            task_id = operate_method(hosts, proc_name)
            data.outputs.task_id = task_id
        else:
            # 在重载进程阶段
            if task_result["failed"]:
                self.log_error(
                    "GSE {} process failed. task_id: [{}] task_result:\n[{}]".format(
                        data.outputs.action, task_id, json.dumps(task_result, indent=2)
                    ),
                    log_context,
                )
                data.outputs.ex_data = "以下主机操作进程失败：{}".format(self.format_error_msg(task_result))
                return False
            self.log_info(
                "GSE {} process success. task_id: [{}] task_result:\n[{}]".format(
                    data.outputs.action, task_id, json.dumps(task_result, indent=2)
                ),
                log_context,
            )
            self.finish_schedule()

        return True


class GseStopProcessService(GseBaseService):
    """
    GSE Service 关闭并注销进程
    """

    ACTION = "stop"

    # 重写轮询，此处需要注销进程
    def schedule(self, data, parent_data, callback_data=None):
        task_id = data.get_one_of_outputs("task_id")
        gse_client = GseClient(_logger=self.logger, **data.get_one_of_inputs("gse_client"))
        polling_time = data.get_one_of_outputs("polling_time")
        log_context = data.get_one_of_inputs("context")

        is_finished, task_result = gse_client.get_task_result(task_id)
        self.log_debug(
            "GSE(task_id: [{}]) get schedule task result:\n[{}].".format(task_id, json.dumps(task_result, indent=2)),
            log_context,
        )
        if is_finished:
            self.finish_schedule()
            self.log_info(
                "GSE(task_id: [{}]) get schedule finished task result:\n[{}].".format(
                    task_id, json.dumps(task_result, indent=2)
                ),
                log_context,
            )
            data.outputs.task_result = task_result
            # 停止进程结果处理
            failed_task_result = []
            for fail in task_result["failed"]:
                if fail["error_code"] == GseDataErrCode.NON_EXIST:
                    continue
                failed_task_result.append(fail)
                self.log_error(
                    "GseStopProcessService stop process failed:\n[{}]".format(json.dumps(fail, indent=2)),
                    log_context,
                )
            if failed_task_result:
                data.outputs.ex_data = "以下主机停止进程失败：{}".format(
                    ",".join(["[{}] {}".format(host["ip"], host.get("error_msg")) for host in failed_task_result])
                )
                return False

        elif polling_time + POLLING_INTERVAL > POLLING_TIMEOUT:
            self.log_error(
                "GseStopProcessService(task_id: [{}]) schedule timeout.".format(task_id),
                log_context,
            )
            data.outputs.ex_data = "任务轮询失败"
            return False

        data.outputs.polling_time = polling_time + POLLING_INTERVAL
        return True


class GseStartProcessComponent(Component):
    name = "GseStartProcessComponent"
    code = "gse_start_process"
    bound_service = GseStartProcessService


class GseRestartProcessComponent(Component):
    name = "GseRestartProcessComponent"
    code = "gse_restart_process"
    bound_service = GseRestartProcessService


class GseStopProcessComponent(Component):
    name = "GseStopProcessComponent"
    code = "gse_stop_process"
    bound_service = GseStopProcessService


class GseReloadProcessComponent(Component):
    name = "GseReloadProcessComponent"
    code = "gse_reload_process"
    bound_service = GseReloadProcessService


class GseDelegateProcessComponent(Component):
    name = "GseDelegateProcessComponent"
    code = "gse_delegate_process"
    bound_service = GseDelegateProcessService


class GseUnDelegateProcessComponent(Component):
    name = "GseDelegateProcessComponent"
    code = "gse_undelegate_process"
    bound_service = GseUnDelegateProcessService
