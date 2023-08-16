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
import socket
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from django.conf import settings
from django.utils import timezone, translation
from django.utils.translation import ugettext_lazy as _
from redis.client import Pipeline

from apps.backend.agent import solution_maker
from apps.backend.agent.tools import InstallationTools
from apps.backend.api.constants import POLLING_INTERVAL, POLLING_TIMEOUT
from apps.backend.constants import (
    REDIS_AGENT_CONF_KEY_TPL,
    REDIS_INSTALL_CALLBACK_KEY_TPL,
    SSH_RUN_TIMEOUT,
)
from apps.backend.subscription.steps.agent_adapter.adapter import AgentStepAdapter
from apps.backend.utils.redis import REDIS_INST
from apps.backend.utils.wmi import execute_cmd, put_file
from apps.core.concurrent import controller
from apps.core.remote import conns
from apps.exceptions import AuthOverdueException
from apps.node_man import constants, models
from apps.utils import concurrent, exc, sync
from common.api import JobApi
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

    @controller.ConcurrentController(
        data_list_name="install_sub_inst_objs",
        batch_call_func=concurrent.batch_call,
        get_config_dict_func=core.get_config_dict,
        get_config_dict_kwargs={"config_name": core.ServiceCCConfigName.JOB_CMD.value},
    )
    def handle_non_lan_inst(self, install_sub_inst_objs: List[InstallSubInstObj]) -> List[int]:
        """处理跨云机器，通过执行作业平台脚本来操作"""
        params_list = [
            {
                "sub_inst_id": install_sub_inst_obj.sub_inst_id,
                "installation_tool": install_sub_inst_obj.installation_tool,
            }
            for install_sub_inst_obj in install_sub_inst_objs
        ]
        return concurrent.batch_call(func=self.execute_job_commands, params_list=params_list)

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
            if bk_host_id not in host_ids_need_gen_commands:
                continue

            host = host_id_obj_map[bk_host_id]
            if not is_uninstall:
                # 仅在安装时需要缓存配置文件
                # 考虑手动安装也是小规模场景且依赖用户输入，暂不做缓存
                # 优先使用注入的ap, 适配只安装Agent场景
                ap_obj: models.AccessPoint = [
                    common_data.host_id__ap_map[host.bk_host_id],
                    common_data.ap_id_obj_map[common_data.injected_ap_id],
                ][common_data.injected_ap_id is not None]
                get_gse_config_tuple_params_list.append(
                    {
                        "sub_inst_id": sub_inst.id,
                        "host": host,
                        "ap": ap_obj,
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
            for cache_key in cache_key__config_content_map:
                # 根据调度超时时间预估一个过期时间
                # 由于此时还未执行「命令下发」动作，随机增量过期时长，避免缓存雪崩
                pipeline.expire(cache_key, POLLING_TIMEOUT + random.randint(POLLING_TIMEOUT, 2 * POLLING_TIMEOUT))
            pipeline.execute()

        remote_conn_helpers_gby_result_type = self.bulk_check_ssh(remote_conn_helpers=lan_windows_sub_inst)

        succeed_non_lan_inst_ids = self.handle_non_lan_inst(install_sub_inst_objs=non_lan_sub_inst)
        succeed_lan_windows_sub_inst_ids = self.handle_lan_windows_sub_inst(
            install_sub_inst_objs=remote_conn_helpers_gby_result_type.get(
                remote.SshCheckResultType.UNAVAILABLE.value, []
            )
        )
        succeed_lan_shell_sub_inst_ids = self.handle_lan_shell_sub_inst(
            install_sub_inst_objs=lan_linux_sub_inst
            + remote_conn_helpers_gby_result_type.get(remote.SshCheckResultType.AVAILABLE.value, [])
        )
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

    @exc.ExceptionHandler(exc_handler=core.default_sub_inst_task_exc_handler)
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

    @exc.ExceptionHandler(exc_handler=core.default_sub_inst_task_exc_handler)
    @base.RetryHandler(interval=0, retry_times=2, exception_types=[ConnectionResetError])
    def execute_windows_commands(
        self, sub_inst_id: int, host: models.Host, commands: List[str], identity_data: models.IdentityData
    ):
        # windows command executing
        ip = host.login_ip or host.inner_ip
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

    @exc.ExceptionHandler(exc_handler=core.default_sub_inst_task_exc_handler)
    @base.RetryHandler(interval=0, retry_times=2, exception_types=[ConnectionResetError])
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

    @exc.ExceptionHandler(exc_handler=core.default_sub_inst_task_exc_handler)
    def execute_job_commands(self, sub_inst_id, installation_tool: InstallationTools):
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

        # 使用全业务执行作业
        bk_biz_id = settings.BLUEKING_BIZ_ID
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
            "script_content": base64.b64encode(self.setup_pagent_file_content).decode(),
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

    @exc.ExceptionHandler(exc_handler=core.default_sub_inst_task_exc_handler)
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
        async with conns.AsyncsshConn(**install_sub_inst_obj.conns_init_params) as conn:

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
                        cmd = content.text
                        await log_info(sub_inst_ids=sub_inst_id, log_content=_("执行命令: {cmd}").format(cmd=cmd))
                        await conn.run(command=cmd, check=True, timeout=SSH_RUN_TIMEOUT)

        return sub_inst_id

    def handle_report_data(self, sub_inst_id: int, success_callback_step: str) -> Dict:
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
            if status == "FAILED":
                error_log = log
                is_finished = True
            else:
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

                logs.append(f"{tag} [{step}] parse healthz result: \n {json.dumps(healthz_result_dict, indent=4)}")

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

        params_list = [
            {"sub_inst_id": sub_inst_id, "success_callback_step": success_callback_step}
            for sub_inst_id in scheduling_sub_inst_ids
        ]
        host_id__sub_inst_map: Dict[int, models.SubscriptionInstanceRecord] = {
            common_data.sub_inst_id__host_id_map[sub_inst.id]: sub_inst
            for sub_inst in common_data.subscription_instances
        }
        results = concurrent.batch_call(func=self.handle_report_data, params_list=params_list)
        left_scheduling_sub_inst_ids = []
        cpu_arch__host_id_map = defaultdict(list)
        os_version__host_id_map = defaultdict(list)
        host_id__agent_id_map: Dict[int, str] = {}
        for result in results:
            # 对于未完成的实例，记录下来到下一次schedule中继续检查
            if not result["is_finished"]:
                left_scheduling_sub_inst_ids.append(result["sub_inst_id"])
            # 按 CPU 架构对主机进行分组
            bk_host_id = common_data.sub_inst_id__host_id_map.get(result["sub_inst_id"])
            cpu_arch__host_id_map[result["cpu_arch"]].append(bk_host_id)
            # 记录不为空的 agent_id 和 bk_host_id 的对应关系
            agent_id: str = result.get("agent_id") or ""
            agent_id = agent_id.split(":")[-1].strip()
            if agent_id:
                host_id__agent_id_map[bk_host_id] = agent_id
            # 按操作系统版本对主机进行分组
            os_version = result.get("os_version", "")
            if os_version is not None:
                os_version__host_id_map[os_version].append(bk_host_id)
        # 批量更新CPU架构
        for cpu_arch, bk_host_ids in cpu_arch__host_id_map.items():
            if cpu_arch:
                models.Host.objects.filter(bk_host_id__in=bk_host_ids).update(cpu_arch=cpu_arch)

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
        if polling_time + POLLING_INTERVAL > POLLING_TIMEOUT:
            self.move_insts_to_failed(left_scheduling_sub_inst_ids, _("安装超时"))
            self.finish_schedule()
        data.outputs.polling_time = polling_time + POLLING_INTERVAL
