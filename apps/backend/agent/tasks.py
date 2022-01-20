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
import time
import traceback

from apps.backend.celery import app
from apps.backend.utils.ssh import SshMan
from apps.backend.utils.wmi import execute_cmd
from apps.component.esbclient import client_v2
from apps.node_man import constants
from apps.node_man.models import Host
from apps.utils.basic import suffix_slash
from common.log import logger
from pipeline.log.models import LogEntry


def collect_log_exception_handler(collect_log_func):
    """日志收集处理装饰器：捕获SshMan抛出异常并记录到LogEntry
    :param collect_log_func: collect_log方法
    :return:
    """

    def exception_handler(bk_host_id, node_id=None):
        try:
            collect_log_func(bk_host_id, node_id)
        except Exception as e:
            insert_logs(
                "Collect log failed[{error}]: {exception_detail}".format(
                    error=e, exception_detail=traceback.format_exc()
                ),
                node_id,
            )

    return exception_handler


@app.task(queue="backend")
@collect_log_exception_handler
def collect_log(bk_host_id, node_id=None):
    host = Host.get_by_host_info({"bk_host_id": bk_host_id})
    dest_dir = host.agent_config["temp_path"]
    dest_dir = suffix_slash(host.os_type.lower(), dest_dir)
    ssh_man = None
    if host.node_type == constants.NodeType.PAGENT:
        proxy = host.get_random_alive_proxy()
        tmp_path = proxy.ap.agent_config["linux"]["temp_path"]
        # 登录目标机器执行命令
        if host.os_type == constants.OsType.WINDOWS:
            cmd, script_type = ("type", "bat")
            cmd_str = f"{cmd} {dest_dir}nm.setup_agent.{script_type}.{node_id}"
        else:
            cmd, script_type = ("cat", "sh")
            cmd_str = f"{cmd} {dest_dir}nm.setup_agent.{script_type}.{node_id}.debug"
        script = """#!/opt/py36/bin/python
# -*- encoding:utf-8 -*-
import sys
import argparse
sys.path.append("{tmp_path}")


def arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="p-agent setup scripts")
    parser.add_argument("-l", "--login-ip", type=str)
    parser.add_argument("-p", "--port", type=int)
    parser.add_argument("-a", "--account", type=str)
    parser.add_argument("-i", "--identity", type=str)
    parser.add_argument("-d", "--download-url", type=str)
    return parser


args = arg_parser().parse_args(sys.argv[1:])
sys.argv = sys.argv[:1]
from setup_pagent import SshMan, execute_cmd


if "{os_type}" == "WINDOWS":
    res = execute_cmd(r"{cmd_str}", args.login_ip, args.account, args.identity, args.download_url, noOutput=False)
    print(res["data"])
else:
    ssh_man = SshMan(args.login_ip, args.port, args.account, args.identity)
    ssh_man.get_and_set_prompt()
    output = ssh_man.send_cmd("{cmd_str}", wait_console_ready=False, check_output=False)
    ssh_man.safe_close(ssh_man.ssh)
    print(output)
""".format(
            tmp_path=tmp_path,
            os_type=host.os_type,
            cmd_str=cmd_str,
        )
        params = "-l {login_ip} -p {port} -a {account} -i {identity} -d {download_url}".format(
            login_ip=host.login_ip,
            port=host.identity.port,
            account=host.identity.account,
            identity=host.identity.key if host.identity.auth_type == constants.AuthType.KEY else host.identity.password,
            download_url=host.ap.package_outer_url,
        )
        kwargs = {
            "bk_biz_id": proxy.bk_biz_id,
            "script_content": base64.b64encode(script.encode()).decode(),
            "script_param": base64.b64encode(params.encode()).decode(),
            "script_timeout": 300,
            "account": "root",
            "is_param_sensitive": 1,
            "script_type": 4,
            "target_server": {"ip_list": [{"bk_cloud_id": proxy.bk_cloud_id, "ip": proxy.inner_ip}]},
        }
        data = client_v2.job.fast_execute_script(kwargs)
        job_instance_id = data["job_instance_id"]

        # 等待6s拉取日志，接取失败直接返回
        log_file_suffix = "" if host.os_type == constants.OsType.WINDOWS else ".debug"
        error_msg = f"拉取debug日志失败，如需查看最新日志请登录目标机器查看[{dest_dir}nm.setup_agent.{script_type}.{node_id}{log_file_suffix}]"
        for i in range(10):
            time.sleep(6)
            log_result = client_v2.job.get_job_instance_log(
                {"bk_biz_id": proxy.bk_biz_id, "job_instance_id": job_instance_id}
            )

            try:
                if log_result[0]["status"] == 3:
                    output = log_result[0]["step_results"][0]["ip_logs"][0]["log_content"]
                    break
                else:
                    continue
            except (IndexError, KeyError):
                output = error_msg
                break
        else:
            output = error_msg

    elif host.node_type == constants.NodeType.PROXY:
        ssh_man = SshMan(host, logger)
        # 一定要先设置一个干净的提示符号，否则会导致console_ready识别失效
        ssh_man.get_and_set_prompt()
        output = ssh_man.send_cmd(
            f"cat {dest_dir}nm.setup_proxy.sh.{node_id}.debug",
            is_clear_cmd_and_prompt=False,
            check_output=False,
        )
    else:
        if host.os_type.lower() == "linux":
            ssh_man = SshMan(host, logger)
            # 一定要先设置一个干净的提示符号，否则会导致console_ready识别失效
            ssh_man.get_and_set_prompt()
            output = ssh_man.send_cmd(
                f"cat {dest_dir}nm.setup_agent.sh.{node_id}.debug",
                is_clear_cmd_and_prompt=False,
                check_output=False,
            )
        else:
            output = execute_cmd(
                f"type {dest_dir}nm.setup_agent.bat.{node_id}",
                host.login_ip or host.inner_ip,
                host.identity.account,
                host.identity.password,
            )["data"]
    if ssh_man:
        ssh_man.safe_close(ssh_man.ssh)
    insert_logs(output, node_id)


def insert_logs(logs, node_id):
    # 覆盖原子日志
    insert_log(" Begin of collected logs: ".center(100, "*"), node_id)
    message = f"[collect] {logs}"
    insert_log(message, node_id)
    insert_log(" End of collected logs ".center(100, "*"), node_id)


def insert_log(message, node_id, level="DEBUG"):
    LogEntry.objects.create(
        logger_name="pipeline.logging",
        level_name=level,
        message=message,
        node_id=node_id,
    )
