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

import re
import time
from pathlib import Path
from typing import List, Tuple

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from apps.backend.exceptions import GenCommandsError
from apps.node_man import constants, models
from apps.node_man.models import aes_cipher
from apps.utils.basic import suffix_slash


class InstallationTools:
    def __init__(
        self,
        script_file_name: str,
        dest_dir: str,
        win_commands: str,
        upstream_nodes: List[str],
        jump_server: models.Host,
        pre_commands: List[str],
        run_cmd: str,
    ):
        """
        :param script_file_name: 脚本名称，如 setup_agent.sh
        :param dest_dir: 目标目录，通常为 /tmp 通过接入点配置获取
        :param win_commands: Windows执行命令
        :param upstream_nodes: 上游节点，通常为proxy或者安装通道指定的商用
        :param jump_server: 跳板服务器，通常为proxy或者安装通道的跳板机
        :param pre_commands: 预执行命令，目前仅 Windows 需要，提前推送 curl.exe 等工具
        :param run_cmd: 运行命令，通过 format_run_cmd_by_os_type 方法生成
        """
        self.script_file_name = script_file_name
        self.dest_dir = dest_dir
        self.win_commands = win_commands
        self.upstream_nodes = upstream_nodes
        self.jump_server = jump_server
        self.pre_commands = pre_commands
        self.run_cmd = run_cmd


def gen_nginx_download_url(nginx_ip: str) -> str:
    return f"http://{nginx_ip}:{settings.BK_NODEMAN_NGINX_DOWNLOAD_PORT}/"


def fetch_gse_servers(host: models.Host) -> Tuple:
    jump_server = None
    if host.install_channel_id:
        # 指定安装通道时，由安装通道生成相关配置
        jump_server, upstream_servers = host.install_channel()
        bt_file_servers = ",".join(upstream_servers["btfileserver"])
        data_servers = ",".join(upstream_servers["dataserver"])
        task_servers = ",".join(upstream_servers["taskserver"])
        package_url = gen_nginx_download_url(jump_server.inner_ip)
        default_callback_url = (
            settings.BKAPP_NODEMAN_CALLBACK_URL
            if host.node_type == constants.NodeType.AGENT
            else settings.BKAPP_NODEMAN_OUTER_CALLBACK_URL
        )
        callback_url = host.ap.outer_callback_url or default_callback_url
        return jump_server, bt_file_servers, data_servers, data_servers, task_servers, package_url, callback_url

    if host.node_type == constants.NodeType.AGENT:
        bt_file_servers = ",".join(server["inner_ip"] for server in host.ap.btfileserver)
        data_servers = ",".join(server["inner_ip"] for server in host.ap.dataserver)
        task_servers = ",".join(server["inner_ip"] for server in host.ap.taskserver)
        package_url = host.ap.package_inner_url
        callback_url = settings.BKAPP_NODEMAN_CALLBACK_URL
    elif host.node_type == constants.NodeType.PROXY:
        bt_file_servers = ",".join(server["outer_ip"] for server in host.ap.btfileserver)
        data_servers = ",".join(server["outer_ip"] for server in host.ap.dataserver)
        task_servers = ",".join(server["outer_ip"] for server in host.ap.taskserver)
        package_url = host.ap.package_outer_url
        # 不同接入点使用不同的callback_url默认情况下接入点callback_url为空，先取接入点，为空的情况下使用原来的配置
        callback_url = host.ap.outer_callback_url or settings.BKAPP_NODEMAN_OUTER_CALLBACK_URL
    else:
        # PAGENT的场景
        proxy_ips = [proxy.inner_ip for proxy in host.proxies]
        jump_server = host.get_random_alive_proxy()
        bt_file_servers = ",".join(ip for ip in proxy_ips)
        data_servers = ",".join(ip for ip in proxy_ips)
        task_servers = ",".join(ip for ip in proxy_ips)
        package_url = host.ap.package_outer_url
        # 不同接入点使用不同的callback_url默认情况下接入点callback_url为空，先取接入点，为空的情况下使用原来的配置
        callback_url = host.ap.outer_callback_url or settings.BKAPP_NODEMAN_OUTER_CALLBACK_URL

    return jump_server, bt_file_servers, data_servers, data_servers, task_servers, package_url, callback_url


def choose_script_file(host: models.Host) -> str:
    """选择脚本文件"""
    if host.node_type == constants.NodeType.PROXY:
        # proxy 安装
        return "setup_proxy.sh"

    if host.install_channel_id or (host.node_type == constants.NodeType.PAGENT and not host.is_manual):
        # 远程安装 P-AGENT 或者指定安装通道时，用 setup_pagent 脚本
        return constants.SetupScriptFileName.SETUP_PAGENT_PY.value

    # 其它场景，按操作系统来区分
    script_file_name_map = {
        constants.OsType.LINUX: constants.SetupScriptFileName.SETUP_AGENT_SH.value,
        constants.OsType.WINDOWS: constants.SetupScriptFileName.SETUP_AGENT_BAT.value,
        constants.OsType.AIX: constants.SetupScriptFileName.SETUP_AGENT_KSH.value,
    }
    script_file_name = script_file_name_map[host.os_type]
    return script_file_name


def format_run_cmd_by_os_type(os_type: str, run_cmd: str) -> str:
    if os_type == constants.OsType.WINDOWS:
        return run_cmd
    elif os_type == constants.OsType.AIX:
        return f"nohup ksh {run_cmd} &"
    else:
        return f"nohup bash {run_cmd} &"


def gen_commands(host: models.Host, pipeline_id: str, is_uninstall: bool) -> InstallationTools:
    """
    生成安装命令
    :param host: 主机信息
    :param pipeline_id: Node ID
    :param is_uninstall: 是否卸载
    :return: dest_dir 目标目录, win_commands: Windows安装命令, proxies 代理列表,
             proxy 云区域所使用的代理, pre_commands 安装前命令, run_cmd 安装命令
    """
    proxies = []
    win_commands = []
    (
        jump_server,
        bt_file_servers,
        data_servers,
        data_servers,
        task_servers,
        package_url,
        callback_url,
    ) = fetch_gse_servers(host)
    upstream_nodes = task_servers

    # 安装操作
    install_path = host.agent_config["setup_path"]
    token = aes_cipher.encrypt(f"{host.inner_ip}|{host.bk_cloud_id}|{pipeline_id}|{time.time()}")
    port_config = host.ap.port_config
    run_cmd_params = [
        f"-s {pipeline_id}",
        f"-r {callback_url}",
        f"-l {package_url}",
        f"-c {token}",
        f'-O {port_config.get("io_port")}',
        f'-E {port_config.get("file_svr_port")}',
        f'-A {port_config.get("data_port")}',
        f'-V {port_config.get("btsvr_thrift_port")}',
        f'-B {port_config.get("bt_port")}',
        f'-S {port_config.get("bt_port_start")}',
        f'-Z {port_config.get("bt_port_end")}',
        f'-K {port_config.get("tracker_port")}',
        f'-e "{bt_file_servers}"',
        f'-a "{data_servers}"',
        f'-k "{task_servers}"',
    ]

    check_run_commands(run_cmd_params)
    script_file_name = choose_script_file(host)

    dest_dir = host.agent_config["temp_path"]
    dest_dir = suffix_slash(host.os_type.lower(), dest_dir)
    if script_file_name == constants.SetupScriptFileName.SETUP_PAGENT_PY.value:
        run_cmd_params.append(f"-L {settings.DOWNLOAD_PATH}")
        # 云区域自动安装
        upstream_nodes = [proxy.inner_ip for proxy in host.proxies]
        host.upstream_nodes = proxies
        host.save(update_fields=["upstream_nodes"])

        dest_dir = jump_server.agent_config["temp_path"]
        dest_dir = suffix_slash("linux", dest_dir)
        host_tmp_path = suffix_slash(host.os_type.lower(), host.agent_config["temp_path"])
        host_identity = (
            host.identity.key if host.identity.auth_type == constants.AuthType.KEY else host.identity.password
        )
        run_cmd_params.extend(
            [
                f"-HLIP {host.login_ip or host.inner_ip}",
                f"-HIIP {host.inner_ip}",
                f"-HA {host.identity.account}",
                f"-HP {host.identity.port}",
                f"-HI '{host_identity}'",
                f"-HC {host.bk_cloud_id}",
                f"-HNT {host.node_type}",
                f"-HOT {host.os_type.lower()}",
                f"-HDD '{host_tmp_path}'",
            ]
        )

        run_cmd_params.extend(
            [
                f"-p '{install_path}'",
                f"-I {jump_server.inner_ip}",
                f"-o {gen_nginx_download_url(jump_server.inner_ip)}",
                "-R" if is_uninstall else "",
            ]
        )

        run_cmd = " ".join(run_cmd_params)

        download_cmd = (
            f"if [ ! -e {dest_dir}{script_file_name} ] || "
            f"[ `curl {package_url}/{script_file_name} -s | md5sum | awk '{{print $1}}'` "
            f"!= `md5sum {dest_dir}{script_file_name} | awk '{{print $1}}'` ]; then "
            f"curl {package_url}/{script_file_name} -o {dest_dir}{script_file_name} --connect-timeout 5 -sSf "
            f"&& chmod +x {dest_dir}{script_file_name}; fi"
        )
    else:
        run_cmd_params.extend(
            [
                f"-i {host.bk_cloud_id}",
                f"-I {host.inner_ip}",
                "-N SERVER",
                f"-p {install_path}",
                f"-T {dest_dir}",
                "-R" if is_uninstall else "",
            ]
        )

        run_cmd = format_run_cmd_by_os_type(host.os_type, f"{dest_dir}{script_file_name} {' '.join(run_cmd_params)}")
        if host.os_type == constants.OsType.WINDOWS:
            # WINDOWS 下的 Agent 安装
            win_remove_cmd = (
                f"del /q /s /f {dest_dir}{script_file_name} "
                f"{dest_dir}{constants.SetupScriptFileName.GSECTL_BAT.value}"
            )
            win_download_cmd = (
                f"{dest_dir}curl.exe {host.ap.package_inner_url}/{script_file_name}"
                f" -o {dest_dir}{script_file_name} -sSf"
                f" && "
                f"{dest_dir}curl.exe {host.ap.package_inner_url}/{constants.SetupScriptFileName.GSECTL_BAT.value}"
                f" -o {dest_dir}{constants.SetupScriptFileName.GSECTL_BAT.value} -sSf"
            )

            win_commands = [win_remove_cmd, win_download_cmd, run_cmd]
        download_cmd = f"curl {package_url}/{script_file_name} -o {dest_dir}{script_file_name} --connect-timeout 5 -sSf"
    chmod_cmd = f"chmod +x {dest_dir}{script_file_name}"
    pre_commands = [
        download_cmd,
        chmod_cmd,
    ]
    if Path(dest_dir) != Path("/tmp"):
        pre_commands.insert(0, f"mkdir -p {dest_dir}")

    return InstallationTools(
        script_file_name, dest_dir, win_commands, upstream_nodes, jump_server, pre_commands, run_cmd
    )


def check_run_commands(run_commands):
    for command in run_commands:
        if command.startswith("-r"):
            if not re.match("^-r https?://.+/backend$", command):
                raise GenCommandsError(context=_("CALLBACK_URL不符合规范, 请联系运维人员修改。 例：http://domain.com/backend"))
