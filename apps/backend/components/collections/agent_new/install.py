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
import base64
import json
import os
import socket
import time
from collections import defaultdict
from typing import Dict, List, Set

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from apps.backend.agent.tools import InstallationTools, batch_gen_commands
from apps.backend.api.constants import POLLING_INTERVAL, POLLING_TIMEOUT
from apps.backend.constants import REDIS_INSTALL_CALLBACK_KEY_TPL
from apps.backend.utils.redis import REDIS_INST
from apps.backend.utils.ssh import SshMan
from apps.backend.utils.wmi import execute_cmd, put_file
from apps.core.concurrent import controller
from apps.exceptions import AuthOverdueException
from apps.node_man import constants, models
from apps.utils import concurrent
from common.api import JobApi
from pipeline.core.flow import Service, StaticIntervalGenerator

from .. import core
from . import base


class InstallSubInstObj:
    def __init__(self, sub_inst_id: int, host: models.Host, installation_tool: InstallationTools):
        self.sub_inst_id = sub_inst_id
        self.host = host
        self.installation_tool = installation_tool


class InstallService(base.AgentBaseService):
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
        """处理直连windows机器，通过wmiexe连接windows机器"""
        pre_commands_params_list = []
        push_curl_exe_params_list = []
        run_install_params_list = []
        for install_sub_inst_obj in install_sub_inst_objs:
            installation_tool = install_sub_inst_obj.installation_tool
            dest_dir = installation_tool.dest_dir
            pre_commands_params_list.append(
                {
                    "sub_inst_id": install_sub_inst_obj.sub_inst_id,
                    "host": installation_tool.host,
                    "commands": [f'if not exist "{dest_dir}" mkdir {dest_dir}'],
                    "identity_data": installation_tool.identity_data,
                }
            )
            push_curl_exe_params_list.append(
                {
                    "sub_inst_id": install_sub_inst_obj.sub_inst_id,
                    "host": installation_tool.host,
                    "dest_dir": dest_dir,
                    "identity_data": installation_tool.identity_data,
                }
            )
            run_install_params_list.append(
                {
                    "sub_inst_id": install_sub_inst_obj.sub_inst_id,
                    "host": installation_tool.host,
                    "commands": installation_tool.win_commands,
                    "identity_data": installation_tool.identity_data,
                }
            )

        concurrent.batch_call(func=self.execute_windows_commands, params_list=pre_commands_params_list)
        concurrent.batch_call(func=self.push_curl_exe, params_list=push_curl_exe_params_list)
        return concurrent.batch_call(func=self.execute_windows_commands, params_list=run_install_params_list)

    @controller.ConcurrentController(
        data_list_name="install_sub_inst_objs",
        batch_call_func=concurrent.batch_call,
        get_config_dict_func=core.get_config_dict,
        get_config_dict_kwargs={"config_name": core.ServiceCCConfigName.SSH.value},
    )
    def handle_lan_linux_sub_inst(self, install_sub_inst_objs: List[InstallSubInstObj]):
        """处理直连linux机器，通过paramiko连接linux机器"""
        params_list = [
            {
                "sub_inst_id": install_sub_inst_obj.sub_inst_id,
                "installation_tool": install_sub_inst_obj.installation_tool,
            }
            for install_sub_inst_obj in install_sub_inst_objs
        ]
        return concurrent.batch_call(func=self.execute_linux_commands, params_list=params_list)

    def _execute(self, data, parent_data, common_data: base.AgentCommonData):

        host_id__sub_inst_id = {
            host_id: sub_inst_id for sub_inst_id, host_id in common_data.sub_inst_id__host_id_map.items()
        }
        is_uninstall = data.get_one_of_inputs("is_uninstall")
        host_id_obj_map = common_data.host_id_obj_map

        non_lan_sub_inst = []
        lan_windows_sub_inst = []
        lan_linux_sub_inst = []

        manual_install_sub_inst_ids: List[int] = []
        hosts_need_gen_commands: List[models] = []
        host_ids_need_gen_commands: Set[int] = set()
        for host in host_id_obj_map.values():
            if not host.is_manual:
                hosts_need_gen_commands.append(host)
                host_ids_need_gen_commands.add(host.bk_host_id)
                continue
            manual_install_sub_inst_ids.append(host_id__sub_inst_id[host.bk_host_id])
        self.log_info(sub_inst_ids=manual_install_sub_inst_ids, log_content=_("等待手动执行安装命令"))

        host_id__installation_tool_map = batch_gen_commands(
            hosts_need_gen_commands, self.id, is_uninstall, host_id__sub_inst_id=host_id__sub_inst_id
        )

        for sub_inst in common_data.subscription_instances:
            bk_host_id = sub_inst.instance_info["host"]["bk_host_id"]
            if bk_host_id not in host_ids_need_gen_commands:
                continue
            host = host_id_obj_map[bk_host_id]
            installation_tool = host_id__installation_tool_map[bk_host_id]
            install_sub_inst_obj = InstallSubInstObj(
                sub_inst_id=sub_inst.id, host=host, installation_tool=installation_tool
            )

            if installation_tool.script_file_name == constants.SetupScriptFileName.SETUP_PAGENT_PY.value:
                non_lan_sub_inst.append(install_sub_inst_obj)
            else:
                # AGENT 或 PROXY安装走 ssh或wmi 连接
                if host.os_type == constants.OsType.WINDOWS:
                    lan_windows_sub_inst.append(install_sub_inst_obj)
                else:
                    lan_linux_sub_inst.append(install_sub_inst_obj)

        succeed_non_lan_inst_ids = self.handle_non_lan_inst(install_sub_inst_objs=non_lan_sub_inst)
        succeed_lan_windows_sub_inst_ids = self.handle_lan_windows_sub_inst(install_sub_inst_objs=lan_windows_sub_inst)
        succeed_lan_linux_sub_inst_ids = self.handle_lan_linux_sub_inst(install_sub_inst_objs=lan_linux_sub_inst)
        # 使用 filter 移除并发过程中抛出异常的实例
        data.outputs.scheduling_sub_inst_ids = list(
            filter(
                None,
                (
                    succeed_non_lan_inst_ids
                    + succeed_lan_windows_sub_inst_ids
                    + succeed_lan_linux_sub_inst_ids
                    + manual_install_sub_inst_ids
                ),
            )
        )
        data.outputs.polling_time = 0

    @base.batch_call_single_exception_handler
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
        retry_times = 5
        for i, cmd in enumerate(commands, 1):
            for try_time in range(retry_times):
                try:
                    if i == len(commands):
                        # Executing scripts is the last command and takes time, using asynchronous
                        self.log_info(sub_inst_ids=sub_inst_id, log_content=f"Sending install cmd: {cmd}")
                        execute_cmd(
                            cmd,
                            ip,
                            identity_data.account,
                            identity_data.password,
                            no_output=True,
                        )
                    else:
                        # Other commands is quick and depends on previous ones, using synchronous
                        self.log_info(sub_inst_ids=sub_inst_id, log_content=f"Sending cmd: {cmd}")
                        execute_cmd(cmd, ip, identity_data.account, identity_data.password)
                except socket.error:
                    self.logger.error(
                        _(
                            "正在安装Windows AGENT, 命令执行失败，请确认: \n"
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
                        )
                    )
                except ConnectionResetError as e:
                    # 高并发下可能导致连接重置，这里添加重置机制
                    if try_time < retry_times:
                        time.sleep(1)
                        continue
                    else:
                        raise e
                else:
                    break
        return sub_inst_id

    @base.batch_call_single_exception_handler
    def push_curl_exe(self, sub_inst_id: int, host: models.Host, dest_dir: str, identity_data: models.IdentityData):
        ip = host.login_ip or host.inner_ip or host.outer_ip
        retry_times = 5
        for name in ("curl.exe", "curl-ca-bundle.crt", "libcurl-x64.dll"):
            for try_time in range(retry_times):
                try:
                    curl_file = os.path.join(settings.BK_SCRIPTS_PATH, name)
                    self.log_info(sub_inst_ids=sub_inst_id, log_content=f"pushing file {curl_file} to {dest_dir}")
                    put_file(
                        curl_file,
                        dest_dir,
                        ip,
                        identity_data.account,
                        identity_data.password,
                    )
                except ConnectionResetError as e:
                    if try_time < retry_times:
                        time.sleep(1)
                        continue
                    else:
                        raise e
                else:
                    break
        return sub_inst_id

    @base.batch_call_single_exception_handler
    def execute_job_commands(self, sub_inst_id, installation_tool: InstallationTools):
        # p-agent 走 作业平台，再 ssh 到 p-agent，这样可以无需保存 proxy 密码
        host = installation_tool.host
        jump_server = installation_tool.jump_server
        self.log_info(
            sub_inst_ids=sub_inst_id,
            log_content=_("主机的上游节点为: {proxies}").format(proxies=",".join(installation_tool.upstream_nodes)),
        )
        self.log_info(
            sub_inst_ids=sub_inst_id,
            log_content=_("已选择 {inner_ip} 作为本次安装的跳板机").format(inner_ip=jump_server.inner_ip),
        )
        path = os.path.join(settings.BK_SCRIPTS_PATH, constants.SetupScriptFileName.SETUP_PAGENT_PY.value)
        with open(path, encoding="utf-8") as fh:
            script = fh.read()

        # 使用全业务执行作业
        bk_biz_id = settings.BLUEKING_BIZ_ID
        kwargs = {
            "bk_biz_id": bk_biz_id,
            "task_name": f"NODEMAN_{sub_inst_id}_{self.__class__.__name__}",
            "target_server": {"ip_list": [{"ip": jump_server.inner_ip, "bk_cloud_id": jump_server.bk_cloud_id}]},
            "timeout": constants.JOB_TIMEOUT,
            "account_alias": settings.BACKEND_UNIX_ACCOUNT,
            "script_language": constants.ScriptLanguageType.PYTHON.value,
            "script_content": base64.b64encode(script.encode()).decode(),
            "script_param": base64.b64encode(installation_tool.run_cmd.encode()).decode(),
            "is_param_sensitive": constants.BkJobParamSensitiveType.YES.value,
        }
        data = JobApi.fast_execute_script(kwargs)
        job_instance_id = data.get("job_instance_id")
        self.log_info(
            sub_inst_ids=sub_inst_id,
            log_content=_('作业任务ID为[{job_instance_id}]，点击跳转到<a href="{link}" target="_blank">[作业平台]</a>').format(
                job_instance_id=job_instance_id,
                link=f"{settings.BK_JOB_HOST}/{settings.BLUEKING_BIZ_ID}/execute/step/{job_instance_id}",
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
                        host_inner_ip=host.inner_ip,
                        jump_server_ip=jump_server.inner_ip,
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

    @base.batch_call_single_exception_handler
    def execute_linux_commands(self, sub_inst_id, installation_tool: InstallationTools):
        host = installation_tool.host
        run_cmd = installation_tool.run_cmd
        pre_commands = installation_tool.pre_commands or []
        ssh_man = SshMan(host, self.logger, identity_data=installation_tool.identity_data)
        # 一定要先设置一个干净的提示符号，否则会导致console_ready识别失效
        ssh_man.get_and_set_prompt()
        for cmd in pre_commands:
            self.log_info(sub_inst_ids=sub_inst_id, log_content=f"Sending cmd: {cmd}")
            ssh_man.send_cmd(cmd)

        if "echo" in run_cmd:
            self.log_info(
                sub_inst_ids=sub_inst_id, log_content=f"Sending install cmd with host_data: {run_cmd.split('&&')[-1]}"
            )
        else:
            self.log_info(sub_inst_ids=sub_inst_id, log_content=f"Sending install cmd: {run_cmd}")
        # 执行脚本命令，通过report log上报日志，无需等待返回，提高执行效率
        ssh_man.send_cmd(run_cmd, wait_console_ready=False)
        ssh_man.safe_close(ssh_man.ssh)
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
        is_finished = False
        error_log = ""
        logs = []
        for data in report_data:
            # redis取出为bytes类型，进行解码
            data = json.loads(data.decode())
            tag = data.get("prefix") or "[script]"
            log = f"{tag} {data['log']}"
            status = data["status"]
            step = data["step"]
            if status == "FAILED":
                error_log = log
                is_finished = True
            else:
                logs.append(log)
            if step == "report_cpu_arch":
                cpu_arch = data["log"]
            # 只要匹配到成功返回步骤完成，则认为是执行完成了
            if step == success_callback_step and status == "DONE":
                is_finished = True
        # 并非每次调度都能取到日志，所以仅在非空情况下打印日志
        if logs:
            self.log_info(sub_inst_ids=sub_inst_id, log_content="\n".join(logs))
        if error_log:
            self.move_insts_to_failed([sub_inst_id], log_content=error_log)
        return {"sub_inst_id": sub_inst_id, "is_finished": is_finished, "cpu_arch": cpu_arch}

    def _schedule(self, data, parent_data, callback_data=None):
        """通过轮询redis的方式来处理，避免使用callback的方式频繁调用schedule"""
        common_data = self.get_common_data(data)
        success_callback_step = data.get_one_of_inputs("success_callback_step")
        scheduling_sub_inst_ids = (
            data.get_one_of_outputs("scheduling_sub_inst_ids") or common_data.subscription_instance_ids
        )
        params_list = [
            {"sub_inst_id": sub_inst_id, "success_callback_step": success_callback_step}
            for sub_inst_id in scheduling_sub_inst_ids
        ]
        results = concurrent.batch_call(func=self.handle_report_data, params_list=params_list)
        left_scheduling_sub_inst_ids = []
        cpu_arch__host_id_map = defaultdict(list)
        for result in results:
            # 对于未完成的实例，记录下来到下一次schedule中继续检查
            if not result["is_finished"]:
                left_scheduling_sub_inst_ids.append(result["sub_inst_id"])
            # 按CPU架构对主机进行分组
            bk_host_id = common_data.sub_inst_id__host_id_map.get(result["sub_inst_id"])
            cpu_arch__host_id_map[result["cpu_arch"]].append(bk_host_id)
        # 批量更新CPU架构
        for cpu_arch, bk_host_ids in cpu_arch__host_id_map.items():
            if cpu_arch:
                models.Host.objects.filter(bk_host_id__in=bk_host_ids).update(cpu_arch=cpu_arch)

        data.outputs.scheduling_sub_inst_ids = left_scheduling_sub_inst_ids
        if not left_scheduling_sub_inst_ids:
            self.finish_schedule()
            return True

        polling_time = data.get_one_of_outputs("polling_time")
        if polling_time + POLLING_INTERVAL > POLLING_TIMEOUT:
            self.move_insts_to_failed(left_scheduling_sub_inst_ids, _("安装超时"))
        data.outputs.polling_time = polling_time + POLLING_INTERVAL
