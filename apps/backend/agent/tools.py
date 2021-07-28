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

import ujson as json
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from apps.backend.exceptions import GenCommandsError
from apps.node_man import constants
from apps.node_man.models import aes_cipher
from apps.utils.basic import suffix_slash


def gen_commands(host, pipeline_id, is_uninstall, batch_install=False):
    """
    生成安装命令
    :param host: 主机信息
    :param pipeline_id: Node ID
    :param is_uninstall: 是否卸载
    :param batch_install: 是否为手动安装的批量安装
    :return: dest_dir 目标目录, win_commands: Windows安装命令, proxies 代理列表,
             proxy 云区域所使用的代理, pre_commands 安装前命令, run_cmd 安装命令
    """

    proxy = ""
    proxies = []
    pre_commands = []
    win_commands = []

    if host.node_type == constants.NodeType.AGENT:
        bt_file_servers = ",".join(server["inner_ip"] for server in host.ap.btfileserver)
        data_servers = ",".join(server["inner_ip"] for server in host.ap.dataserver)
        task_servers = ",".join(server["inner_ip"] for server in host.ap.taskserver)
        package_url = host.ap.package_inner_url
        callback_url = settings.BKAPP_NODEMAN_CALLBACK_URL
    else:
        bt_file_servers = ",".join(server["outer_ip"] for server in host.ap.btfileserver)
        data_servers = ",".join(server["outer_ip"] for server in host.ap.dataserver)
        task_servers = ",".join(server["outer_ip"] for server in host.ap.taskserver)
        package_url = host.ap.package_outer_url
        # 不同接入点使用不同的callback_url默认情况下接入点callback_url为空，先取接入点，为空的情况下使用原来的配置
        callback_url = host.ap.outer_callback_url or settings.BKAPP_NODEMAN_OUTER_CALLBACK_URL

    # 安装操作
    if host.node_type == constants.NodeType.PROXY and not host.os_type:
        host.os_type = constants.OsType.LINUX
        host.save()
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
    ]

    check_run_commands(run_cmd_params)

    shell_file_name_map = {
        "AGENT": "setup_agent.sh",
        "PROXY": "setup_proxy.sh",
        "PAGENT": "setup_pagent.py",
    }

    if not batch_install:
        shell_file_name = shell_file_name_map[host.node_type]
    else:
        shell_file_name = shell_file_name_map["PAGENT"]

    dest_dir = host.agent_config["temp_path"]
    dest_dir = suffix_slash(host.os_type.lower(), dest_dir)
    if host.node_type in [constants.NodeType.AGENT, constants.NodeType.PROXY] and not batch_install:
        # 直连区域
        run_cmd_params.extend([f"-i {host.bk_cloud_id}", f"-I {host.inner_ip}", "-N SERVER", f"-p {install_path}"])

        run_cmd_params.append(f"-T {dest_dir}")
        run_cmd_params.append(f'-e "{bt_file_servers}"')
        run_cmd_params.append(f'-a "{data_servers}"')
        run_cmd_params.append(f'-k "{task_servers}"')

        if host.os_type == constants.OsType.AIX:
            shell_file_name = "setup_agent.ksh"

        if host.os_type == constants.OsType.WINDOWS:
            # WINDOWS 下的 Agent 安装
            shell_file_name = "setup_agent.bat"
            gsectl_file_name = "gsectl.bat"
            remove_cmd = f"del /q /s /f {dest_dir}{shell_file_name} {dest_dir}{gsectl_file_name}"
            download_cmd = (
                f"{dest_dir}curl.exe {host.ap.package_inner_url}/{shell_file_name}"
                f" -o {dest_dir}{shell_file_name} -sSf"
            )
            download_gsectl_cmd = (
                f"{dest_dir}curl.exe {host.ap.package_inner_url}/{gsectl_file_name}"
                f" -o {dest_dir}{gsectl_file_name} -sSf"
            )
            if is_uninstall:
                # 卸载操作
                run_cmd_params.append("-R")
            run_cmd = f"{dest_dir}{shell_file_name} {' '.join(run_cmd_params)}"
            win_commands = [remove_cmd, download_cmd, download_gsectl_cmd, run_cmd]
            return dest_dir, win_commands, proxies, proxy, pre_commands, run_cmd
        else:
            # 其他系统的 Agent 安装
            if is_uninstall:
                # 卸载操作
                run_cmd_params.append("-R")
            run_cmd = f"nohup bash {dest_dir}{shell_file_name} {' '.join(run_cmd_params)} &"

        download_cmd = f"curl {package_url}/{shell_file_name} -o {dest_dir}{shell_file_name} --connect-timeout 5 -sSf"

    else:
        run_cmd_params.append(f"-L {settings.NGINX_DOWNLOAD_PATH}")
        # 云区域自动安装
        dest_host = host
        # 手动批量安装均走该分支
        if not batch_install:
            # 非手动批量安装
            proxies = [proxy.inner_ip for proxy in host.proxies]
            host.upstream_nodes = proxies
            host.save(update_fields=["upstream_nodes"])

            proxy = host.get_random_alive_proxy()
            dest_host = proxy

        pa_conf_file = f"{pipeline_id}_pa.json"
        host_data = [
            (
                host.login_ip or host.inner_ip,
                host.inner_ip,
                host.identity.account,
                str(host.identity.port),
                host.identity.key if host.identity.auth_type == constants.AuthType.KEY else host.identity.password,
                str(host.bk_cloud_id),
                host.node_type,
                host.os_type.lower(),
                dest_dir,
            )
        ]

        dest_dir = dest_host.agent_config["temp_path"]
        dest_dir = suffix_slash("linux", dest_dir)

        install_path = "".join([char if char != "\\" else "\\\\" for char in install_path])
        run_cmd_params.extend([f"-j {dest_dir}{pa_conf_file}", f"-p {install_path}"])
        if not batch_install:
            # 非手动批量安装
            proxy_ips = ",".join(proxies)
            run_cmd_params.extend(
                [
                    f"-e {proxy_ips}",
                    f"-a {proxy_ips}",
                    f"-k {proxy_ips}",
                    f"-I {proxy.inner_ip}",
                    f"-o http://{proxy.inner_ip}:17980/",
                ]
            )
        else:
            run_cmd_params.extend(
                [
                    f"-e {bt_file_servers}",
                    f"-a {data_servers}",
                    f"-k {task_servers}",
                    f"-i {host.bk_cloud_id}",
                    f"-I {host.inner_ip}",
                    "-N SERVER",
                ]
            )
        if is_uninstall:
            # 卸载操作
            run_cmd_params.append("-R")
        run_cmd = (
            f"echo '{json.dumps(host_data)}' > {dest_dir}{pa_conf_file} && "
            f"nohup {dest_dir}{shell_file_name} {' '.join(run_cmd_params)} "
            f">{dest_dir}nm.setup_pagent.py.{pipeline_id} 2>&1"
        )

        download_cmd = (
            f"if [ ! -e {dest_dir}{shell_file_name} ] || "
            f"[ `curl {package_url}/{shell_file_name} -s | md5sum | awk '{{print $1}}'` "
            f"!= `md5sum {dest_dir}{shell_file_name} | awk '{{print $1}}'` ]; then "
            f"curl {package_url}/{shell_file_name} -o {dest_dir}{shell_file_name} --connect-timeout 5 -sSf "
            f"&& chmod +x {dest_dir}{shell_file_name}; fi"
        )

    chmod_cmd = f"chmod +x {dest_dir}{shell_file_name}"

    pre_commands = [
        download_cmd,
        chmod_cmd,
    ]

    if Path(dest_dir) != Path("/tmp"):
        pre_commands.insert(0, f"mkdir -p {dest_dir}")

    return dest_dir, win_commands, proxies, proxy, pre_commands, run_cmd


def check_run_commands(run_commands):
    for command in run_commands:
        if command.startswith("-r"):
            if not re.match("^-r https?://.+/backend$", command):
                raise GenCommandsError(context=_("CALLBACK_URL不符合规范, 请联系运维人员修改。 例：http://domain.com/backend"))
