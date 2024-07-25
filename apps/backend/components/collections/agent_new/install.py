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
import base64
import binascii
import json
import os
import random
import re
import socket
import time
import typing
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from django.conf import settings
from django.utils import timezone, translation
from django.utils.translation import ugettext_lazy as _
from redis.client import Pipeline

from apps.backend.agent import solution_maker
from apps.backend.agent.tools import InstallationTools
from apps.backend.api.constants import POLLING_INTERVAL
from apps.backend.constants import (
    POWERSHELL_SERVICE_CHECK_SSHD,
    REDIS_AGENT_CONF_KEY_TPL,
    REDIS_INSTALL_CALLBACK_KEY_TPL,
    SSH_RUN_TIMEOUT,
)
from apps.backend.subscription.steps.agent_adapter.adapter import AgentStepAdapter
from apps.backend.utils.redis import REDIS_INST
from apps.backend.utils.wmi import execute_cmd, put_file
from apps.core.concurrent import controller
from apps.core.concurrent.retry import RetryHandler
from apps.core.remote import conns
from apps.exceptions import ApiResultError, AuthOverdueException, parse_exception
from apps.node_man import constants, models
from apps.prometheus import metrics
from apps.prometheus.helper import SetupObserve
from apps.utils import concurrent, sync
from apps.utils.exc import ExceptionHandler
from common.api import CCApi, JobApi
from common.log import logger
from pipeline.core.flow import Service, StaticIntervalGenerator

from .. import core
from ..base import LogLevel
from ..common import remote
from . import base


class InstallSubInstObj(remote.RemoteConnHelper):
    installation_tool: InstallationTools = None

    def __init__(self, sub_inst_id: int, host: models.Host, installation_tool: InstallationTools):
        self.installation_tool = installation_tool
        super().__init__(sub_inst_id=sub_inst_id, host=host, identity_data=installation_tool.identity_data)


def parse_common_labels_by_install_obj(
    method: str, params: typing.Dict[str, typing.Any]
) -> typing.Dict[str, typing.Any]:
    install_sub_inst_obj: InstallSubInstObj = params["install_sub_inst_obj"]
    common_labels: typing.Dict[str, typing.Any] = {
        "method": method,
        "username": install_sub_inst_obj.conns_init_params["username"],
        "port": install_sub_inst_obj.conns_init_params["port"],
        "auth_type": install_sub_inst_obj.identity_data.auth_type,
        "os_type": install_sub_inst_obj.host.os_type,
    }
    return common_labels


def parse_common_labels_by_host_identity(
    method: str, params: typing.Dict[str, typing.Any]
) -> typing.Dict[str, typing.Any]:
    host: models.Host = params["host"]
    identity_data: models.IdentityData = params["identity_data"]
    common_labels: typing.Dict[str, typing.Any] = {
        "method": method,
        "username": identity_data.account,
        "port": identity_data.port,
        "auth_type": identity_data.auth_type,
        "os_type": host.os_type,
    }
    return common_labels


def execute_shell_solution_async_exc_handler(
    wrapped: Callable, instance: base.BaseService, args: Tuple[Any], kwargs: Dict[str, Any], exc: Exception
) -> Optional[List]:
    """
    默认的单订阅实例任务异常处理，用于批量调用时规避单任务异常导致整体执行失败的情况
    :param wrapped: 被装饰的函数或类方法
    :param instance: 基础Pipeline服务
    :param exc: 捕获到异常
    :param args: 位置参数
    :param kwargs: 关键字参数
    :return:
    """
    common_labels: typing.Dict[str, typing.Any] = parse_common_labels_by_install_obj("ssh", kwargs)
    metrics.app_core_remote_connects_total.labels(**common_labels, status="failed").inc()
    metrics.app_core_remote_connect_exceptions_total.labels(**common_labels, **parse_exception(exc)).inc()
    return core.default_sub_inst_task_exc_handler(wrapped, instance, args, kwargs, exc)


def execute_windows_commands_exc_handler(
    wrapped: Callable, instance: base.BaseService, args: Tuple[Any], kwargs: Dict[str, Any], exc: Exception
) -> Optional[List]:
    """
    默认的单订阅实例任务异常处理，用于批量调用时规避单任务异常导致整体执行失败的情况
    :param wrapped: 被装饰的函数或类方法
    :param instance: 基础Pipeline服务
    :param exc: 捕获到异常
    :param args: 位置参数
    :param kwargs: 关键字参数
    :return:
    """
    common_labels: typing.Dict[str, typing.Any] = parse_common_labels_by_host_identity("wmiexe", kwargs)
    metrics.app_core_remote_connects_total.labels(**common_labels, status="failed").inc()
    metrics.app_core_remote_connect_exceptions_total.labels(**common_labels, **parse_exception(exc)).inc()
    return core.default_sub_inst_task_exc_handler(wrapped, instance, args, kwargs, exc)


def execute_shell_solution_async_success_handler(
    wrapped: Callable, instance: base.BaseService, args: Tuple[Any], kwargs: Dict[str, Any]
) -> None:
    common_labels: typing.Dict[str, typing.Any] = parse_common_labels_by_install_obj("ssh", kwargs)
    metrics.app_core_remote_connects_total.labels(**common_labels, status="success").inc()


def execute_windows_commands_success_handler(
    wrapped: Callable, instance: base.BaseService, args: Tuple[Any], kwargs: Dict[str, Any]
) -> None:
    common_labels: typing.Dict[str, typing.Any] = parse_common_labels_by_host_identity("wmiexe", kwargs)
    metrics.app_core_remote_connects_total.labels(**common_labels, status="success").inc()


class InstallService(base.AgentBaseService, remote.RemoteServiceMixin):
    __need_schedule__ = True
    interval = StaticIntervalGenerator(5)

    def inputs_format(self):
        return super().inputs_format() + [
            Service.InputItem(name="is_uninstall", key="is_uninstall", type="bool", required=False),
            Service.InputItem(name="success_callback_step", key="success_callback_step", type="str", required=True),
        ]

    def outputs_format(self):
        return super().outputs_format() + [
            Service.InputItem(name="polling_time", key="polling_time", type="int", required=True),
        ]

    @SetupObserve(
        histogram=metrics.app_core_remote_batch_execute_duration_seconds,
        labels={"method": "job"},
        # 不统计异常耗时
        include_exception_histogram=False,
    )
    @controller.ConcurrentController(
        data_list_name="install_sub_inst_objs",
        batch_call_func=concurrent.batch_call,
        get_config_dict_func=core.get_config_dict,
        get_config_dict_kwargs={"config_name": core.ServiceCCConfigName.JOB_CMD.value},
    )
    def handle_non_lan_inst(self, install_sub_inst_objs: List[InstallSubInstObj], bk_biz_id: int) -> List[int]:
        """处理跨云机器，通过执行作业平台脚本来操作"""
        params_list = [
            {
                "sub_inst_id": install_sub_inst_obj.sub_inst_id,
                "installation_tool": install_sub_inst_obj.installation_tool,
                "bk_biz_id": bk_biz_id,
            }
            for install_sub_inst_obj in install_sub_inst_objs
        ]
        return concurrent.batch_call(func=self.execute_job_commands, params_list=params_list)

    @SetupObserve(
        histogram=metrics.app_core_remote_batch_execute_duration_seconds,
        labels={"method": "wmiexe"},
        # 不统计异常耗时
        include_exception_histogram=False,
    )
    @controller.ConcurrentController(
        data_list_name="install_sub_inst_objs",
        batch_call_func=concurrent.batch_call,
        get_config_dict_func=core.get_config_dict,
        get_config_dict_kwargs={"config_name": core.ServiceCCConfigName.WMIEXE.value},
    )
    def handle_lan_windows_sub_inst(self, install_sub_inst_objs: List[InstallSubInstObj]):
        """处理直连windows机器，通过 wmiexe 连接windows机器"""
        pre_commands_params_list = []
        push_curl_exe_params_list = []
        run_install_params_list = []
        for install_sub_inst_obj in install_sub_inst_objs:
            installation_tool = install_sub_inst_obj.installation_tool
            execution_solution: solution_maker.ExecutionSolution = installation_tool.type__execution_solution_map[
                constants.CommonExecutionSolutionType.BATCH.value
            ]
            dest_dir = installation_tool.dest_dir
            dependencies: List[str] = []
            run_commands: List[str] = []
            for solution_step in execution_solution.steps[1:]:
                if solution_step.type == constants.CommonExecutionSolutionStepType.DEPENDENCIES.value:
                    dependencies.extend(
                        [
                            f"{content.child_dir}/{content.name}" if content.child_dir else content.name
                            for content in solution_step.contents
                        ]
                    )
                else:
                    run_commands.extend([content.text for content in solution_step.contents])

            # TODO 快速兼容方式，后续优化
            pre_commands_params_list.append(
                {
                    "sub_inst_id": install_sub_inst_obj.sub_inst_id,
                    "host": installation_tool.host,
                    "commands": [content.text for content in execution_solution.steps[0].contents],
                    "identity_data": installation_tool.identity_data,
                }
            )
            push_curl_exe_params_list.append(
                {
                    "sub_inst_id": install_sub_inst_obj.sub_inst_id,
                    "host": installation_tool.host,
                    "dest_dir": dest_dir,
                    "identity_data": installation_tool.identity_data,
                    "dependencies": dependencies,
                }
            )
            run_install_params_list.append(
                {
                    "sub_inst_id": install_sub_inst_obj.sub_inst_id,
                    "host": installation_tool.host,
                    "commands": run_commands,
                    "identity_data": installation_tool.identity_data,
                }
            )

        def _filter_params_list_in_next_step(
            _params_list: List[Dict[str, Any]], _succeed_sub_inst_ids: List[Optional[int]]
        ) -> List[Dict[str, Any]]:
            _params_list_in_next_step: List[Dict[str, Any]] = []
            _succeed_sub_inst_ids: Set[Optional[int]] = set(_succeed_sub_inst_ids)
            for _params in _params_list:
                if _params["sub_inst_id"] in _succeed_sub_inst_ids:
                    _params_list_in_next_step.append(_params)
            return _params_list_in_next_step

        # 前置命令执行较快，可以并发执行
        succeed_sub_inst_ids = concurrent.batch_call(
            func=self.execute_windows_commands, params_list=pre_commands_params_list
        )
        # 单个调用大约耗时 14s
        succeed_sub_inst_ids = concurrent.batch_call_serial(
            func=self.push_curl_exe,
            params_list=_filter_params_list_in_next_step(push_curl_exe_params_list, succeed_sub_inst_ids),
        )
        # 单个调用大约耗时 15s
        return concurrent.batch_call_serial(
            func=self.execute_windows_commands,
            params_list=_filter_params_list_in_next_step(run_install_params_list, succeed_sub_inst_ids),
        )

    @SetupObserve(
        histogram=metrics.app_core_remote_batch_execute_duration_seconds,
        labels={"method": "ssh"},
        # 不统计异常耗时
        include_exception_histogram=False,
    )
    @controller.ConcurrentController(
        data_list_name="install_sub_inst_objs",
        batch_call_func=concurrent.batch_call,
        get_config_dict_func=core.get_config_dict,
        get_config_dict_kwargs={"config_name": core.ServiceCCConfigName.SSH.value},
    )
    def handle_lan_shell_sub_inst(self, install_sub_inst_objs: List[InstallSubInstObj]):
        """处理直连且通过 Shell 执行的机器"""
        params_list = [
            {
                "meta": {"blueking_language": translation.get_language()},
                "sub_inst_id": install_sub_inst_obj.sub_inst_id,
                "install_sub_inst_obj": install_sub_inst_obj,
            }
            for install_sub_inst_obj in install_sub_inst_objs
        ]
        return concurrent.batch_call_coroutine(func=self.execute_shell_solution_async, params_list=params_list)

    def _execute(self, data, parent_data, common_data: base.AgentCommonData):
        host_id__sub_inst_id = {
            host_id: sub_inst_id for sub_inst_id, host_id in common_data.sub_inst_id__host_id_map.items()
        }
        is_uninstall = data.get_one_of_inputs("is_uninstall")
        host_id_obj_map = common_data.host_id_obj_map
        gse_version: str = data.get_one_of_inputs("meta", {}).get("GSE_VERSION")

        non_lan_sub_inst = []
        lan_windows_sub_inst = []
        lan_linux_sub_inst = []

        manual_install_sub_inst_ids: List[int] = []
        hosts_need_gen_commands: List[models.Host] = []
        for host in host_id_obj_map.values():
            if not host.is_manual:
                hosts_need_gen_commands.append(host)
                continue
            manual_install_sub_inst_ids.append(host_id__sub_inst_id[host.bk_host_id])
        self.log_info(sub_inst_ids=manual_install_sub_inst_ids, log_content=_("等待手动执行安装命令"))

        host_id__installation_tool_map = self.get_host_id__installation_tool_map(
            common_data, hosts_need_gen_commands, is_uninstall, gse_version, common_data.injected_ap_id
        )

        get_gse_config_tuple_params_list: List[Dict[str, Any]] = []
        host_ids_need_gen_commands = set(host_id__installation_tool_map.keys())
        for sub_inst in common_data.subscription_instances:
            bk_host_id = sub_inst.instance_info["host"]["bk_host_id"]
            host: Optional[models.Host] = self.get_host(common_data, bk_host_id)
            if not host:
                continue

            if bk_host_id not in host_ids_need_gen_commands:
                continue

            if not is_uninstall:
                # 仅在安装时需要缓存配置文件
                # 考虑手动安装也是小规模场景且依赖用户输入，暂不做缓存
                # 优先使用注入的ap, 适配只安装Agent场景
                host_ap: Optional[models.AccessPoint] = self.get_host_ap(common_data, host)
                if not host_ap:
                    continue
                get_gse_config_tuple_params_list.append(
                    {
                        "sub_inst_id": sub_inst.id,
                        "host": host,
                        "ap": host_ap,
                        "agent_step_adapter": common_data.agent_step_adapter,
                        "file_name": common_data.agent_step_adapter.get_main_config_filename(),
                    }
                )
            installation_tool = host_id__installation_tool_map[bk_host_id]
            install_sub_inst_obj = InstallSubInstObj(
                sub_inst_id=sub_inst.id, host=host, installation_tool=installation_tool
            )

            if installation_tool.is_need_jump_server:
                # 需要跳板执行时，通过 JOB 下发命令到跳板机
                non_lan_sub_inst.append(install_sub_inst_obj)
            else:
                # AGENT 或 PROXY 安装走 ssh 或 wmi 连接
                if host.os_type == constants.OsType.WINDOWS:
                    lan_windows_sub_inst.append(install_sub_inst_obj)
                else:
                    lan_linux_sub_inst.append(install_sub_inst_obj)

        gse_config_tuples = concurrent.batch_call(
            func=self.get_gse_config_tuple, params_list=get_gse_config_tuple_params_list
        )
        cache_key__config_content_map: Dict[str, str] = dict(list(filter(None, gse_config_tuples)))
        if cache_key__config_content_map:
            # 该场景下需要批量设置键过期时间，采用 Pipeline 批量提交命令，减少 IO 消耗
            pipeline: Pipeline = REDIS_INST.pipeline()
            # 缓存 Agent 配置
            pipeline.mset(cache_key__config_content_map)
            # 设置过期时间
            polling_timeout = self.service_polling_timeout
            for cache_key in cache_key__config_content_map:
                # 根据调度超时时间预估一个过期时间
                # 由于此时还未执行「命令下发」动作，随机增量过期时长，避免缓存雪崩
                pipeline.expire(cache_key, polling_timeout + random.randint(polling_timeout, 2 * polling_timeout))
            pipeline.execute()

        remote_conn_helpers_gby_result_type = self.bulk_check_ssh(remote_conn_helpers=lan_windows_sub_inst)

        if non_lan_sub_inst:
            job_meta: Dict[str, Any] = self.get_job_meta(data)
            bk_biz_id: int = job_meta["bk_biz_id"]
            succeed_non_lan_inst_ids = self.handle_non_lan_inst(
                install_sub_inst_objs=non_lan_sub_inst, bk_biz_id=bk_biz_id
            )
        else:
            succeed_non_lan_inst_ids = []

        unavailable_ssh_lan_windows_sub_inst = remote_conn_helpers_gby_result_type.get(
            remote.SshCheckResultType.UNAVAILABLE.value, []
        )
        if unavailable_ssh_lan_windows_sub_inst:
            succeed_lan_windows_sub_inst_ids = self.handle_lan_windows_sub_inst(
                install_sub_inst_objs=unavailable_ssh_lan_windows_sub_inst
            )
        else:
            succeed_lan_windows_sub_inst_ids = []

        lan_shell_sub_inst = lan_linux_sub_inst + remote_conn_helpers_gby_result_type.get(
            remote.SshCheckResultType.AVAILABLE.value, []
        )
        if lan_shell_sub_inst:
            succeed_lan_shell_sub_inst_ids = self.handle_lan_shell_sub_inst(install_sub_inst_objs=lan_shell_sub_inst)
        else:
            succeed_lan_shell_sub_inst_ids = []

        # 使用 filter 移除并发过程中抛出异常的实例
        data.outputs.scheduling_sub_inst_ids = list(
            filter(
                None,
                (
                    succeed_non_lan_inst_ids
                    + succeed_lan_windows_sub_inst_ids
                    + succeed_lan_shell_sub_inst_ids
                    + manual_install_sub_inst_ids
                ),
            )
        )
        data.outputs.polling_time = 0

    @ExceptionHandler(exc_handler=core.default_sub_inst_task_exc_handler)
    def get_gse_config_tuple(
        self,
        sub_inst_id: int,
        host: models.Host,
        ap: models.AccessPoint,
        agent_step_adapter: AgentStepAdapter,
        file_name: str,
    ) -> Tuple[str, str]:
        general_node_type = self.get_general_node_type(host.node_type)
        content = agent_step_adapter.get_config(host=host, filename=file_name, node_type=general_node_type, ap=ap)
        return REDIS_AGENT_CONF_KEY_TPL.format(file_name=file_name, sub_inst_id=sub_inst_id), content

    @ExceptionHandler(
        exc_handler=execute_windows_commands_exc_handler, success_handler=execute_windows_commands_success_handler
    )
    @SetupObserve(
        histogram=metrics.app_core_remote_execute_duration_seconds,
        labels={"method": "wmiexe"},
        # 不统计异常耗时
        include_exception_histogram=False,
    )
    @RetryHandler(interval=0, retry_times=2, exception_types=[ConnectionResetError])
    def execute_windows_commands(
        self, sub_inst_id: int, host: models.Host, commands: List[str], identity_data: models.IdentityData
    ):
        # windows command executing
        ip = host.login_ip or host.inner_ip or host.inner_ipv6
        if (identity_data.auth_type == constants.AuthType.PASSWORD and not identity_data.password) or (
            identity_data.auth_type == constants.AuthType.KEY and not identity_data.key
        ):
            self.log_info(sub_inst_ids=sub_inst_id, log_content=_("认证信息已过期, 请重装并填入认证信息"))
            raise AuthOverdueException
        for i, cmd in enumerate(commands, 1):
            try:
                if i == len(commands):
                    # Executing scripts is the last command and takes time, using asynchronous
                    self.log_info(sub_inst_ids=sub_inst_id, log_content=_("执行命令: {cmd}").format(cmd=cmd))
                    execute_cmd(
                        cmd,
                        ip,
                        identity_data.account,
                        identity_data.password,
                        no_output=True,
                    )
                else:
                    # Other commands is quick and depends on previous ones, using synchronous
                    self.log_info(sub_inst_ids=sub_inst_id, log_content=_("执行命令: {cmd}").format(cmd=cmd))
                    execute_cmd(cmd, ip, identity_data.account, identity_data.password)
            except socket.error:
                self.move_insts_to_failed(
                    [sub_inst_id],
                    _(
                        "正在安装 Windows AGENT, 命令执行失败，请确认: \n"
                        "1. 检查文件共享相关服务，确认以下服务均已开启\n"
                        "    - Function Discovery Resource Publication\n"
                        "    - SSDP Discovery \n"
                        "    - UPnP Device Host\n"
                        "    - Server\n"
                        "    - NetLogon // 如果没有加入域，可以不启动这个\n"
                        "    - TCP/IP NetBIOS Helper\n"
                        "2. 开启网卡 Net BOIS \n"
                        "3. 开启文件共享 Net share \n"
                        "4. 检查防火墙是否有放开 139/135/445 端口 \n"
                    ),
                )
            except ConnectionResetError as e:
                # 高并发模式下可能导致连接重置，记录报错信息并抛出异常，等待上层处理逻辑重试或抛出异常
                self.log_warning(sub_inst_ids=sub_inst_id, log_content=_("远程登录失败，等待自动重试，重试失败将打印异常信息。"))
                raise e
            except Exception as e:
                self.log_error(sub_inst_ids=[sub_inst_id], log_content=_("远程登录失败"))
                # batch_call_single_exception_handler 由最上层捕获并打印 DEBUG 日志
                raise e

        return sub_inst_id

    @ExceptionHandler(exc_handler=core.default_sub_inst_task_exc_handler)
    @RetryHandler(interval=0, retry_times=2, exception_types=[ConnectionResetError])
    def push_curl_exe(
        self,
        sub_inst_id: int,
        host: models.Host,
        dest_dir: str,
        identity_data: models.IdentityData,
        dependencies: List[str],
    ):
        ip = host.login_ip or host.inner_ip or host.outer_ip
        for dependence in dependencies:
            try:
                localpath = os.path.join(settings.BK_SCRIPTS_PATH, dependence)
                self.log_info(
                    sub_inst_ids=sub_inst_id,
                    log_content=_("推送文件 {localpath} 到目标机器路径 {dest_dir}").format(localpath=localpath, dest_dir=dest_dir),
                )
                put_file(
                    localpath,
                    dest_dir,
                    ip,
                    identity_data.account,
                    identity_data.password,
                )
            except ConnectionResetError as e:
                # 高并发模式下可能导致连接重置，记录报错信息并抛出异常，等待上层处理逻辑重试或抛出异常
                self.log_warning(sub_inst_ids=sub_inst_id, log_content=_("远程登录失败，等待自动重试，重试失败将打印异常信息。"))
                raise e
            except Exception as e:
                self.log_error(sub_inst_ids=[sub_inst_id], log_content=_("远程登录失败"))
                # batch_call_single_exception_handler 由最上层捕获并打印 DEBUG 日志
                raise e
        return sub_inst_id

    @ExceptionHandler(exc_handler=core.default_sub_inst_task_exc_handler)
    @SetupObserve(
        histogram=metrics.app_core_remote_execute_duration_seconds,
        labels={"method": "job"},
        # 不统计异常耗时
        include_exception_histogram=False,
    )
    def execute_job_commands(self, sub_inst_id, installation_tool: InstallationTools, bk_biz_id: int):
        # p-agent 走 作业平台，再 ssh 到 p-agent，这样可以无需保存 proxy 密码
        host = installation_tool.host
        jump_server = installation_tool.jump_server
        self.log_info(
            sub_inst_ids=sub_inst_id,
            log_content=_("主机的上游节点为: {upstream_nodes}").format(upstream_nodes=installation_tool.upstream_nodes),
        )
        self.log_info(
            sub_inst_ids=sub_inst_id,
            log_content=_("已选择 {inner_ip} 作为本次安装的跳板机").format(inner_ip=jump_server.inner_ip or jump_server.inner_ipv6),
        )

        target_server: Dict[str, List[Union[int, Dict[str, Union[int, str]]]]] = (
            {"host_id_list": [jump_server.bk_host_id]}
            if settings.BKAPP_ENABLE_DHCP
            else {
                "ip_list": [
                    {
                        "ip": jump_server.inner_ip,
                        "bk_cloud_id": jump_server.bk_cloud_id,
                    }
                ]
            }
        )
        execution_solution = installation_tool.type__execution_solution_map[
            constants.CommonExecutionSolutionType.SHELL.value
        ]
        kwargs = {
            "bk_biz_id": bk_biz_id,
            "task_name": f"NODEMAN_{sub_inst_id}_{self.__class__.__name__}",
            "target_server": target_server,
            "timeout": constants.JOB_TIMEOUT,
            "account_alias": settings.BACKEND_UNIX_ACCOUNT,
            "script_language": constants.ScriptLanguageType.PYTHON.value,
            # "script_content": base64.b64encode(self.setup_pagent_file_content).decode(),
            "script_content": "IyEvb3B0L3B5MzYvYmluL3B5dGhvbg0KIyAtKi0gZW5jb2Rpbmc6dXRmLTggLSotDQojIHZpbTpmdD1weXRob24gc3RzPTQgc3c9NCBleHBhbmR0YWIgbnUNCg0KZnJvbSBfX2Z1dHVyZV9fIGltcG9ydCBwcmludF9mdW5jdGlvbg0KDQppbXBvcnQgYWJjDQppbXBvcnQgYXJncGFyc2UNCmltcG9ydCBiYXNlNjQNCmltcG9ydCBoYXNobGliDQppbXBvcnQgaXBhZGRyZXNzDQppbXBvcnQganNvbg0KaW1wb3J0IGxvZ2dpbmcNCmltcG9ydCBvcw0KaW1wb3J0IHJlDQppbXBvcnQgc29ja2V0DQppbXBvcnQgc3lzDQppbXBvcnQgdGltZQ0KaW1wb3J0IHRyYWNlYmFjaw0KaW1wb3J0IHR5cGluZw0KZnJvbSBmdW5jdG9vbHMgaW1wb3J0IHBhcnRpYWwNCmZyb20gaW8gaW1wb3J0IFN0cmluZ0lPDQpmcm9tIHBhdGhsaWIgaW1wb3J0IFBhdGgNCmZyb20gc3VicHJvY2VzcyBpbXBvcnQgUG9wZW4NCmZyb20gdHlwaW5nIGltcG9ydCBBbnksIENhbGxhYmxlLCBEaWN0LCBMaXN0LCBPcHRpb25hbCwgVW5pb24NCg0KDQpkZWYgYXJnX3BhcnNlcigpIC0+IGFyZ3BhcnNlLkFyZ3VtZW50UGFyc2VyOg0KICAgICIiIkNvbW1hbmRsaW5lIGFyZ3VtZW50IHBhcnNlciIiIg0KICAgIHBhcnNlciA9IGFyZ3BhcnNlLkFyZ3VtZW50UGFyc2VyKGRlc2NyaXB0aW9uPSJwLWFnZW50IHNldHVwIHNjcmlwdHMiKQ0KICAgIHBhcnNlci5hZGRfYXJndW1lbnQoIi1mIiwgIi0tY29uZmlnIiwgdHlwZT1zdHIsIGhlbHA9ImEgZmlsZSBjb250YWluIHAtYWdlbnQgaG9zdHMgaW5mbyIpDQogICAgcGFyc2VyLmFkZF9hcmd1bWVudCgNCiAgICAgICAgIi1qIiwNCiAgICAgICAgIi0tanNvbiIsDQogICAgICAgIHR5cGU9c3RyLA0KICAgICAgICBoZWxwPSJhIGZpbGUgY29udGFpbiBwLWFnZW50IGhvc3RzIGluZm8gaW4ganNvbiBmb3JtYXQiLA0KICAgICkNCiAgICBwYXJzZXIuYWRkX2FyZ3VtZW50KCItSSIsICItLWxhbi1ldGgtaXAiLCB0eXBlPXN0ciwgaGVscD0ibG9jYWwgaXAgYWRkcmVzcyBvZiBwcm94eSIpDQogICAgcGFyc2VyLmFkZF9hcmd1bWVudCgNCiAgICAgICAgIi1sIiwNCiAgICAgICAgIi0tZG93bmxvYWQtdXJsIiwNCiAgICAgICAgdHlwZT1zdHIsDQogICAgICAgIGhlbHA9ImEgdXJsIGZvciBkb3dubG9hZGluZyBnc2UgYWdlbnQgcGFja2FnZXMgKHdpdGhvdXQgZmlsZW5hbWUpIiwNCiAgICApDQogICAgcGFyc2VyLmFkZF9hcmd1bWVudCgiLXMiLCAiLS10YXNrLWlkIiwgdHlwZT1zdHIsIGhlbHA9InRhc2sgaWQgZ2VuZXJhdGVkIGJ5IG5vZGVtYW4sIG9wdGlvbmFsIikNCiAgICBwYXJzZXIuYWRkX2FyZ3VtZW50KCItciIsICItLWNhbGxiYWNrLXVybCIsIHR5cGU9c3RyLCBoZWxwPSJhcGkgZm9yIHJlcG9ydCBzdGVwIGFuZCB0YXNrIHN0YXR1cyIpDQogICAgcGFyc2VyLmFkZF9hcmd1bWVudCgiLWMiLCAiLS10b2tlbiIsIHR5cGU9c3RyLCBoZWxwPSJ0b2tlbiBmb3IgcmVxdWVzdCBjYWxsYmFjayBhcGkiKQ0KICAgIHBhcnNlci5hZGRfYXJndW1lbnQoDQogICAgICAgICItVCIsDQogICAgICAgICItLXRlbXAtZGlyIiwNCiAgICAgICAgYWN0aW9uPSJzdG9yZV90cnVlIiwNCiAgICAgICAgZGVmYXVsdD1GYWxzZSwNCiAgICAgICAgaGVscD0iZGlyZWN0b3J5IHRvIHNhdmUgZG93bmxvYWRlZCBzY3JpcHRzIGFuZCB0ZW1wb3JhcnkgZmlsZXMiLA0KICAgICkNCiAgICBwYXJzZXIuYWRkX2FyZ3VtZW50KCItTCIsICItLWRvd25sb2FkLXBhdGgiLCB0eXBlPXN0ciwgaGVscD0iVG9vbCBraXQgc3RvcmFnZSBwYXRoIikNCg0KICAgICMg5Li75py65L+h5oGvDQogICAgcGFyc2VyLmFkZF9hcmd1bWVudCgiLUhMSVAiLCAiLS1ob3N0LWxvZ2luLWlwIiwgdHlwZT1zdHIsIGhlbHA9Ikhvc3QgTG9naW4gSVAiKQ0KICAgIHBhcnNlci5hZGRfYXJndW1lbnQoIi1ISUlQIiwgIi0taG9zdC1pbm5lci1pcCIsIHR5cGU9c3RyLCBoZWxwPSJIb3N0IElubmVyIElQIikNCiAgICBwYXJzZXIuYWRkX2FyZ3VtZW50KCItSEEiLCAiLS1ob3N0LWFjY291bnQiLCB0eXBlPXN0ciwgaGVscD0iSG9zdCBBY2NvdW50IikNCiAgICBwYXJzZXIuYWRkX2FyZ3VtZW50KCItSFAiLCAiLS1ob3N0LXBvcnQiLCB0eXBlPXN0ciwgaGVscD0iSG9zdCBQb3J0IikNCiAgICBwYXJzZXIuYWRkX2FyZ3VtZW50KCItSEkiLCAiLS1ob3N0LWlkZW50aXR5IiwgdHlwZT1zdHIsIGhlbHA9Ikhvc3QgSWRlbnRpdHkiKQ0KICAgIHBhcnNlci5hZGRfYXJndW1lbnQoIi1IQVQiLCAiLS1ob3N0LWF1dGgtdHlwZSIsIHR5cGU9c3RyLCBoZWxwPSJIb3N0IEF1dGggVHlwZSIpDQogICAgcGFyc2VyLmFkZF9hcmd1bWVudCgiLUhDIiwgIi0taG9zdC1jbG91ZCIsIHR5cGU9c3RyLCBoZWxwPSJIb3N0IENsb3VkIikNCiAgICBwYXJzZXIuYWRkX2FyZ3VtZW50KCItSE5UIiwgIi0taG9zdC1ub2RlLXR5cGUiLCB0eXBlPXN0ciwgaGVscD0iSG9zdCBOb2RlIFR5cGUiKQ0KICAgIHBhcnNlci5hZGRfYXJndW1lbnQoIi1IT1QiLCAiLS1ob3N0LW9zLXR5cGUiLCB0eXBlPXN0ciwgaGVscD0iSG9zdCBPcyBUeXBlIikNCiAgICBwYXJzZXIuYWRkX2FyZ3VtZW50KCItSEREIiwgIi0taG9zdC1kZXN0LWRpciIsIHR5cGU9c3RyLCBoZWxwPSJIb3N0IERlc3QgRGlyIikNCiAgICBwYXJzZXIuYWRkX2FyZ3VtZW50KCItSFBQIiwgIi0taG9zdC1wcm94eS1wb3J0IiwgdHlwZT1pbnQsIGRlZmF1bHQ9MTc5ODEsIGhlbHA9Ikhvc3QgUHJveHkgUG9ydCIpDQogICAgcGFyc2VyLmFkZF9hcmd1bWVudCgiLUNQQSIsICItLWNoYW5uZWwtcHJveHktYWRkcmVzcyIsIHR5cGU9c3RyLCBoZWxwPSJDaGFubmVsIFByb3h5IEFkZHJlc3MiLCBkZWZhdWx0PU5vbmUpDQoNCiAgICBwYXJzZXIuYWRkX2FyZ3VtZW50KCItSFNKQiIsICItLWhvc3Qtc29sdXRpb25zLWpzb24tYjY0IiwgdHlwZT1zdHIsIGhlbHA9IkNoYW5uZWwgUHJveHkgQWRkcmVzcyIsIGRlZmF1bHQ9Tm9uZSkNCiAgICByZXR1cm4gcGFyc2VyDQoNCg0KYXJncyA9IGFyZ19wYXJzZXIoKS5wYXJzZV9hcmdzKHN5cy5hcmd2WzE6XSkNCg0KdHJ5Og0KICAgICMgaW1wb3J0IDNyZCBwYXJ0eSBsaWJyYXJpZXMgaGVyZSwgaW4gY2FzZSB0aGUgcHl0aG9uIGludGVycHJldGVyIGRvZXMgbm90IGhhdmUgdGhlbQ0KICAgIGltcG9ydCBwYXJhbWlrbyAgIyBub3FhDQogICAgaW1wb3J0IHJlcXVlc3RzICAjIG5vcWENCg0KICAgIGltcG9ydCBpbXBhY2tldCAgIyBub3FhDQoNCiAgICAjIGltcG9ydCBwc3V0aWwNCg0KZXhjZXB0IEltcG9ydEVycm9yIGFzIGVycjoNCiAgICBmcm9tIHVybGxpYiBpbXBvcnQgcmVxdWVzdA0KDQogICAgX3F1ZXJ5X3BhcmFtcyA9IGpzb24uZHVtcHMoDQogICAgICAgIHsNCiAgICAgICAgICAgICJ0YXNrX2lkIjogYXJncy50YXNrX2lkLA0KICAgICAgICAgICAgInRva2VuIjogYXJncy50b2tlbiwNCiAgICAgICAgICAgICJsb2dzIjogWw0KICAgICAgICAgICAgICAgIHsNCiAgICAgICAgICAgICAgICAgICAgInRpbWVzdGFtcCI6IHJvdW5kKHRpbWUudGltZSgpKSwNCiAgICAgICAgICAgICAgICAgICAgImxldmVsIjogIkVSUk9SIiwNCiAgICAgICAgICAgICAgICAgICAgInN0ZXAiOiAiaW1wb3J0XzNyZF9saWJzIiwNCiAgICAgICAgICAgICAgICAgICAgImxvZyI6IHN0cihlcnIpLA0KICAgICAgICAgICAgICAgICAgICAic3RhdHVzIjogIkZBSUxFRCIsDQogICAgICAgICAgICAgICAgICAgICJwcmVmaXgiOiAiW3Byb3h5XSIsDQogICAgICAgICAgICAgICAgfQ0KICAgICAgICAgICAgXSwNCiAgICAgICAgfQ0KICAgICkuZW5jb2RlKCkNCg0KICAgIHJlcSA9IHJlcXVlc3QuUmVxdWVzdCgNCiAgICAgICAgZiJ7YXJncy5jYWxsYmFja191cmx9L3JlcG9ydF9sb2cvIiwNCiAgICAgICAgZGF0YT1fcXVlcnlfcGFyYW1zLA0KICAgICAgICBoZWFkZXJzPXsiQ29udGVudC1UeXBlIjogImFwcGxpY2F0aW9uL2pzb24ifSwNCiAgICApDQogICAgcmVxdWVzdC51cmxvcGVuKHJlcSkNCiAgICBleGl0KCkNCg0KDQojIOiHquWumuS5ieaXpeW/l+WkhOeQhuWZqA0KY2xhc3MgUmVwb3J0TG9nSGFuZGxlcihsb2dnaW5nLkhhbmRsZXIpOg0KICAgIGRlZiBfX2luaXRfXyhzZWxmLCByZXBvcnRfbG9nX3VybCk6DQogICAgICAgIHN1cGVyKCkuX19pbml0X18oKQ0KICAgICAgICBzZWxmLl9yZXBvcnRfbG9nX3VybCA9IHJlcG9ydF9sb2dfdXJsDQoNCiAgICBkZWYgZW1pdChzZWxmLCByZWNvcmQpOg0KDQogICAgICAgIGlzX3JlcG9ydDogYm9vbCA9IGdldGF0dHIocmVjb3JkLCAiaXNfcmVwb3J0IiwgRmFsc2UpDQoNCiAgICAgICAgaWYgbm90IGlzX3JlcG9ydDoNCiAgICAgICAgICAgIHJldHVybg0KDQogICAgICAgIHN0YXR1czogc3RyID0gKCItIiwgIkZBSUxFRCIpW3JlY29yZC5sZXZlbG5hbWUgPT0gIkVSUk9SIl0NCiAgICAgICAgcXVlcnlfcGFyYW1zID0gew0KICAgICAgICAgICAgInRhc2tfaWQiOiBhcmdzLnRhc2tfaWQsDQogICAgICAgICAgICAidG9rZW4iOiBhcmdzLnRva2VuLA0KICAgICAgICAgICAgImxvZ3MiOiBbDQogICAgICAgICAgICAgICAgew0KICAgICAgICAgICAgICAgICAgICAidGltZXN0YW1wIjogcm91bmQodGltZS50aW1lKCkpLA0KICAgICAgICAgICAgICAgICAgICAibGV2ZWwiOiByZWNvcmQubGV2ZWxuYW1lLA0KICAgICAgICAgICAgICAgICAgICAic3RlcCI6IHJlY29yZC5zdGVwLA0KICAgICAgICAgICAgICAgICAgICAibWV0cmljcyI6IHJlY29yZC5tZXRyaWNzLA0KICAgICAgICAgICAgICAgICAgICAibG9nIjogZiIoe3N0YXR1c30pIHtyZWNvcmQubWVzc2FnZX0iLA0KICAgICAgICAgICAgICAgICAgICAic3RhdHVzIjogc3RhdHVzLA0KICAgICAgICAgICAgICAgICAgICAicHJlZml4IjogIltwcm94eV0iLA0KICAgICAgICAgICAgICAgIH0NCiAgICAgICAgICAgIF0sDQogICAgICAgIH0NCiAgICAgICAgaWYgYXJncy5jaGFubmVsX3Byb3h5X2FkZHJlc3M6DQogICAgICAgICAgICBwcm94eV9hZGRyZXNzID0gew0KICAgICAgICAgICAgICAgICJodHRwIjogYXJncy5jaGFubmVsX3Byb3h5X2FkZHJlc3MsDQogICAgICAgICAgICAgICAgImh0dHBzIjogYXJncy5jaGFubmVsX3Byb3h5X2FkZHJlc3MsDQogICAgICAgICAgICB9DQogICAgICAgICAgICByZXF1ZXN0cy5wb3N0KHNlbGYuX3JlcG9ydF9sb2dfdXJsLCBqc29uPXF1ZXJ5X3BhcmFtcywgcHJveGllcz1wcm94eV9hZGRyZXNzKQ0KICAgICAgICBlbHNlOg0KICAgICAgICAgICAgcmVxdWVzdHMucG9zdChzZWxmLl9yZXBvcnRfbG9nX3VybCwganNvbj1xdWVyeV9wYXJhbXMpDQoNCg0KY2xhc3MgQ3VzdG9tTG9nZ2VyKGxvZ2dpbmcuTG9nZ2VyQWRhcHRlcik6DQogICAgZGVmIF9sb2coc2VsZiwgbGV2ZWwsIG1zZywgKmFyZ3MsIGV4dHJhPU5vbmUsICoqa3dhcmdzKToNCiAgICAgICAgaWYgZXh0cmEgaXMgTm9uZToNCiAgICAgICAgICAgIGV4dHJhID0ge30NCg0KICAgICAgICBzdGVwOiBzdHIgPSBleHRyYS5wb3AoInN0ZXAiLCAiTi9BIikNCiAgICAgICAgaXNfcmVwb3J0OiBzdHIgPSBleHRyYS5wb3AoImlzX3JlcG9ydCIsIFRydWUpDQogICAgICAgIG1ldHJpY3M6IHR5cGluZy5EaWN0W3N0ciwgdHlwaW5nLkFueV0gPSBleHRyYS5wb3AoIm1ldHJpY3MiLCB7fSkNCiAgICAgICAga3dhcmdzID0geyJzdGVwIjogc3RlcCwgImlzX3JlcG9ydCI6IGlzX3JlcG9ydCwgIm1ldHJpY3MiOiBtZXRyaWNzfQ0KICAgICAgICBrd2FyZ3MudXBkYXRlKGV4dHJhKQ0KDQogICAgICAgIHN1cGVyKCkuX2xvZyhsZXZlbCwgbXNnLCBhcmdzLCBleHRyYT1rd2FyZ3MpDQoNCiAgICBkZWYgbG9nZ2luZygNCiAgICAgICAgc2VsZiwNCiAgICAgICAgc3RlcDogc3RyLA0KICAgICAgICBtc2c6IHN0ciwNCiAgICAgICAgbWV0cmljczogdHlwaW5nLk9wdGlvbmFsW3R5cGluZy5EaWN0W3N0ciwgdHlwaW5nLkFueV1dID0gTm9uZSwNCiAgICAgICAgbGV2ZWw6IGludCA9IGxvZ2dpbmcuSU5GTywNCiAgICAgICAgaXNfcmVwb3J0OiBib29sID0gVHJ1ZSwNCiAgICApOg0KICAgICAgICBzZWxmLl9sb2cobGV2ZWwsIG1zZywgZXh0cmE9eyJzdGVwIjogc3RlcCwgImlzX3JlcG9ydCI6IGlzX3JlcG9ydCwgIm1ldHJpY3MiOiBtZXRyaWNzIG9yIHt9fSkNCg0KDQpjb25zb2xlX2hhbmRsZXIgPSBsb2dnaW5nLlN0cmVhbUhhbmRsZXIoKQ0KY29uc29sZV9oYW5kbGVyLnN0cmVhbSA9IG9zLmZkb3BlbihzeXMuc3Rkb3V0LmZpbGVubygpLCAidyIsIDEpDQoNCg0KbG9nZ2luZy5iYXNpY0NvbmZpZygNCiAgICBsZXZlbD1sb2dnaW5nLklORk8sDQogICAgZm9ybWF0PSIlKGFzY3RpbWUpcyAlKGxldmVsbmFtZSktOHMgJShtZXNzYWdlKXMiLA0KICAgIGRhdGVmbXQ9IiVZLSVtLSVkICVIOiVNOiVTIiwNCiAgICBoYW5kbGVycz1bY29uc29sZV9oYW5kbGVyLCBSZXBvcnRMb2dIYW5kbGVyKGYie2FyZ3MuY2FsbGJhY2tfdXJsfS9yZXBvcnRfbG9nLyIpXSwNCikNCg0KbG9nZ2VyID0gQ3VzdG9tTG9nZ2VyKGxvZ2dpbmcuZ2V0TG9nZ2VyKCksIHt9KQ0KDQoNCiMg6buY6K6k55qE6L+e5o6l5pyA6ZW/562J5b6F5pe26Ze0DQpERUZBVUxUX0NPTk5FQ1RfVElNRU9VVCA9IDMwDQoNCiMg6buY6K6k55qE5ZG95Luk5omn6KGM5pyA6ZW/562J5b6F5pe26Ze0DQpERUZBVUxUX0NNRF9SVU5fVElNRU9VVCA9IDMwDQoNCkRFRkFVTFRfSFRUUF9QUk9YWV9TRVJWRVJfUE9SVCA9IGFyZ3MuaG9zdF9wcm94eV9wb3J0DQoNCkpPQl9QUklWQVRFX0tFWV9SRSA9IHJlLmNvbXBpbGUociJeKC17NX1CRUdJTiAuKj8gUFJJVkFURSBLRVktezV9KSguKj8pKC17NX1FTkQgLio/IFBSSVZBVEUgS0VZLXs1fS4/KSQiKQ0KDQpQT1dFUlNIRUxMX1NFUlZJQ0VfQ0hFQ0tfU1NIRCA9ICJwb3dlcnNoZWxsIC1jIEdldC1TZXJ2aWNlIC1OYW1lIHNzaGQiDQoNCg0KZGVmIGlzX2lwKGlwOiBzdHIsIF92ZXJzaW9uOiBPcHRpb25hbFtpbnRdID0gTm9uZSkgLT4gYm9vbDoNCiAgICAiIiINCiAgICDliKTmlq3mmK/lkKbkuLrlkIjms5UgSVANCiAgICA6cGFyYW0gaXA6DQogICAgOnBhcmFtIF92ZXJzaW9uOiDmmK/lkKbkuLrlkIjms5XniYjmnKzvvIznvLrnnIHooajnpLogYm90aA0KICAgIDpyZXR1cm46DQogICAgIiIiDQogICAgdHJ5Og0KICAgICAgICBpcF9hZGRyZXNzID0gaXBhZGRyZXNzLmlwX2FkZHJlc3MoaXApDQogICAgZXhjZXB0IFZhbHVlRXJyb3I6DQogICAgICAgIHJldHVybiBGYWxzZQ0KICAgIGlmIF92ZXJzaW9uIGlzIE5vbmU6DQogICAgICAgIHJldHVybiBUcnVlDQogICAgcmV0dXJuIGlwX2FkZHJlc3MudmVyc2lvbiA9PSBfdmVyc2lvbg0KDQoNCiMg5Yik5pat5piv5ZCm5Li65ZCI5rOVIElQdjYNCmlzX3Y2ID0gcGFydGlhbChpc19pcCwgX3ZlcnNpb249NikNCg0KIyDliKTmlq3mmK/lkKbkuLrlkIjms5UgSVB2NA0KaXNfdjQgPSBwYXJ0aWFsKGlzX2lwLCBfdmVyc2lvbj00KQ0KDQoNCmNsYXNzIERvd25sb2FkRmlsZUVycm9yKEV4Y2VwdGlvbik6DQogICAgIiIi5paH5Lu2IiIiDQoNCiAgICBwYXNzDQoNCg0KZGVmIGpzb25fYjY0X2RlY29kZShqc29uX2I2NDogc3RyKSAtPiBBbnk6DQogICAgIiIiDQogICAgYmFzZTY0KGpzb25fc3RyKSB0byBweXRob24gdHlwZQ0KICAgIDpwYXJhbSBqc29uX2I2NDoNCiAgICA6cmV0dXJuOg0KICAgICIiIg0KICAgIHJldHVybiBqc29uLmxvYWRzKGJhc2U2NC5iNjRkZWNvZGUoanNvbl9iNjQuZW5jb2RlKCkpLmRlY29kZSgpKQ0KDQoNCmRlZiBleGVjdXRlX2NtZCgNCiAgICBjbWRfc3RyLA0KICAgIGlwYWRkciwNCiAgICB1c2VybmFtZSwNCiAgICBwYXNzd29yZCwNCiAgICBkb21haW49IiIsDQogICAgc2hhcmU9IkFETUlOJCIsDQogICAgaXNfbm9fb3V0cHV0PUZhbHNlLA0KKToNCiAgICAiIiJleGVjdXRlIGNvbW1hbmQiIiINCiAgICB0cnk6DQogICAgICAgIGZyb20gd21pZXhlYyBpbXBvcnQgV01JRVhFQw0KICAgIGV4Y2VwdCBJbXBvcnRFcnJvcjoNCiAgICAgICAgIyBXTUkg5omn6KGM5paH5Lu25LiN5a2Y5Zyo77yM5LuO5LiL6L295rqQ5ZCM5q2lDQogICAgICAgICMgd21pZXhlYyDmmK/kuIvovb3liLDohJrmnKzmiafooYznm67lvZXkuIvvvIzkuI3lsZ7kuo7lm57njq8NCiAgICAgICAgZG93bmxvYWRfZmlsZShmInthcmdzLmRvd25sb2FkX3VybH0vd21pZXhlYy5weSIsIHN0cihQYXRoKF9fZmlsZV9fKS5wYXJlbnQpLCBza2lwX2xvX2NoZWNrPVRydWUpDQogICAgICAgIGZyb20gd21pZXhlYyBpbXBvcnQgV01JRVhFQw0KDQogICAgZXhlY3V0b3IgPSBXTUlFWEVDKGNtZF9zdHIsIHVzZXJuYW1lLCBwYXNzd29yZCwgZG9tYWluLCBzaGFyZT1zaGFyZSwgbm9PdXRwdXQ9aXNfbm9fb3V0cHV0KQ0KICAgIHJlc3VsdF9kYXRhID0gZXhlY3V0b3IucnVuKGlwYWRkcikNCiAgICByZXR1cm4geyJyZXN1bHQiOiBUcnVlLCAiZGF0YSI6IHJlc3VsdF9kYXRhfQ0KDQoNCmRlZiBleGVjdXRlX2JhdGNoX3NvbHV0aW9uKA0KICAgIGxvZ2luX2lwOiBzdHIsDQogICAgYWNjb3VudDogc3RyLA0KICAgIGlkZW50aXR5OiBzdHIsDQogICAgdG1wX2Rpcjogc3RyLA0KICAgIGV4ZWN1dGlvbl9zb2x1dGlvbjogRGljdFtzdHIsIEFueV0sDQopOg0KICAgIGlmIG9zLnBhdGguaXNmaWxlKGlkZW50aXR5KToNCiAgICAgICAgbG9nZ2VyLmxvZ2dpbmcoDQogICAgICAgICAgICBzdGVwPSJleGVjdXRlX2JhdGNoX3NvbHV0aW9uIiwNCiAgICAgICAgICAgIG1zZz0iaWRlbnRpdHkgc2VlbXMgbGlrZSBhIGtleSBmaWxlLCB3aGljaCBpcyBub3Qgc3VwcG9ydGVkIGJ5IHdpbmRvd3MgYXV0aGVudGljYXRpb24iLA0KICAgICAgICAgICAgbGV2ZWw9bG9nZ2luZy5FUlJPUiwNCiAgICAgICAgKQ0KDQogICAgICAgIHJldHVybiBGYWxzZQ0KDQogICAgZm9yIHN0ZXAgaW4gZXhlY3V0aW9uX3NvbHV0aW9uWyJzdGVwcyJdOg0KICAgICAgICBmb3IgY29udGVudCBpbiBzdGVwWyJjb250ZW50cyJdOg0KICAgICAgICAgICAgaWYgc3RlcFsidHlwZSJdID09ICJkZXBlbmRlbmNpZXMiOg0KICAgICAgICAgICAgICAgIGRvd25sb2FkX3BhdGg6IHN0ciA9IGFyZ3MuZG93bmxvYWRfcGF0aA0KICAgICAgICAgICAgICAgIGlmIGNvbnRlbnQuZ2V0KCJjaGlsZF9kaXIiKToNCiAgICAgICAgICAgICAgICAgICAgZG93bmxvYWRfcGF0aCA9IG9zLnBhdGguam9pbihkb3dubG9hZF9wYXRoLCBjb250ZW50WyJjaGlsZF9kaXIiXSkNCiAgICAgICAgICAgICAgICBsb2NhbHBhdGggPSBvcy5wYXRoLmpvaW4oZG93bmxvYWRfcGF0aCwgY29udGVudFsibmFtZSJdKQ0KICAgICAgICAgICAgICAgICMg5paH5Lu25LiN5a2Y5Zyo77yM5LuO5LiL6L295rqQ5ZCM5q2lDQogICAgICAgICAgICAgICAgaWYgbm90IG9zLnBhdGguZXhpc3RzKGxvY2FscGF0aCkgb3IgY29udGVudC5nZXQoImFsd2F5c19kb3dubG9hZCIpOg0KICAgICAgICAgICAgICAgICAgICBsb2dnZXIubG9nZ2luZygNCiAgICAgICAgICAgICAgICAgICAgICAgICJleGVjdXRlX2JhdGNoX3NvbHV0aW9uIiwgZiJmaWxlIC0+IHtjb250ZW50WyduYW1lJ119IG5vdCBleGlzdHMsIHN5bmMgZnJvbSB7Y29udGVudFsndGV4dCddfSINCiAgICAgICAgICAgICAgICAgICAgKQ0KICAgICAgICAgICAgICAgICAgICBkb3dubG9hZF9maWxlKGNvbnRlbnRbInRleHQiXSwgZG93bmxvYWRfcGF0aCkNCg0KICAgICAgICAgICAgICAgICMg5p6E6YCg5paH5Lu25o6o6YCB5ZG95LukDQogICAgICAgICAgICAgICAgY21kOiBzdHIgPSAicHV0IHtsb2NhbHBhdGh9IHt0bXBfZGlyfSIuZm9ybWF0KGxvY2FscGF0aD1sb2NhbHBhdGgsIHRtcF9kaXI9dG1wX2RpcikNCiAgICAgICAgICAgIGVsaWYgc3RlcFsidHlwZSJdID09ICJjb21tYW5kcyI6DQogICAgICAgICAgICAgICAgY21kOiBzdHIgPSBjb250ZW50WyJ0ZXh0Il0NCiAgICAgICAgICAgIGVsc2U6DQogICAgICAgICAgICAgICAgbG9nZ2VyLmxvZ2dpbmcoImV4ZWN1dGVfYmF0Y2hfc29sdXRpb24iLCBmInVua25vd24gc3RlcCB0eXBlIC0+IHtzdGVwWyd0eXBlJ119IikNCiAgICAgICAgICAgICAgICBjb250aW51ZQ0KDQogICAgICAgICAgICBsb2dnZXIubG9nZ2luZygic2VuZF9jbWQiLCBjbWQpDQoNCiAgICAgICAgICAgIHRyeToNCiAgICAgICAgICAgICAgICByZXMgPSBleGVjdXRlX2NtZChjbWQsIGxvZ2luX2lwLCBhY2NvdW50LCBpZGVudGl0eSwgaXNfbm9fb3V0cHV0PWNvbnRlbnRbIm5hbWUiXSA9PSAicnVuX2NtZCIpDQogICAgICAgICAgICBleGNlcHQgRXhjZXB0aW9uOg0KICAgICAgICAgICAgICAgICMg6L+H56iL5Lit5Y+q6KaB5pyJ5LiA5p2h5ZG95Luk5omn6KGM5aSx6LSl77yM6KeG5Li65omn6KGM5pa55qGI5aSx6LSlDQogICAgICAgICAgICAgICAgbG9nZ2VyLmxvZ2dpbmcoImV4ZWN1dGVfYmF0Y2hfc29sdXRpb24iLCBmImV4ZWN1dGUge2NtZH0gZmFpbGVkIiwgbGV2ZWw9bG9nZ2luZy5XQVJOSU5HKQ0KICAgICAgICAgICAgICAgICMg5oqK5byC5bi45oqb57uZ5pyA5aSW5bGCDQogICAgICAgICAgICAgICAgcmFpc2UNCg0KICAgICAgICAgICAgcHJpbnQocmVzKQ0KDQoNCmRlZiBjb252ZXJ0X3NoZWxsX3RvX3Bvd2Vyc2hlbGwoc2hlbGxfY21kKToNCiAgICAjIENvbnZlcnQgbWtkaXIgLXAgeHh4IHRvIGlmIG5vdCBleGlzdCB4eHggbWtkaXIgeHh4DQogICAgc2hlbGxfY21kID0gcmUuc3ViKA0KICAgICAgICByIm1rZGlyIC1wXHMrKFxTKykiLA0KICAgICAgICByInBvd2Vyc2hlbGwgLWMgJ2lmICgtTm90IChUZXN0LVBhdGggLVBhdGggXDEpKSB7IE5ldy1JdGVtIC1JdGVtVHlwZSBEaXJlY3RvcnkgLVBhdGggXDEgfSciLA0KICAgICAgICBzaGVsbF9jbWQsDQogICAgKQ0KDQogICAgIyBDb252ZXJ0IGNobW9kICt4IHh4eCB0byAnJw0KICAgIHNoZWxsX2NtZCA9IHJlLnN1YihyImNobW9kXHMrXCt4XHMrXFMrIiwgciIiLCBzaGVsbF9jbWQpDQoNCiAgICAjIENvbnZlcnQgY3VybCB0byBJbnZva2UtV2ViUmVxdWVzdA0KICAgICMgc2hlbGxfY21kID0gcmUuc3ViKA0KICAgICMgICAgIHIiY3VybFxzKyhodHRwW3NdPzpcL1wvW15cc10rKVxzKy1vXHMrKFwvP1teXHNdKylccystLWNvbm5lY3QtdGltZW91dFxzKyhcZCspXHMrLXNTZmciLA0KICAgICMgICAgIHIicG93ZXJzaGVsbCAtYyAnSW52b2tlLVdlYlJlcXVlc3QgLVVyaSBcMSAtT3V0RmlsZSBcMiAtVGltZW91dFNlYyBcMyAtVXNlQmFzaWNQYXJzaW5nJyIsDQogICAgIyAgICAgc2hlbGxfY21kLA0KICAgICMgKQ0KICAgIHNoZWxsX2NtZCA9IHJlLnN1YihyIihjdXJsXHMrXFMrXHMrLW9ccytcUytccystLWNvbm5lY3QtdGltZW91dFxzK1xkK1xzKy1zU2ZnKSIsIHInY21kIC9jICJcMSInLCBzaGVsbF9jbWQpDQoNCiAgICAjIENvbnZlcnQgbm9odXAgeHh4ICY+IC4uLiAmIHRvIHh4eCAoaWdub3JlIG5vaHVwLCBvdXRwdXQgcmVkaXJlY3Rpb24gYW5kIGJhY2tncm91bmQgZXhlY3V0aW9uKQ0KICAgIHNoZWxsX2NtZCA9IHJlLnN1YigNCiAgICAgICAgciJub2h1cFxzKyhbXiY+XSspKFxzKiY+XHMqLio/Jik/IiwNCiAgICAgICAgciJwb3dlcnNoZWxsIC1jICdJbnZva2UtQ29tbWFuZCAtU2Vzc2lvbiAoTmV3LVBTU2Vzc2lvbikgLVNjcmlwdEJsb2NrIHsgXDEgfSAtQXNKb2InIiwNCiAgICAgICAgc2hlbGxfY21kLA0KICAgICkNCg0KICAgICMgUmVtb3ZlICcmPicgYW5kIGV2ZXJ5dGhpbmcgYWZ0ZXIgaXQNCiAgICBzaGVsbF9jbWQgPSByZS5zdWIociJccyomPi4qIiwgIiIsIHNoZWxsX2NtZCkNCg0KICAgICMgQ29udmVydCBcXCB0byBcDQogICAgc2hlbGxfY21kID0gc2hlbGxfY21kLnJlcGxhY2UoIlxcXFwiLCAiXFwiKQ0KDQogICAgcmV0dXJuIHNoZWxsX2NtZC5zdHJpcCgpDQoNCg0KZGVmIGV4ZWN1dGVfc2hlbGxfc29sdXRpb24oDQogICAgbG9naW5faXA6IHN0ciwNCiAgICBhY2NvdW50OiBzdHIsDQogICAgcG9ydDogaW50LA0KICAgIGlkZW50aXR5OiBzdHIsDQogICAgYXV0aF90eXBlOiBzdHIsDQogICAgb3NfdHlwZTogc3RyLA0KICAgIGV4ZWN1dGlvbl9zb2x1dGlvbjogRGljdFtzdHIsIEFueV0sDQopOg0KICAgIGNsaWVudF9rZXlfc3RyaW5nczogTGlzdFtzdHJdID0gW10NCiAgICBpZiBhdXRoX3R5cGUgPT0gIktFWSI6DQogICAgICAgIGNsaWVudF9rZXlfc3RyaW5ncy5hcHBlbmQoaWRlbnRpdHkpDQoNCiAgICB3aXRoIFBhcmFtaWtvQ29ubigNCiAgICAgICAgaG9zdD1sb2dpbl9pcCwNCiAgICAgICAgcG9ydD1wb3J0LA0KICAgICAgICB1c2VybmFtZT1hY2NvdW50LA0KICAgICAgICBwYXNzd29yZD1pZGVudGl0eSwNCiAgICAgICAgY2xpZW50X2tleV9zdHJpbmdzPWNsaWVudF9rZXlfc3RyaW5ncywNCiAgICAgICAgY29ubmVjdF90aW1lb3V0PTE1LA0KICAgICkgYXMgY29ubjoNCiAgICAgICAgY29tbWFuZF9jb252ZXJ0ZXIgPSB7fQ0KICAgICAgICBpZiBvc190eXBlID09ICJ3aW5kb3dzIjoNCiAgICAgICAgICAgIHJ1bl9vdXRwdXQ6IFJ1bk91dHB1dCA9IGNvbm4ucnVuKFBPV0VSU0hFTExfU0VSVklDRV9DSEVDS19TU0hELCBjaGVjaz1UcnVlLCB0aW1lb3V0PTMwKQ0KICAgICAgICAgICAgaWYgcnVuX291dHB1dC5leGl0X3N0YXR1cyA9PSAwIGFuZCAiY3lnd2luIiBub3QgaW4gcnVuX291dHB1dC5zdGRvdXQubG93ZXIoKToNCiAgICAgICAgICAgICAgICBmb3Igc3RlcCBpbiBleGVjdXRpb25fc29sdXRpb25bInN0ZXBzIl06DQogICAgICAgICAgICAgICAgICAgIGlmIHN0ZXBbInR5cGUiXSAhPSAiY29tbWFuZHMiOg0KICAgICAgICAgICAgICAgICAgICAgICAgY29udGludWUNCiAgICAgICAgICAgICAgICAgICAgZm9yIGNvbnRlbnQgaW4gc3RlcFsiY29udGVudHMiXToNCiAgICAgICAgICAgICAgICAgICAgICAgIGNtZDogc3RyID0gY29udGVudFsidGV4dCJdDQogICAgICAgICAgICAgICAgICAgICAgICBjb21tYW5kX2NvbnZlcnRlcltjbWRdID0gY29udmVydF9zaGVsbF90b19wb3dlcnNoZWxsKGNtZCkNCg0KICAgICAgICBmb3Igc3RlcCBpbiBleGVjdXRpb25fc29sdXRpb25bInN0ZXBzIl06DQogICAgICAgICAgICAjIOaaguS4jeaUr+aMgSBkZXBlbmRlbmNpZXMg562J5YW25LuW5q2l6aqk57G75Z6LDQogICAgICAgICAgICBpZiBzdGVwWyJ0eXBlIl0gIT0gImNvbW1hbmRzIjoNCiAgICAgICAgICAgICAgICBjb250aW51ZQ0KICAgICAgICAgICAgZm9yIGNvbnRlbnQgaW4gc3RlcFsiY29udGVudHMiXToNCiAgICAgICAgICAgICAgICBjbWQ6IHN0ciA9IGNvbW1hbmRfY29udmVydGVyLmdldChjb250ZW50WyJ0ZXh0Il0sIGNvbnRlbnRbInRleHQiXSkNCiAgICAgICAgICAgICAgICBpZiAiYzovVGVtcC9jdXJsLmV4ZSIgaW4gY21kOg0KICAgICAgICAgICAgICAgICAgICBjb250aW51ZQ0KICAgICAgICAgICAgICAgIGlmIG5vdCBjbWQ6DQogICAgICAgICAgICAgICAgICAgIGNvbnRpbnVlDQoNCiAgICAgICAgICAgICAgICAjIOagueaNrueUqOaIt+WQjeWIpOaWreaYr+WQpumHh+eUqHN1ZG8NCiAgICAgICAgICAgICAgICBpZiBhY2NvdW50IG5vdCBpbiBbInJvb3QiLCAiQWRtaW5pc3RyYXRvciIsICJhZG1pbmlzdHJhdG9yIl0gYW5kIG5vdCBjbWQuc3RhcnRzd2l0aCgic3VkbyIpOg0KICAgICAgICAgICAgICAgICAgICBjbWQgPSAic3VkbyAlcyIgJSBjbWQNCg0KICAgICAgICAgICAgICAgIGlmIGNvbnRlbnRbIm5hbWUiXSA9PSAicnVuX2NtZCI6DQogICAgICAgICAgICAgICAgICAgIGxvZ2dlci5sb2dnaW5nKCJzZW5kX2NtZCIsIGNtZCwgaXNfcmVwb3J0PVRydWUpDQogICAgICAgICAgICAgICAgZWxzZToNCiAgICAgICAgICAgICAgICAgICAgbG9nZ2VyLmxvZ2dpbmcoInNlbmRfY21kIiwgY21kLCBpc19yZXBvcnQ9RmFsc2UpDQogICAgICAgICAgICAgICAgcnVuX291dHB1dDogUnVuT3V0cHV0ID0gY29ubi5ydW4oY21kLCBjaGVjaz1UcnVlLCB0aW1lb3V0PTMwKQ0KICAgICAgICAgICAgICAgIGlmIHJ1bl9vdXRwdXQuZXhpdF9zdGF0dXMgIT0gMDoNCiAgICAgICAgICAgICAgICAgICAgcmFpc2UgUHJvY2Vzc0Vycm9yKGYiQ29tbWFuZCByZXR1cm5lZCBub24temVybzoge3J1bl9vdXRwdXR9IikNCiAgICAgICAgICAgICAgICBsb2dnZXIubG9nZ2luZygic2VuZF9jbWQiLCBzdHIocnVuX291dHB1dCksIGlzX3JlcG9ydD1GYWxzZSkNCg0KDQpkZWYgaXNfcG9ydF9saXN0ZW4oaXA6IHN0ciwgcG9ydDogaW50KSAtPiBib29sOg0KICAgIHMgPSBzb2NrZXQuc29ja2V0KChzb2NrZXQuQUZfSU5FVCwgc29ja2V0LkFGX0lORVQ2KVtpc192NihpcCldLCBzb2NrZXQuU09DS19TVFJFQU0pDQogICAgciA9IHMuY29ubmVjdF9leCgoaXAsIHBvcnQpKQ0KDQogICAgaWYgciA9PSAwOg0KICAgICAgICByZXR1cm4gVHJ1ZQ0KICAgIGVsc2U6DQogICAgICAgIHJldHVybiBGYWxzZQ0KDQoNCmRlZiBzdGFydF9odHRwX3Byb3h5KGlwOiBzdHIsIHBvcnQ6IGludCkgLT4gQW55Og0KICAgIGlmIGlzX3BvcnRfbGlzdGVuKGlwLCBwb3J0KToNCiAgICAgICAgbG9nZ2VyLmxvZ2dpbmcoInN0YXJ0X2h0dHBfcHJveHkiLCAiaHR0cCBwcm94eSBleGlzdHMiLCBpc19yZXBvcnQ9RmFsc2UpDQogICAgZWxzZToNCiAgICAgICAgUG9wZW4oIi9vcHQvbmdpbngtcG9ydGFibGUvbmdpbngtcG9ydGFibGUgcmVzdGFydCIsIHNoZWxsPVRydWUpDQoNCiAgICAgICAgdGltZS5zbGVlcCg1KQ0KICAgICAgICBpZiBpc19wb3J0X2xpc3RlbihpcCwgcG9ydCk6DQogICAgICAgICAgICBsb2dnZXIubG9nZ2luZygic3RhcnRfaHR0cF9wcm94eSIsICJodHRwIHByb3h5IHN0YXJ0ZWQiKQ0KICAgICAgICBlbHNlOg0KICAgICAgICAgICAgbG9nZ2VyLmxvZ2dpbmcoInN0YXJ0X2h0dHBfcHJveHkiLCAiaHR0cCBwcm94eSBzdGFydCBmYWlsZWQiLCBsZXZlbD1sb2dnaW5nLkVSUk9SKQ0KICAgICAgICAgICAgcmFpc2UgRXhjZXB0aW9uKCJodHRwIHByb3h5IHN0YXJ0IGZhaWxlZC4iKQ0KDQoNCmRlZiBqc29uX3BhcnNlcihqc29uX2ZpbGU6IHN0cikgLT4gTGlzdDoNCiAgICAiIiJSZXNvbHZlIGZvcm1hdHRlZCBsaW5lcyB0byBvYmplY3QgZnJvbSBjb25maWcgZmlsZSIiIg0KDQogICAgY29uZmlncyA9IFtdDQoNCiAgICB3aXRoIG9wZW4oanNvbl9maWxlLCAiciIsIGVuY29kaW5nPSJ1dGYtOCIpIGFzIGY6DQogICAgICAgIGhvc3RzID0ganNvbi5sb2FkcyhmLnJlYWQoKSkNCiAgICAgICAgZm9yIGhvc3QgaW4gaG9zdHM6DQogICAgICAgICAgICBjb25maWdzLmFwcGVuZCh0dXBsZShob3N0KSkNCiAgICByZXR1cm4gY29uZmlncw0KDQoNCmRlZiBkb3dubG9hZF9maWxlKHVybDogc3RyLCBkZXN0X2Rpcjogc3RyLCBza2lwX2xvX2NoZWNrOiBib29sID0gRmFsc2UpOg0KICAgICIiImdldCBmaWxlcyB2aWEgaHR0cCIiIg0KICAgIHRyeToNCiAgICAgICAgIyDliJvlu7rkuIvovb3nm67lvZUNCiAgICAgICAgb3MubWFrZWRpcnMoZGVzdF9kaXIsIGV4aXN0X29rPVRydWUpDQogICAgICAgIGxvY2FsX2ZpbGVuYW1lID0gdXJsLnNwbGl0KCIvIilbLTFdDQogICAgICAgICMgTk9URSB0aGUgc3RyZWFtPVRydWUgcGFyYW1ldGVyIGJlbG93DQogICAgICAgIGxvY2FsX2ZpbGUgPSBvcy5wYXRoLmpvaW4oZGVzdF9kaXIsIGxvY2FsX2ZpbGVuYW1lKQ0KDQogICAgICAgIGlmIG9zLnBhdGguZXhpc3RzKGxvY2FsX2ZpbGUpOg0KICAgICAgICAgICAgIyDlpoLmnpzkv67mlLnml7bpl7TkuLTov5HvvIzot7Pov4fkuIvovb3vvIzpgb/lhY3lpJrkuKogc2V0dXAg6ISa5pys5paH5Lu25LqS55u46KaG55uWDQogICAgICAgICAgICBtdGltZXN0YW1wOiBmbG9hdCA9IG9zLnBhdGguZ2V0bXRpbWUobG9jYWxfZmlsZSkNCiAgICAgICAgICAgIGlmIHRpbWUudGltZSgpIC0gbXRpbWVzdGFtcCA8IDEwOg0KICAgICAgICAgICAgICAgIGxvZ2dlci5sb2dnaW5nKA0KICAgICAgICAgICAgICAgICAgICAiZG93bmxvYWRfZmlsZSIsIGYiRmlsZSBkb3dubG9hZCBza2lwcGVkIGR1ZSB0byBzeW5jIHRpbWUgYXBwcm9hY2hpbmcsIG10aW1lc3RhbXAgLT4ge210aW1lc3RhbXB9Ig0KICAgICAgICAgICAgICAgICkNCiAgICAgICAgICAgICAgICByZXR1cm4NCg0KICAgICAgICBpZiBhcmdzLmxhbl9ldGhfaXAgaW4gdXJsIGFuZCBub3Qgc2tpcF9sb19jaGVjazoNCiAgICAgICAgICAgIGxvZ2dlci5sb2dnaW5nKCJkb3dubG9hZF9maWxlIiwgIkZpbGUgZG93bmxvYWQgc2tpcHBlZCBkdWUgdG8gbG8gaXAiKQ0KICAgICAgICAgICAgcmV0dXJuDQoNCiAgICAgICAgciA9IHJlcXVlc3RzLmdldCh1cmwsIHN0cmVhbT1UcnVlKQ0KICAgICAgICByLnJhaXNlX2Zvcl9zdGF0dXMoKQ0KDQogICAgICAgICMg5YWI5LiL6L295Yiw5Li05pe25paH5Lu25aS577yM5YaN6YCa6L+HIG9zLnJlcGxhY2Ug5ZG95ZCN5Yiw55uu5qCH5paH5Lu26Lev5b6E77yM6YCa6L+H6K+l5pa55byP6Ziy5q2i5ZCM5LiA5pe26Ze05aSa5ZCM5q2l5Lu75Yqh55u45LqS5bmy5omw77yM56Gu5L+d5paH5Lu25pON5L2c5Y6f5a2Q5oCnDQogICAgICAgICMgUmVmZXI6IGh0dHBzOi8vc3RhY2tvdmVyZmxvdy5jb20vcXVlc3Rpb25zLzIzMzM4NzIvDQogICAgICAgIGxvY2FsX3RtcF9maWxlID0gb3MucGF0aC5qb2luKA0KICAgICAgICAgICAgZGVzdF9kaXIsIGxvY2FsX2ZpbGVuYW1lICsgIi4iICsgaGFzaGxpYi5tZDUoYXJncy50b2tlbi5lbmNvZGUoInV0Zi04IikpLmhleGRpZ2VzdCgpDQogICAgICAgICkNCiAgICAgICAgd2l0aCBvcGVuKHN0cihsb2NhbF90bXBfZmlsZSksICJ3YiIpIGFzIGY6DQogICAgICAgICAgICBmb3IgY2h1bmsgaW4gci5pdGVyX2NvbnRlbnQoY2h1bmtfc2l6ZT0xMDI0KToNCiAgICAgICAgICAgICAgICAjIGZpbHRlciBvdXQga2VlcC1hbGl2ZSBuZXcgY2h1bmtzDQogICAgICAgICAgICAgICAgaWYgY2h1bms6DQogICAgICAgICAgICAgICAgICAgIGYud3JpdGUoY2h1bmspDQoNCiAgICAgICAgb3MucmVwbGFjZShsb2NhbF90bXBfZmlsZSwgbG9jYWxfZmlsZSkNCg0KICAgIGV4Y2VwdCBFeGNlcHRpb24gYXMgZXhjOg0KICAgICAgICBlcnJfbXNnOiBzdHIgPSBmImRvd25sb2FkIGZpbGUgZnJvbSB7dXJsfSB0byB7ZGVzdF9kaXJ9IGZhaWxlZDoge3N0cihleGMpfSINCiAgICAgICAgbG9nZ2VyLmxvZ2dpbmcoImRvd25sb2FkX2ZpbGUiLCBlcnJfbXNnLCBsZXZlbD1sb2dnaW5nLldBUk5JTkcpDQogICAgICAgIHJhaXNlIERvd25sb2FkRmlsZUVycm9yKGVycl9tc2cpIGZyb20gZXhjDQoNCg0KZGVmIHVzZV9zaGVsbCgpIC0+IGJvb2w6DQogICAgb3NfdHlwZTogc3RyID0gYXJncy5ob3N0X29zX3R5cGUNCiAgICBwb3J0ID0gaW50KGFyZ3MuaG9zdF9wb3J0KQ0KICAgIGlmIG9zX3R5cGUgbm90IGluIFsid2luZG93cyJdIG9yIChvc190eXBlIGluIFsid2luZG93cyJdIGFuZCBwb3J0ICE9IDQ0NSk6DQogICAgICAgIHJldHVybiBUcnVlDQogICAgZWxzZToNCiAgICAgICAgcmV0dXJuIEZhbHNlDQoNCg0KZGVmIGdldF9jb21tb25fbGFiZWxzKCkgLT4gdHlwaW5nLkRpY3Rbc3RyLCB0eXBpbmcuQW55XToNCiAgICBvc190eXBlOiBzdHIgPSBhcmdzLmhvc3Rfb3NfdHlwZSBvciAidW5rbm93biINCiAgICByZXR1cm4gew0KICAgICAgICAibWV0aG9kIjogKCJwcm94eV93bWlleGUiLCAicHJveHlfc3NoIilbdXNlX3NoZWxsKCldLA0KICAgICAgICAidXNlcm5hbWUiOiBhcmdzLmhvc3RfYWNjb3VudCwNCiAgICAgICAgInBvcnQiOiBpbnQoYXJncy5ob3N0X3BvcnQpLA0KICAgICAgICAiYXV0aF90eXBlIjogYXJncy5ob3N0X2F1dGhfdHlwZSwNCiAgICAgICAgIm9zX3R5cGUiOiBvc190eXBlLnVwcGVyKCksDQogICAgfQ0KDQoNCmRlZiBtYWluKCkgLT4gTm9uZToNCg0KICAgIGxvZ2luX2lwID0gYXJncy5ob3N0X2xvZ2luX2lwDQogICAgdXNlciA9IGFyZ3MuaG9zdF9hY2NvdW50DQogICAgcG9ydCA9IGludChhcmdzLmhvc3RfcG9ydCkNCiAgICBpZGVudGl0eSA9IGFyZ3MuaG9zdF9pZGVudGl0eQ0KICAgIGF1dGhfdHlwZSA9IGFyZ3MuaG9zdF9hdXRoX3R5cGUNCiAgICBvc190eXBlID0gYXJncy5ob3N0X29zX3R5cGUNCiAgICB0bXBfZGlyID0gYXJncy5ob3N0X2Rlc3RfZGlyDQogICAgaG9zdF9zb2x1dGlvbnNfanNvbl9iNjQgPSBhcmdzLmhvc3Rfc29sdXRpb25zX2pzb25fYjY0DQoNCiAgICBob3N0X3NvbHV0aW9ucyA9IGpzb25fYjY0X2RlY29kZShob3N0X3NvbHV0aW9uc19qc29uX2I2NCkNCiAgICB0eXBlX19ob3N0X3NvbHV0aW9uX21hcCA9IHtob3N0X3NvbHV0aW9uWyJ0eXBlIl06IGhvc3Rfc29sdXRpb24gZm9yIGhvc3Rfc29sdXRpb24gaW4gaG9zdF9zb2x1dGlvbnN9DQoNCiAgICAjIOWQr+WKqHByb3h5DQogICAgc3RhcnRfaHR0cF9wcm94eShhcmdzLmxhbl9ldGhfaXAsIERFRkFVTFRfSFRUUF9QUk9YWV9TRVJWRVJfUE9SVCkNCg0KICAgIGlmIG9zX3R5cGUgbm90IGluIFsid2luZG93cyJdIG9yIChvc190eXBlIGluIFsid2luZG93cyJdIGFuZCBwb3J0ICE9IDQ0NSk6DQogICAgICAgIGhvc3Rfc29sdXRpb24gPSB0eXBlX19ob3N0X3NvbHV0aW9uX21hcFsic2hlbGwiXQ0KICAgICAgICBleGVjdXRlX3NoZWxsX3NvbHV0aW9uKA0KICAgICAgICAgICAgbG9naW5faXA9bG9naW5faXAsDQogICAgICAgICAgICBhY2NvdW50PXVzZXIsDQogICAgICAgICAgICBwb3J0PXBvcnQsDQogICAgICAgICAgICBhdXRoX3R5cGU9YXV0aF90eXBlLA0KICAgICAgICAgICAgaWRlbnRpdHk9aWRlbnRpdHksDQogICAgICAgICAgICBvc190eXBlPW9zX3R5cGUsDQogICAgICAgICAgICBleGVjdXRpb25fc29sdXRpb249aG9zdF9zb2x1dGlvbiwNCiAgICAgICAgKQ0KICAgIGVsc2U6DQogICAgICAgIGhvc3Rfc29sdXRpb24gPSB0eXBlX19ob3N0X3NvbHV0aW9uX21hcFsiYmF0Y2giXQ0KICAgICAgICBleGVjdXRlX2JhdGNoX3NvbHV0aW9uKA0KICAgICAgICAgICAgbG9naW5faXA9bG9naW5faXAsDQogICAgICAgICAgICBhY2NvdW50PXVzZXIsDQogICAgICAgICAgICBpZGVudGl0eT1pZGVudGl0eSwNCiAgICAgICAgICAgIHRtcF9kaXI9dG1wX2RpciwNCiAgICAgICAgICAgIGV4ZWN1dGlvbl9zb2x1dGlvbj1ob3N0X3NvbHV0aW9uLA0KICAgICAgICApDQoNCiAgICBhcHBfY29yZV9yZW1vdGVfY29ubmVjdHNfdG90YWxfbGFiZWxzID0geyoqZ2V0X2NvbW1vbl9sYWJlbHMoKSwgInN0YXR1cyI6ICJzdWNjZXNzIn0NCiAgICBsb2dnZXIubG9nZ2luZygNCiAgICAgICAgIm1ldHJpY3MiLA0KICAgICAgICBmImFwcF9jb3JlX3JlbW90ZV9jb25uZWN0c190b3RhbF9sYWJlbHMgLT4ge2FwcF9jb3JlX3JlbW90ZV9jb25uZWN0c190b3RhbF9sYWJlbHN9IiwNCiAgICAgICAgbWV0cmljcz17Im5hbWUiOiAiYXBwX2NvcmVfcmVtb3RlX2Nvbm5lY3RzX3RvdGFsIiwgImxhYmVscyI6IGFwcF9jb3JlX3JlbW90ZV9jb25uZWN0c190b3RhbF9sYWJlbHN9LA0KICAgICkNCg0KDQpCeXRlc09yU3RyID0gVW5pb25bc3RyLCBieXRlc10NCg0KDQpjbGFzcyBSZW1vdGVCYXNlRXhjZXB0aW9uKEV4Y2VwdGlvbik6DQogICAgY29kZSA9IDANCg0KDQpjbGFzcyBSdW5DbWRFcnJvcihSZW1vdGVCYXNlRXhjZXB0aW9uKToNCiAgICBjb2RlID0gMQ0KDQoNCmNsYXNzIFBlcm1pc3Npb25EZW5pZWRFcnJvcihSZW1vdGVCYXNlRXhjZXB0aW9uKToNCiAgICBjb2RlID0gMg0KDQoNCmNsYXNzIERpc2Nvbm5lY3RFcnJvcihSZW1vdGVCYXNlRXhjZXB0aW9uKToNCiAgICBjb2RlID0gMw0KDQoNCmNsYXNzIFJlbW90ZVRpbWVvdXRFcnJvcihSZW1vdGVCYXNlRXhjZXB0aW9uKToNCiAgICBjb2RlID0gNA0KDQoNCmNsYXNzIFByb2Nlc3NFcnJvcihSZW1vdGVCYXNlRXhjZXB0aW9uKToNCiAgICBjb2RlID0gNQ0KDQoNCmNsYXNzIFJ1bk91dHB1dDoNCiAgICBjb21tYW5kOiBzdHIgPSBOb25lDQogICAgZXhpdF9zdGF0dXM6IGludCA9IE5vbmUNCiAgICBzdGRvdXQ6IE9wdGlvbmFsW3N0cl0gPSBOb25lDQogICAgc3RkZXJyOiBPcHRpb25hbFtzdHJdID0gTm9uZQ0KDQogICAgZGVmIF9faW5pdF9fKHNlbGYsIGNvbW1hbmQ6IEJ5dGVzT3JTdHIsIGV4aXRfc3RhdHVzOiBpbnQsIHN0ZG91dDogQnl0ZXNPclN0ciwgc3RkZXJyOiBCeXRlc09yU3RyKToNCiAgICAgICAgc2VsZi5leGl0X3N0YXR1cyA9IGV4aXRfc3RhdHVzDQogICAgICAgIHNlbGYuY29tbWFuZCA9IHNlbGYuYnl0ZXMyc3RyKGNvbW1hbmQpDQogICAgICAgIHNlbGYuc3Rkb3V0ID0gc2VsZi5ieXRlczJzdHIoc3Rkb3V0KQ0KICAgICAgICBzZWxmLnN0ZGVyciA9IHNlbGYuYnl0ZXMyc3RyKHN0ZGVycikNCg0KICAgIEBzdGF0aWNtZXRob2QNCiAgICBkZWYgYnl0ZXMyc3RyKHZhbDogQnl0ZXNPclN0cikgLT4gc3RyOg0KICAgICAgICBpZiBpc2luc3RhbmNlKHZhbCwgYnl0ZXMpOg0KICAgICAgICAgICAgdHJ5Og0KICAgICAgICAgICAgICAgIHJldHVybiB2YWwuZGVjb2RlKGVuY29kaW5nPSJ1dGYtOCIpDQogICAgICAgICAgICBleGNlcHQgVW5pY29kZURlY29kZUVycm9yOg0KICAgICAgICAgICAgICAgIHJldHVybiB2YWwuZGVjb2RlKGVuY29kaW5nPSJnYmsiKQ0KICAgICAgICByZXR1cm4gdmFsDQoNCiAgICBkZWYgX19zdHJfXyhzZWxmKToNCiAgICAgICAgb3V0cHV0cyA9IFsNCiAgICAgICAgICAgIGYiZXhpdF9zdGF0dXMgLT4ge3NlbGYuZXhpdF9zdGF0dXN9IiwNCiAgICAgICAgICAgIGYic3Rkb3V0IC0+IHtzZWxmLnN0ZG91dH0iLA0KICAgICAgICAgICAgZiJzdGRlcnIgLT4ge3NlbGYuc3RkZXJyfSIsDQogICAgICAgIF0NCiAgICAgICAgcmV0dXJuICJ8Ii5qb2luKG91dHB1dHMpDQoNCg0KY2xhc3MgQmFzZUNvbm4oYWJjLkFCQyk6DQogICAgIiIi6L+e5o6l5Z+657G7IiIiDQoNCiAgICAjIOi/nuaOpeWcsOWdgOaIluWfn+WQjQ0KICAgIGhvc3Q6IHN0ciA9IE5vbmUNCiAgICAjIOi/nuaOpeerr+WPow0KICAgIHBvcnQ6IGludCA9IE5vbmUNCiAgICAjIOeZu+W9leeUqOaIt+WQjQ0KICAgIHVzZXJuYW1lOiBzdHIgPSBOb25lDQogICAgIyDnmbvlvZXlr4bnoIENCiAgICBwYXNzd29yZDogT3B0aW9uYWxbc3RyXSA9IE5vbmUNCiAgICAjIOeZu+W9leWvhumSpQ0KICAgIGNsaWVudF9rZXlfc3RyaW5nczogT3B0aW9uYWxbTGlzdFtzdHJdXSA9IE5vbmUNCiAgICAjIOi/nuaOpei2heaXtuaXtumXtA0KICAgIGNvbm5lY3RfdGltZW91dDogVW5pb25baW50LCBmbG9hdF0gPSBOb25lDQogICAgIyDmo4Dmn6XlmajliJfooajvvIznlKjkuo7ovpPlh7rpooTlpITnkIYNCiAgICBpbnNwZWN0b3JzOiBMaXN0W0NhbGxhYmxlW1siQmFzZUNvbm4iLCBSdW5PdXRwdXRdLCBOb25lXV0gPSBOb25lDQogICAgIyDov57mjqXlj4LmlbANCiAgICBvcHRpb25zOiBEaWN0W3N0ciwgQW55XSA9IE5vbmUNCiAgICAjIOi/nuaOpeWvueixoQ0KICAgIF9jb25uOiBBbnkgPSBOb25lDQoNCiAgICBkZWYgX19pbml0X18oDQogICAgICAgIHNlbGYsDQogICAgICAgIGhvc3Q6IHN0ciwNCiAgICAgICAgcG9ydDogaW50LA0KICAgICAgICB1c2VybmFtZTogc3RyLA0KICAgICAgICBwYXNzd29yZDogT3B0aW9uYWxbc3RyXSA9IE5vbmUsDQogICAgICAgIGNsaWVudF9rZXlfc3RyaW5nczogT3B0aW9uYWxbTGlzdFtzdHJdXSA9IE5vbmUsDQogICAgICAgIGNvbm5lY3RfdGltZW91dDogT3B0aW9uYWxbVW5pb25baW50LCBmbG9hdF1dID0gTm9uZSwNCiAgICAgICAgaW5zcGVjdG9yczogTGlzdFtDYWxsYWJsZVtbIkJhc2VDb25uIiwgUnVuT3V0cHV0XSwgYm9vbF1dID0gTm9uZSwNCiAgICAgICAgKipvcHRpb25zLA0KICAgICk6DQogICAgICAgIHNlbGYuaG9zdCA9IGhvc3QNCiAgICAgICAgc2VsZi5wb3J0ID0gcG9ydA0KICAgICAgICBzZWxmLnVzZXJuYW1lID0gdXNlcm5hbWUNCiAgICAgICAgc2VsZi5wYXNzd29yZCA9IHBhc3N3b3JkDQogICAgICAgIHNlbGYuY2xpZW50X2tleV9zdHJpbmdzID0gY2xpZW50X2tleV9zdHJpbmdzIG9yIFtdDQogICAgICAgIHNlbGYuY29ubmVjdF90aW1lb3V0ID0gKGNvbm5lY3RfdGltZW91dCwgREVGQVVMVF9DT05ORUNUX1RJTUVPVVQpW2Nvbm5lY3RfdGltZW91dCBpcyBOb25lXQ0KICAgICAgICBzZWxmLmluc3BlY3RvcnMgPSBpbnNwZWN0b3JzIG9yIFtdDQogICAgICAgIHNlbGYub3B0aW9ucyA9IG9wdGlvbnMNCg0KICAgIEBhYmMuYWJzdHJhY3RtZXRob2QNCiAgICBkZWYgY2xvc2Uoc2VsZik6DQogICAgICAgIHJhaXNlIE5vdEltcGxlbWVudGVkRXJyb3INCg0KICAgIEBhYmMuYWJzdHJhY3RtZXRob2QNCiAgICBkZWYgY29ubmVjdChzZWxmKToNCiAgICAgICAgIiIiDQogICAgICAgIOWIm+W7uuS4gOS4qui/nuaOpQ0KICAgICAgICA6cmV0dXJuOg0KICAgICAgICA6cmFpc2VzOg0KICAgICAgICAgICAgS2V5RXhjaGFuZ2VFcnJvcg0KICAgICAgICAgICAgUGVybWlzc2lvbkRlbmllZEVycm9yIOiupOivgeWksei0pQ0KICAgICAgICAgICAgQ29ubmVjdGlvbkxvc3RFcnJvciDov57mjqXkuKLlpLENCiAgICAgICAgICAgIFJlbW90ZVRpbWVvdXRFcnJvciDov57mjqXotoXml7YNCiAgICAgICAgICAgIERpc2Nvbm5lY3RFcnJvciDov5znqIvov57mjqXlpLHotKUNCiAgICAgICAgIiIiDQogICAgICAgIHJhaXNlIE5vdEltcGxlbWVudGVkRXJyb3INCg0KICAgIEBhYmMuYWJzdHJhY3RtZXRob2QNCiAgICBkZWYgX3J1bigNCiAgICAgICAgc2VsZiwgY29tbWFuZDogc3RyLCBjaGVjazogYm9vbCA9IEZhbHNlLCB0aW1lb3V0OiBPcHRpb25hbFtVbmlvbltpbnQsIGZsb2F0XV0gPSBOb25lLCAqKmt3YXJncw0KICAgICkgLT4gUnVuT3V0cHV0Og0KICAgICAgICAiIiLlkb3ku6TmiafooYwiIiINCiAgICAgICAgcmFpc2UgTm90SW1wbGVtZW50ZWRFcnJvcg0KDQogICAgZGVmIHJ1bigNCiAgICAgICAgc2VsZiwgY29tbWFuZDogc3RyLCBjaGVjazogYm9vbCA9IEZhbHNlLCB0aW1lb3V0OiBPcHRpb25hbFtVbmlvbltpbnQsIGZsb2F0XV0gPSBOb25lLCAqKmt3YXJncw0KICAgICkgLT4gUnVuT3V0cHV0Og0KICAgICAgICAiIiINCiAgICAgICAg5ZG95Luk5omn6KGMDQogICAgICAgIDpwYXJhbSBjb21tYW5kOiDlkb3ku6QNCiAgICAgICAgOnBhcmFtIGNoZWNrOiDov5Tlm57noIHpnZ4w5oqb5Ye6IFByb2Nlc3NFcnJvciDlvILluLgNCiAgICAgICAgOnBhcmFtIHRpbWVvdXQ6IOWRveS7pOaJp+ihjOacgOWkp+etieW+heaXtumXtO+8jOi2heaXtuaKm+WHuiBSZW1vdGVUaW1lb3V0RXJyb3Ig5byC5bi4DQogICAgICAgIDpwYXJhbSBrd2FyZ3M6DQogICAgICAgIDpyZXR1cm46DQogICAgICAgIDpyYWlzZXM6DQogICAgICAgICAgICBTZXNzaW9uRXJyb3Ig5Zue6K+d5byC5bi477yM6L+e5o6l6KKr6YeN572u562JDQogICAgICAgICAgICBQcm9jZXNzRXJyb3Ig5ZG95Luk5omn6KGM5byC5bi4DQogICAgICAgICAgICBSZW1vdGVUaW1lb3V0RXJyb3Ig5omn6KGM6LaF5pe2DQogICAgICAgICIiIg0KICAgICAgICBydW5fb3V0cHV0ID0gc2VsZi5fcnVuKGNvbW1hbmQsIGNoZWNrLCB0aW1lb3V0LCAqKmt3YXJncykNCiAgICAgICAgIyDovpPlh7rpooTlpITnkIYNCiAgICAgICAgZm9yIGluc3BlY3RvciBpbiBzZWxmLmluc3BlY3RvcnM6DQogICAgICAgICAgICBpbnNwZWN0b3Ioc2VsZiwgcnVuX291dHB1dCkNCiAgICAgICAgcmV0dXJuIHJ1bl9vdXRwdXQNCg0KICAgIGRlZiBfX2VudGVyX18oc2VsZikgLT4gIkJhc2VDb25uIjoNCiAgICAgICAgc2VsZi5jb25uZWN0KCkNCiAgICAgICAgcmV0dXJuIHNlbGYNCg0KICAgIGRlZiBfX2V4aXRfXyhzZWxmLCBleGNfdHlwZSwgZXhjX3ZhbCwgZXhjX3RiKToNCiAgICAgICAgc2VsZi5jbG9zZSgpDQogICAgICAgIHNlbGYuX2Nvbm4gPSBOb25lDQoNCg0KY2xhc3MgUGFyYW1pa29Db25uKEJhc2VDb25uKToNCiAgICAiIiINCiAgICDln7rkuo4gcGFyYW1pa28g5a6e546w55qE5ZCM5q2lIFNTSCDov57mjqUNCiAgICBwYXJhbWlrbw0KICAgICAgICDku5PlupPvvJpodHRwczovL2dpdGh1Yi5jb20vcGFyYW1pa28vcGFyYW1pa28NCiAgICAgICAg5paH5qGj77yaaHR0cHM6Ly93d3cucGFyYW1pa28ub3JnLw0KICAgICIiIg0KDQogICAgX2Nvbm46IE9wdGlvbmFsW3BhcmFtaWtvLlNTSENsaWVudF0gPSBOb25lDQoNCiAgICBAc3RhdGljbWV0aG9kDQogICAgZGVmIGdldF9rZXlfaW5zdGFuY2Uoa2V5X2NvbnRlbnQ6IHN0cik6DQoNCiAgICAgICAgbWF0Y2hlZF9wcml2YXRlX2tleSA9IEpPQl9QUklWQVRFX0tFWV9SRS5tYXRjaChrZXlfY29udGVudCkNCiAgICAgICAgaWYgbWF0Y2hlZF9wcml2YXRlX2tleToNCiAgICAgICAgICAgIHN0YXJ0LCBjb250ZW50LCBlbmQgPSBtYXRjaGVkX3ByaXZhdGVfa2V5Lmdyb3VwcygpDQogICAgICAgICAgICAjIOS9nOS4muW5s+WPsOS8oOWPguWQjmtleeeahOaNouihjOespuiiq+i9rOS5ieS4uuOAkOepuuagvOOAke+8jOmcgOmHjeaWsOabv+aNouS4uuaNouihjOespg0KICAgICAgICAgICAgY29udGVudCA9IGNvbnRlbnQucmVwbGFjZSgiICIsICJcbiIpDQogICAgICAgICAgICAjIOaJi+WKqOWuieijheWRveS7pGtleeeahOaNouihjOespuiiq+i9rOS5ieS4uiBcbiDlrZfnrKbkuLLvvIzpnIDph43mlrDmm7/mjaLkuLrmjaLooYznrKYNCiAgICAgICAgICAgIGNvbnRlbnQgPSBjb250ZW50LnJlcGxhY2UoIlxcbiIsICJcbiIpDQogICAgICAgICAgICBrZXlfY29udGVudCA9IGYie3N0YXJ0fXtjb250ZW50fXtlbmR9Ig0KDQogICAgICAgIGtleV9pbnN0YW5jZSA9IE5vbmUNCiAgICAgICAgd2l0aCBTdHJpbmdJTyhrZXlfY29udGVudCkgYXMga2V5X2ZpbGU6DQogICAgICAgICAgICBmb3IgY2xzIGluIFtwYXJhbWlrby5SU0FLZXksIHBhcmFtaWtvLkRTU0tleSwgcGFyYW1pa28uRUNEU0FLZXksIHBhcmFtaWtvLkVkMjU1MTlLZXldOg0KICAgICAgICAgICAgICAgIHRyeToNCiAgICAgICAgICAgICAgICAgICAga2V5X2luc3RhbmNlID0gY2xzLmZyb21fcHJpdmF0ZV9rZXkoa2V5X2ZpbGUpDQogICAgICAgICAgICAgICAgICAgIGxvZ2dlci5sb2dnaW5nKCJbZ2V0X2tleV9pbnN0YW5jZV0iLCBmIm1hdGNoIHtjbHMuX19uYW1lX199IiwgaXNfcmVwb3J0PUZhbHNlKQ0KICAgICAgICAgICAgICAgICAgICBicmVhaw0KICAgICAgICAgICAgICAgIGV4Y2VwdCBwYXJhbWlrby5zc2hfZXhjZXB0aW9uLlBhc3N3b3JkUmVxdWlyZWRFeGNlcHRpb246DQogICAgICAgICAgICAgICAgICAgIHJhaXNlIFBlcm1pc3Npb25EZW5pZWRFcnJvcigiUGFzc3dvcmQgaXMgcmVxdWlyZWQgZm9yIHRoZSBwcml2YXRlIGtleSIpDQogICAgICAgICAgICAgICAgZXhjZXB0IHBhcmFtaWtvLnNzaF9leGNlcHRpb24uU1NIRXhjZXB0aW9uOg0KICAgICAgICAgICAgICAgICAgICBsb2dnZXIubG9nZ2luZygiW2dldF9rZXlfaW5zdGFuY2VdIiwgZiJub3QgbWF0Y2gge2Nscy5fX25hbWVfX30sIHNraXBwZWQiLCBpc19yZXBvcnQ9RmFsc2UpDQogICAgICAgICAgICAgICAgICAgIGtleV9maWxlLnNlZWsoMCkNCiAgICAgICAgICAgICAgICAgICAgY29udGludWUNCg0KICAgICAgICBpZiBub3Qga2V5X2luc3RhbmNlOg0KICAgICAgICAgICAgcmFpc2UgUGVybWlzc2lvbkRlbmllZEVycm9yKCJVbnN1cHBvcnRlZCBrZXkgdHlwZSIpDQoNCiAgICAgICAgcmV0dXJuIGtleV9pbnN0YW5jZQ0KDQogICAgZGVmIGNsb3NlKHNlbGYpOg0KICAgICAgICBzZWxmLl9jb25uLmNsb3NlKCkNCg0KICAgIGRlZiBjb25uZWN0KHNlbGYpIC0+IHBhcmFtaWtvLlNTSENsaWVudDoNCiAgICAgICAgc3NoID0gcGFyYW1pa28uU1NIQ2xpZW50KCkNCiAgICAgICAgc3NoLnNldF9taXNzaW5nX2hvc3Rfa2V5X3BvbGljeShwYXJhbWlrby5BdXRvQWRkUG9saWN5KCkpDQoNCiAgICAgICAgIyDku4XmlK/mjIHljZXkuKrlr4bpkqUNCiAgICAgICAgaWYgc2VsZi5jbGllbnRfa2V5X3N0cmluZ3M6DQogICAgICAgICAgICBwa2V5ID0gc2VsZi5nZXRfa2V5X2luc3RhbmNlKHNlbGYuY2xpZW50X2tleV9zdHJpbmdzWzBdKQ0KICAgICAgICBlbHNlOg0KICAgICAgICAgICAgcGtleSA9IE5vbmUNCg0KICAgICAgICAjIEFQSSDmlofmoaPvvJpodHRwczovL2RvY3MucGFyYW1pa28ub3JnL2VuL3N0YWJsZS9hcGkvY2xpZW50Lmh0bWwjcGFyYW1pa28uY2xpZW50LlNTSENsaWVudC5jb25uZWN0DQogICAgICAgICMg6K6k6K+B6aG65bqP77yaDQogICAgICAgICMgIC0gcGtleSBvciBrZXlfZmlsZW5hbWUNCiAgICAgICAgIyAgLSBBbnkg4oCcaWRfcnNh4oCdLCDigJxpZF9kc2HigJ0gb3Ig4oCcaWRfZWNkc2HigJ0ga2V5IGRpc2NvdmVyYWJsZSBpbiB+Ly5zc2gvIChsb29rX2Zvcl9rZXlzPVRydWUpDQogICAgICAgICMgIC0gdXNlcm5hbWUvcGFzc3dvcmQgYXV0aCwgaWYgYSBwYXNzd29yZCB3YXMgZ2l2ZW4NCiAgICAgICAgdHJ5Og0KICAgICAgICAgICAgc3NoLmNvbm5lY3QoDQogICAgICAgICAgICAgICAgaG9zdG5hbWU9c2VsZi5ob3N0LA0KICAgICAgICAgICAgICAgIHBvcnQ9c2VsZi5wb3J0LA0KICAgICAgICAgICAgICAgIHVzZXJuYW1lPXNlbGYudXNlcm5hbWUsDQogICAgICAgICAgICAgICAgcGtleT1wa2V5LA0KICAgICAgICAgICAgICAgIHBhc3N3b3JkPXNlbGYucGFzc3dvcmQsDQogICAgICAgICAgICAgICAgdGltZW91dD1zZWxmLmNvbm5lY3RfdGltZW91dCwNCiAgICAgICAgICAgICAgICBhbGxvd19hZ2VudD1GYWxzZSwNCiAgICAgICAgICAgICAgICAjIOS7juWuieWFqOS4iuiAg+iZke+8jOemgeeUqOacrOWcsFJTQeengemSpeaJq+aPjw0KICAgICAgICAgICAgICAgIGxvb2tfZm9yX2tleXM9RmFsc2UsDQogICAgICAgICAgICAgICAgKipzZWxmLm9wdGlvbnMsDQogICAgICAgICAgICApDQogICAgICAgIGV4Y2VwdCBwYXJhbWlrby5CYWRIb3N0S2V5RXhjZXB0aW9uIGFzIGU6DQogICAgICAgICAgICByYWlzZSBQZXJtaXNzaW9uRGVuaWVkRXJyb3IoZiJLZXkgdmVyaWZpY2F0aW9uIGZhaWxlZO+8mntlfSIpIGZyb20gZQ0KICAgICAgICBleGNlcHQgcGFyYW1pa28uQXV0aGVudGljYXRpb25FeGNlcHRpb24gYXMgZToNCiAgICAgICAgICAgIHJhaXNlIFBlcm1pc3Npb25EZW5pZWRFcnJvcigNCiAgICAgICAgICAgICAgICBmIkF1dGhlbnRpY2F0aW9uIGZhaWxlZCwgcGxlYXNlIGNoZWNrIHRoZSBhdXRoZW50aWNhdGlvbiBpbmZvcm1hdGlvbiBmb3IgZXJyb3JzOiB7ZX0iDQogICAgICAgICAgICApIGZyb20gZQ0KICAgICAgICBleGNlcHQgKHBhcmFtaWtvLlNTSEV4Y2VwdGlvbiwgc29ja2V0LmVycm9yLCBFeGNlcHRpb24pIGFzIGU6DQogICAgICAgICAgICByYWlzZSBEaXNjb25uZWN0RXJyb3IoZiJSZW1vdGUgY29ubmVjdGlvbiBmYWlsZWQ6IHtlfSIpIGZyb20gZQ0KICAgICAgICBzZWxmLl9jb25uID0gc3NoDQogICAgICAgIHJldHVybiBzc2gNCg0KICAgIGRlZiBfcnVuKA0KICAgICAgICBzZWxmLCBjb21tYW5kOiBzdHIsIGNoZWNrOiBib29sID0gRmFsc2UsIHRpbWVvdXQ6IE9wdGlvbmFsW1VuaW9uW2ludCwgZmxvYXRdXSA9IE5vbmUsICoqa3dhcmdzDQogICAgKSAtPiBSdW5PdXRwdXQ6DQoNCiAgICAgICAgYmVnaW5fdGltZSA9IHRpbWUudGltZSgpDQogICAgICAgIHRyeToNCiAgICAgICAgICAgIF9fLCBzdGRvdXQsIHN0ZGVyciA9IHNlbGYuX2Nvbm4uZXhlY19jb21tYW5kKGNvbW1hbmQ9Y29tbWFuZCwgdGltZW91dD10aW1lb3V0KQ0KICAgICAgICAgICAgIyDojrflj5YgZXhpdF9zdGF0dXMg5pa55byP5Y+C6ICD77yaaHR0cHM6Ly9zdGFja292ZXJmbG93LmNvbS9xdWVzdGlvbnMvMzU2MjQwMy8NCiAgICAgICAgICAgIGV4aXRfc3RhdHVzID0gc3Rkb3V0LmNoYW5uZWwucmVjdl9leGl0X3N0YXR1cygpDQogICAgICAgIGV4Y2VwdCBwYXJhbWlrby5TU0hFeGNlcHRpb24gYXMgZToNCiAgICAgICAgICAgIGlmIGNoZWNrOg0KICAgICAgICAgICAgICAgIHJhaXNlIFByb2Nlc3NFcnJvcihmIkNvbW1hbmQgcmV0dXJuZWQgbm9uLXplcm86IHtlfSIpDQogICAgICAgICAgICAjIGV4ZWNfY29tbWFuZCDmlrnms5XmsqHmnInmmI7noa7mipvlh7ogdGltZW91dCDlvILluLjvvIzpnIDopoHorrDlvZXosIPnlKjliY3lkI7ml7bpl7Tlt67ov5vooYzmipvlh7oNCiAgICAgICAgICAgIGNvc3RfdGltZSA9IHRpbWUudGltZSgpIC0gYmVnaW5fdGltZQ0KICAgICAgICAgICAgaWYgY29zdF90aW1lID4gdGltZW91dDoNCiAgICAgICAgICAgICAgICByYWlzZSBSZW1vdGVUaW1lb3V0RXJyb3IoZiJDb25uZWN0IHRpbWVvdXTvvJp7ZX0iKSBmcm9tIGUNCiAgICAgICAgICAgIGV4aXRfc3RhdHVzLCBzdGRvdXQsIHN0ZGVyciA9IDEsIFN0cmluZ0lPKCIiKSwgU3RyaW5nSU8oc3RyKGUpKQ0KICAgICAgICByZXR1cm4gUnVuT3V0cHV0KGNvbW1hbmQ9Y29tbWFuZCwgZXhpdF9zdGF0dXM9ZXhpdF9zdGF0dXMsIHN0ZG91dD1zdGRvdXQucmVhZCgpLCBzdGRlcnI9c3RkZXJyLnJlYWQoKSkNCg0KDQppZiBfX25hbWVfXyA9PSAiX19tYWluX18iOg0KDQogICAgX3BhcmFtaWtvX3ZlcnNpb246IHN0ciA9ICItIg0KICAgIHRyeToNCiAgICAgICAgX3BhcmFtaWtvX3ZlcnNpb24gPSBzdHIocGFyYW1pa28uX192ZXJzaW9uX18pDQogICAgZXhjZXB0IEV4Y2VwdGlvbjoNCiAgICAgICAgbG9nZ2VyLmxvZ2dpbmcoInByb3h5IiwgIkZhaWxlZCB0byBnZXQgcGFyYW1pa28gdmVyc2lvbiIsIGlzX3JlcG9ydD1GYWxzZSwgbGV2ZWw9bG9nZ2luZy5XQVJOSU5HKQ0KDQogICAgX2FwcF9jb3JlX3JlbW90ZV9wcm94eV9pbmZvX2xhYmVscyA9IHsNCiAgICAgICAgInByb3h5X25hbWUiOiBzb2NrZXQuZ2V0aG9zdG5hbWUoKSwNCiAgICAgICAgInByb3h5X2lwIjogYXJncy5sYW5fZXRoX2lwLA0KICAgICAgICAiYmtfY2xvdWRfaWQiOiBhcmdzLmhvc3RfY2xvdWQsDQogICAgICAgICJwYXJhbWlrb192ZXJzaW9uIjogX3BhcmFtaWtvX3ZlcnNpb24sDQogICAgfQ0KICAgIGxvZ2dlci5sb2dnaW5nKA0KICAgICAgICAibWV0cmljcyIsDQogICAgICAgIGYiYXBwX2NvcmVfcmVtb3RlX3Byb3h5X2luZm9fbGFiZWxzIC0+IHtfYXBwX2NvcmVfcmVtb3RlX3Byb3h5X2luZm9fbGFiZWxzfSIsDQogICAgICAgIG1ldHJpY3M9eyJuYW1lIjogImFwcF9jb3JlX3JlbW90ZV9wcm94eV9pbmZvIiwgImxhYmVscyI6IF9hcHBfY29yZV9yZW1vdGVfcHJveHlfaW5mb19sYWJlbHN9LA0KICAgICkNCg0KICAgIGxvZ2dlci5sb2dnaW5nKCJwcm94eSIsICJzZXR1cF9wYWdlbnQyIHdpbGwgc3RhcnQgcnVubmluZyBub3cuIiwgaXNfcmVwb3J0PUZhbHNlKQ0KICAgIF9zdGFydCA9IHRpbWUucGVyZl9jb3VudGVyKCkNCg0KICAgIHRyeToNCiAgICAgICAgbWFpbigpDQogICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBfZToNCiAgICAgICAgX2FwcF9jb3JlX3JlbW90ZV9jb25uZWN0c190b3RhbF9sYWJlbHMgPSB7KipnZXRfY29tbW9uX2xhYmVscygpLCAic3RhdHVzIjogImZhaWxlZCJ9DQogICAgICAgIGxvZ2dlci5sb2dnaW5nKA0KICAgICAgICAgICAgIm1ldHJpY3MiLA0KICAgICAgICAgICAgZiJhcHBfY29yZV9yZW1vdGVfY29ubmVjdHNfdG90YWxfbGFiZWxzIC0+IHtfYXBwX2NvcmVfcmVtb3RlX2Nvbm5lY3RzX3RvdGFsX2xhYmVsc30iLA0KICAgICAgICAgICAgbWV0cmljcz17Im5hbWUiOiAiYXBwX2NvcmVfcmVtb3RlX2Nvbm5lY3RzX3RvdGFsIiwgImxhYmVscyI6IF9hcHBfY29yZV9yZW1vdGVfY29ubmVjdHNfdG90YWxfbGFiZWxzfSwNCiAgICAgICAgKQ0KDQogICAgICAgIGlmIGlzaW5zdGFuY2UoX2UsIFJlbW90ZUJhc2VFeGNlcHRpb24pOg0KICAgICAgICAgICAgZXhjX3R5cGUgPSAiYXBwIg0KICAgICAgICAgICAgZXhjX2NvZGUgPSBzdHIoX2UuY29kZSkNCiAgICAgICAgZWxzZToNCiAgICAgICAgICAgIGV4Y190eXBlID0gInVua25vd24iDQogICAgICAgICAgICBleGNfY29kZSA9IF9lLl9fY2xhc3NfXy5fX25hbWVfXw0KDQogICAgICAgIF9hcHBfY29yZV9yZW1vdGVfY29ubmVjdF9leGNlcHRpb25zX3RvdGFsX2xhYmVscyA9IHsNCiAgICAgICAgICAgICoqZ2V0X2NvbW1vbl9sYWJlbHMoKSwNCiAgICAgICAgICAgICJleGNfdHlwZSI6IGV4Y190eXBlLA0KICAgICAgICAgICAgImV4Y19jb2RlIjogZXhjX2NvZGUsDQogICAgICAgIH0NCiAgICAgICAgbG9nZ2VyLmxvZ2dpbmcoDQogICAgICAgICAgICAibWV0cmljcyIsDQogICAgICAgICAgICBmImFwcF9jb3JlX3JlbW90ZV9jb25uZWN0X2V4Y2VwdGlvbnNfdG90YWxfbGFiZWxzIC0+IHtfYXBwX2NvcmVfcmVtb3RlX2Nvbm5lY3RfZXhjZXB0aW9uc190b3RhbF9sYWJlbHN9IiwNCiAgICAgICAgICAgIG1ldHJpY3M9ew0KICAgICAgICAgICAgICAgICJuYW1lIjogImFwcF9jb3JlX3JlbW90ZV9jb25uZWN0X2V4Y2VwdGlvbnNfdG90YWwiLA0KICAgICAgICAgICAgICAgICJsYWJlbHMiOiBfYXBwX2NvcmVfcmVtb3RlX2Nvbm5lY3RfZXhjZXB0aW9uc190b3RhbF9sYWJlbHMsDQogICAgICAgICAgICB9LA0KICAgICAgICApDQogICAgICAgIGxvZ2dlci5sb2dnaW5nKCJwcm94eV9mYWlsIiwgc3RyKF9lKSwgbGV2ZWw9bG9nZ2luZy5FUlJPUikNCiAgICAgICAgbG9nZ2VyLmxvZ2dpbmcoInByb3h5X2ZhaWwiLCB0cmFjZWJhY2suZm9ybWF0X2V4YygpLCBsZXZlbD1sb2dnaW5nLkVSUk9SLCBpc19yZXBvcnQ9RmFsc2UpDQogICAgZWxzZToNCiAgICAgICAgX2FwcF9jb3JlX3JlbW90ZV9leGVjdXRlX2R1cmF0aW9uX3NlY29uZHNfbGFiZWxzID0geyJtZXRob2QiOiAoInByb3h5X3dtaWV4ZSIsICJwcm94eV9zc2giKVt1c2Vfc2hlbGwoKV19DQogICAgICAgIGNvc3RfdGltZSA9IHRpbWUucGVyZl9jb3VudGVyKCkgLSBfc3RhcnQNCiAgICAgICAgbG9nZ2VyLmxvZ2dpbmcoDQogICAgICAgICAgICAibWV0cmljcyIsDQogICAgICAgICAgICBmImFwcF9jb3JlX3JlbW90ZV9leGVjdXRlX2R1cmF0aW9uX3NlY29uZHNfbGFiZWxzIC0+IHtfYXBwX2NvcmVfcmVtb3RlX2V4ZWN1dGVfZHVyYXRpb25fc2Vjb25kc19sYWJlbHN9IiwNCiAgICAgICAgICAgIG1ldHJpY3M9ew0KICAgICAgICAgICAgICAgICJuYW1lIjogImFwcF9jb3JlX3JlbW90ZV9leGVjdXRlX2R1cmF0aW9uX3NlY29uZHMiLA0KICAgICAgICAgICAgICAgICJsYWJlbHMiOiBfYXBwX2NvcmVfcmVtb3RlX2V4ZWN1dGVfZHVyYXRpb25fc2Vjb25kc19sYWJlbHMsDQogICAgICAgICAgICAgICAgImRhdGEiOiB7ImNvc3RfdGltZSI6IGNvc3RfdGltZX0sDQogICAgICAgICAgICB9LA0KICAgICAgICApDQogICAgICAgIGxvZ2dlci5sb2dnaW5nKCJwcm94eSIsIGYic2V0dXBfcGFnZW50MiBzdWNjZWVkZWQ6IGNvc3RfdGltZSAtPiB7Y29zdF90aW1lfSIsIGlzX3JlcG9ydD1GYWxzZSkNCg==",
            "script_param": base64.b64encode(execution_solution.steps[0].contents[0].text.encode()).decode(),
            "is_param_sensitive": constants.BkJobParamSensitiveType.YES.value,
        }
        data = JobApi.fast_execute_script(kwargs)
        job_instance_id = data.get("job_instance_id")
        self.log_info(
            sub_inst_ids=sub_inst_id,
            log_content=_('作业任务ID为[{job_instance_id}]，点击跳转到<a href="{link}" target="_blank">[作业平台]</a>').format(
                job_instance_id=job_instance_id,
                link=f"{settings.BK_JOB_HOST}/api_execute/{job_instance_id}",
            ),
        )
        name = REDIS_INSTALL_CALLBACK_KEY_TPL.format(sub_inst_id=sub_inst_id)
        REDIS_INST.lpush(
            name,
            json.dumps(
                {
                    "timestamp": time.time(),
                    "level": "INFO",
                    "step": "wait_for_job",
                    "log": _(
                        "作业执行中，如果卡在这里较长时间，请检查：\n"
                        "1. P-Agent({host_inner_ip}) 到 Proxy({jump_server_ip})"
                        " 的 {download_port}、{proxy_pass_port} 是否可连通。 \n"
                        "2. Proxy是否已正确完成所有安装步骤且状态正常。 \n"
                        "3. 点击上面链接跳转到作业平台查看任务执行情况。\n"
                    ).format(
                        host_inner_ip=host.inner_ip or host.inner_ipv6,
                        jump_server_ip=jump_server.inner_ip or host.inner_ipv6,
                        download_port=settings.BK_NODEMAN_NGINX_DOWNLOAD_PORT,
                        proxy_pass_port=settings.BK_NODEMAN_NGINX_PROXY_PASS_PORT,
                    ),
                    "status": "-",
                    "job_status_kwargs": {"bk_biz_id": bk_biz_id, "job_instance_id": job_instance_id},
                    "prefix": "job",
                }
            ),
        )
        # 执行后更新主机的上游节点
        host.upstream_nodes = [proxy.inner_ip for proxy in installation_tool.proxies]
        host.save(update_fields=["upstream_nodes"])
        return sub_inst_id

    @ExceptionHandler(
        exc_handler=execute_shell_solution_async_exc_handler,
        success_handler=execute_shell_solution_async_success_handler,
    )
    @SetupObserve(
        histogram=metrics.app_core_remote_execute_duration_seconds,
        labels={"method": "ssh"},
        # 不统计异常耗时
        include_exception_histogram=False,
    )
    async def execute_shell_solution_async(
        self, meta: Dict[str, Any], sub_inst_id: int, install_sub_inst_obj: InstallSubInstObj
    ) -> int:
        """
        执行 Shell 方案
        :param meta:
        :param sub_inst_id:
        :param install_sub_inst_obj:
        :return:
        """
        translation.activate(meta["blueking_language"])

        # sudo 权限提示
        await self.sudo_prompt(install_sub_inst_obj)

        # 解决如下报错
        # django.core.exceptions.SynchronousOnlyOperation: You cannot call this from an async context -
        # use a thread or sync_to_async.
        # 参考：https://docs.djangoproject.com/en/3.2/topics/async/
        log_info = sync.sync_to_async(self.log_info)
        installation_tool = install_sub_inst_obj.installation_tool
        execution_solution = installation_tool.type__execution_solution_map[
            constants.CommonExecutionSolutionType.SHELL.value
        ]
        command_converter: Dict = {}

        async with conns.AsyncsshConn(**install_sub_inst_obj.conns_init_params) as conn:
            if install_sub_inst_obj.host.os_type == constants.OsType.WINDOWS:
                sshd_info = await conn.run(POWERSHELL_SERVICE_CHECK_SSHD, check=True, timeout=SSH_RUN_TIMEOUT)
                sshd_info = sshd_info.stdout.lower()
                self.build_shell_to_batch_command_converter(execution_solution.steps, command_converter, sshd_info)

            for execution_solution_step in execution_solution.steps:
                if execution_solution_step.type == constants.CommonExecutionSolutionStepType.DEPENDENCIES.value:
                    localpaths = [
                        os.path.join(settings.BK_SCRIPTS_PATH, content.name)
                        for content in execution_solution_step.contents
                    ]
                    if installation_tool.host.os_type == constants.OsType.WINDOWS:
                        dest_dir = installation_tool.dest_dir.replace("\\", "/")
                    else:
                        dest_dir = installation_tool.dest_dir

                    async with await conn.file_client() as file_client:
                        await file_client.makedirs(path=installation_tool.dest_dir)
                        await log_info(
                            sub_inst_ids=install_sub_inst_obj.sub_inst_id,
                            log_content=_("推送下列文件到「{dest_dir}」\n{filenames_str}").format(
                                dest_dir=dest_dir, filenames_str="\n".join(localpaths)
                            ),
                        )
                        await file_client.put(localpaths=localpaths, remotepath=installation_tool.dest_dir)

                elif execution_solution_step.type == constants.CommonExecutionSolutionStepType.COMMANDS.value:
                    for content in execution_solution_step.contents:
                        cmd = command_converter.get(content.text, content.text)
                        if not cmd:
                            continue
                        await log_info(sub_inst_ids=sub_inst_id, log_content=_("执行命令: {cmd}").format(cmd=cmd))
                        await conn.run(command=cmd, check=True, timeout=SSH_RUN_TIMEOUT)

        return sub_inst_id

    @classmethod
    def convert_shell_to_powershell(cls, shell_cmd):
        # Convert mkdir -p xxx to if not exist xxx mkdir xxx
        shell_cmd = re.sub(
            r"mkdir -p\s+(\S+)",
            r"powershell -c 'if (-Not (Test-Path -Path \1)) { New-Item -ItemType Directory -Path \1 }'",
            shell_cmd,
        )

        # Convert chmod +x xxx to ''
        shell_cmd = re.sub(r"chmod\s+\+x\s+\S+", r"", shell_cmd)

        # Convert curl to Invoke-WebRequest
        # shell_cmd = re.sub(
        #     r"curl\s+(http[s]?:\/\/[^\s]+)\s+-o\s+(\/?[^\s]+)\s+--connect-timeout\s+(\d+)\s+-sSfg",
        #     r"powershell -c 'Invoke-WebRequest -Uri \1 -OutFile \2 -TimeoutSec \3 -UseBasicParsing'",
        #     shell_cmd,
        # )
        shell_cmd = re.sub(r"(curl\s+\S+\s+-o\s+\S+\s+--connect-timeout\s+\d+\s+-sSfg)", r'cmd /c "\1"', shell_cmd)

        # Convert nohup xxx &> ... & to xxx (ignore nohup, output redirection and background execution)
        shell_cmd = re.sub(
            r"nohup\s+([^&>]+)(\s*&>\s*.*?&)?",
            r"powershell -c 'Invoke-Command -Session (New-PSSession) -ScriptBlock { \1 } -AsJob'",
            shell_cmd,
        )

        # Remove '&>' and everything after it
        shell_cmd = re.sub(r"\s*&>.*", "", shell_cmd)

        # Convert \\ to \
        shell_cmd = shell_cmd.replace("\\\\", "\\")

        return shell_cmd.strip()

    def build_shell_to_batch_command_converter(self, steps, command_converter, sshd_info):
        if "cygwin" in sshd_info:
            return

        for execution_solution_step in steps:
            if execution_solution_step.type == constants.CommonExecutionSolutionStepType.COMMANDS.value:
                for content in execution_solution_step.contents:
                    cmd = content.text
                    command_converter[cmd] = self.convert_shell_to_powershell(cmd)

    def handle_report_data(self, host: models.Host, sub_inst_id: int, success_callback_step: str) -> Dict:
        """处理上报数据"""
        name = REDIS_INSTALL_CALLBACK_KEY_TPL.format(sub_inst_id=sub_inst_id)
        # 先计算出要从redis取数据的长度
        report_data_len = REDIS_INST.llen(name)
        # 从redis中取出对应长度的数据
        report_data = REDIS_INST.lrange(name, -report_data_len, -1)
        # 后使用ltrim保留剩下的，可以保证report_log中新push的值不会丢失
        REDIS_INST.ltrim(name, 0, -report_data_len - 1)
        report_data.reverse()
        cpu_arch = None
        os_version = None
        agent_id = None
        is_finished = False
        error_log = ""
        logs = []
        for data in report_data:
            # redis取出为bytes类型，进行解码
            data = json.loads(data.decode())
            step = data["step"]
            tag = data.get("prefix") or "[script]"
            log = f"{tag} [{step}] {data['log']}"
            status = data["status"]
            labels = {"step": step, "os_type": host.os_type, "node_type": host.node_type}
            if status == "FAILED":
                error_log = log
                logger.warning(
                    f"[app_core_remote:handle_report_data:scripts_error] install failed: sub_inst_id -> {sub_inst_id}, "
                    f"ip -> {host.inner_ip or host.inner_ipv6}, labels -> {labels}, log -> {error_log}"
                )
                metrics.app_core_remote_install_exceptions_total.labels(**labels).inc()
                is_finished = True
            else:
                if step != "metrics":
                    logs.append(log)

            if step == "report_cpu_arch":
                cpu_arch = data["log"]
            elif step == "report_agent_id":
                agent_id = data["log"]
            elif step == "report_os_version":
                os_version = data["log"]
            elif step in ["report_healthz"]:
                # 考虑解析 healthz 输出，进行友好提示
                untreated_healthz_result: str = data["log"]
                try:
                    # 尝试 b64 解析 healthz 日志
                    untreated_healthz_result = base64.b64decode(untreated_healthz_result.encode()).decode()
                except binascii.Error:
                    pass

                # 去除可能存在的前缀
                if untreated_healthz_result.startswith("healthz:"):
                    untreated_healthz_result = untreated_healthz_result.replace("healthz:", "", 1)

                # 去除多余的空白符号
                healthz_result = untreated_healthz_result.strip()

                try:
                    # 尝试将 healthz 输出转为字典格式
                    healthz_result_dict = json.loads(healthz_result)
                    if not isinstance(healthz_result_dict, dict):
                        raise json.decoder.JSONDecodeError
                except json.decoder.JSONDecodeError:
                    # 如果 healthz 不可解析，记录原文并打上标记
                    healthz_result_dict = {"is_parseable": False, "log": data["log"]}
                    logger.warning(
                        f"[app_core_remote:handle_report_data:scripts_error] healthz decode failed: "
                        f"sub_inst_id -> {sub_inst_id}, ip -> {host.inner_ip or host.inner_ipv6}, labels -> {labels}, "
                        f"result -> {healthz_result_dict}"
                    )
                    metrics.app_core_remote_install_exceptions_total.labels(**labels).inc()

                logs.append(f"{tag} [{step}] parse healthz result: \n {json.dumps(healthz_result_dict, indent=4)}")

            elif step == "metrics":
                logger.info(f"[app_core_remote:handle_report_data] sub_inst_id -> {sub_inst_id}, data -> {data}")
                try:
                    name: str = data["metrics"]["name"]
                    if name == "app_core_remote_proxy_info":
                        metrics.app_core_remote_proxy_info.labels(**data["metrics"]["labels"]).set(1)
                    elif name == "app_core_remote_connect_exceptions_total":
                        metrics.app_core_remote_connect_exceptions_total.labels(**data["metrics"]["labels"]).inc()
                    elif name == "app_core_remote_execute_duration_seconds":
                        metrics.app_core_remote_execute_duration_seconds.labels(**data["metrics"]["labels"]).observe(
                            data["metrics"]["data"]["cost_time"]
                        )
                    elif name == "app_core_remote_connects_total":
                        metrics.app_core_remote_connects_total.labels(**data["metrics"]["labels"]).inc()
                except Exception:
                    logger.exception(
                        f"[app_core_remote:handle_report_data:metrics] sub_inst_id -> {sub_inst_id}, data -> {data}"
                    )
                    metrics.app_core_remote_install_exceptions_total.labels(**labels).inc()

            # 只要匹配到成功返回步骤完成，则认为是执行完成了
            if step == success_callback_step and status == "DONE":
                is_finished = True
        # 并非每次调度都能取到日志，所以仅在非空情况下打印日志
        if logs:
            # 多行日志批量打印时，非起始日志需要补充时间等前缀，提升美观度
            logs = [logs[0]] + [
                self.log_maker_class.get_log_content(level=LogLevel.INFO, content=log)
                for log in logs[1:]
                if len(log.strip())
            ]
            self.log_info(sub_inst_ids=sub_inst_id, log_content="\n".join(logs))
        if error_log:
            self.move_insts_to_failed([sub_inst_id], log_content=error_log)
        return {
            "sub_inst_id": sub_inst_id,
            "is_finished": is_finished,
            "cpu_arch": cpu_arch,
            "os_version": os_version,
            "agent_id": agent_id,
        }

    def _schedule(self, data, parent_data, callback_data=None):
        """通过轮询redis的方式来处理，避免使用callback的方式频繁调用schedule"""
        common_data = self.get_common_data(data)
        success_callback_step = data.get_one_of_inputs("success_callback_step")
        # 与上一轮次的订阅实例ID取交集，确保本轮次需执行的订阅实例ID已排除手动终止的情况
        scheduling_sub_inst_ids = (
            set(data.get_one_of_outputs("scheduling_sub_inst_ids", [])) & common_data.subscription_instance_ids
        )
        if not scheduling_sub_inst_ids:
            self.finish_schedule()
            return

        params_list = []
        for sub_inst_id in scheduling_sub_inst_ids:
            host: Optional[models.Host] = self.get_host(common_data, common_data.sub_inst_id__host_id_map[sub_inst_id])
            if not host:
                continue

            params_list.append(
                {
                    "host": host,
                    "sub_inst_id": sub_inst_id,
                    "success_callback_step": success_callback_step,
                }
            )

        host_id__sub_inst_map: Dict[int, models.SubscriptionInstanceRecord] = {
            common_data.sub_inst_id__host_id_map[sub_inst.id]: sub_inst
            for sub_inst in common_data.subscription_instances
        }
        results = concurrent.batch_call(func=self.handle_report_data, params_list=params_list)
        left_scheduling_sub_inst_ids = []
        host_info_list = []
        os_version__host_id_map = defaultdict(list)
        host_id__agent_id_map: Dict[int, str] = {}
        for result in results:
            # 对于未完成的实例，记录下来到下一次schedule中继续检查
            if not result["is_finished"]:
                left_scheduling_sub_inst_ids.append(result["sub_inst_id"])
            # 按 CPU 架构对主机进行分组
            bk_host_id = common_data.sub_inst_id__host_id_map.get(result["sub_inst_id"])
            if result["cpu_arch"]:
                host_info_list.append({"bk_host_id": bk_host_id, "report_cpu_arch": result["cpu_arch"]})
            # 记录不为空的 agent_id 和 bk_host_id 的对应关系
            agent_id: str = result.get("agent_id") or ""
            agent_id = agent_id.split(":")[-1].strip()
            if agent_id:
                host_id__agent_id_map[bk_host_id] = agent_id
            # 按操作系统版本对主机进行分组
            os_version = result.get("os_version", "")
            if os_version is not None:
                os_version__host_id_map[os_version].append(bk_host_id)
        # 批量更新CPU架构并且上报至CMDB
        self.update_db_and_report_cpu_arch(
            host_info_list=host_info_list, host_id__sub_inst_id_map=common_data.host_id__sub_inst_id_map
        )

        # 批量更新主机操作系统版本号
        for os_version, bk_host_ids in os_version__host_id_map.items():
            if os_version:
                models.Host.objects.filter(bk_host_id__in=bk_host_ids).update(os_version=os_version)

        # 批量更新主机 Agent ID
        if host_id__agent_id_map:
            report_agent_id_sub_insts: List[models.SubscriptionInstanceRecord] = []
            for bk_host_id, bk_agent_id in host_id__agent_id_map.items():
                sub_inst: models.SubscriptionInstanceRecord = host_id__sub_inst_map[bk_host_id]
                sub_inst.update_time = timezone.now()
                sub_inst.instance_info["host"]["bk_agent_id"] = bk_agent_id
                report_agent_id_sub_insts.append(sub_inst)

            # 更新订阅实例中的实例信息
            models.SubscriptionInstanceRecord.objects.bulk_update(
                report_agent_id_sub_insts, fields=["instance_info", "update_time"], batch_size=self.batch_size
            )

        data.outputs.scheduling_sub_inst_ids = left_scheduling_sub_inst_ids
        if not left_scheduling_sub_inst_ids:
            self.finish_schedule()
            return True

        polling_time = data.get_one_of_outputs("polling_time")
        if polling_time + POLLING_INTERVAL > self.service_polling_timeout:
            self.move_insts_to_failed(left_scheduling_sub_inst_ids, _("安装超时"))
            self.finish_schedule()
        data.outputs.polling_time = polling_time + POLLING_INTERVAL

    @controller.ConcurrentController(
        data_list_name="host_info_list",
        batch_call_func=concurrent.batch_call,
        get_config_dict_func=core.get_config_dict,
        get_config_dict_kwargs={"config_name": core.ServiceCCConfigName.HOST_WRITE.value},
    )
    @ExceptionHandler(exc_handler=core.update_cpu_arch_sub_insts_task_exc_handler)
    @RetryHandler(interval=3, retry_times=2, exception_types=[ApiResultError])
    def update_db_and_report_cpu_arch(
        self, host_info_list: List[Dict[str, Any]], host_id__sub_inst_id_map: Dict[int, int]
    ):
        """
        :param host_info_list: 包含bk_host_id与cpu_arch字段的主机信息列表
        :param host_id__sub_inst_id_map:主机ID与订阅实例ID的映射
        return:
        """
        update_list: List[Dict[str, Any]] = []
        cpu_arch__host_id_map = defaultdict(list)
        for host_info in host_info_list:
            report_cpu_arch = host_info["report_cpu_arch"]
            if report_cpu_arch not in constants.CmdbCpuArchType.cpu_type__arch_map():
                continue
            host_id = host_info["bk_host_id"]
            sub_inst_id = host_id__sub_inst_id_map[host_id]
            update_params: Dict[str, Any] = {
                "bk_host_id": host_id,
                "properties": {
                    "bk_cpu_architecture": constants.CmdbCpuArchType.cpu_type__arch_map()[report_cpu_arch],
                    "bk_os_bit": constants.OsBitType.cpu_type__os_bit_map()[report_cpu_arch],
                },
            }
            self.log_info(
                sub_inst_ids=sub_inst_id,
                log_content=_("更新 CMDB 主机信息:\n {params}").format(params=json.dumps(update_params, indent=2)),
            )
            update_list.append(update_params)
            cpu_arch__host_id_map[report_cpu_arch].append(host_id)

        for cpu_arch, bk_host_ids in cpu_arch__host_id_map.items():
            models.Host.objects.filter(bk_host_id__in=bk_host_ids).update(cpu_arch=cpu_arch)

        CCApi.batch_update_host({"update": update_list})
        return []
