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
import os
import time
import traceback
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml
from django.conf import settings
from django.db import DatabaseError, IntegrityError, transaction
from django.utils.translation import ugettext_lazy as _

from apps.backend import exceptions
from apps.backend.api import constants as const
from apps.backend.utils.package.tools import pre_check
from apps.core.files.storage import get_storage
from apps.node_man import constants, models
from apps.node_man.models import aes_cipher
from apps.utils import files
from apps.utils.basic import suffix_slash
from apps.utils.encrypt import rsa

logger = logging.getLogger("app")


class InstallationTools:
    def __init__(
        self,
        script_file_name: str,
        dest_dir: str,
        win_commands: List[str],
        upstream_nodes: str,
        jump_server: models.Host,
        pre_commands: List[str],
        run_cmd: str,
        host: models.Host,
        ap: models.AccessPoint,
        identity_data: models.IdentityData,
        proxies: List[models.Host],
        package_url: str,
    ):
        """
        :param script_file_name: 脚本名称，如 setup_agent.sh
        :param dest_dir: 目标目录，通常为 /tmp 通过接入点配置获取
        :param win_commands: Windows执行命令
        :param upstream_nodes: 上游节点，通常为proxy或者安装通道指定的商用
        :param jump_server: 跳板服务器，通常为proxy或者安装通道的跳板机
        :param pre_commands: 预执行命令，目前仅 Windows 需要，提前推送 curl.exe 等工具
        :param run_cmd: shell 运行命令，通过 format_run_cmd_by_os_type 方法生成
        :param host: 主机对象
        :param ap: 接入点对象
        :param identity_data: 认证数据对象
        :param proxies: 代理列表
        :param package_url 文件下载链接
        """
        self.script_file_name = script_file_name
        self.dest_dir = dest_dir
        self.win_commands = win_commands
        self.upstream_nodes = upstream_nodes
        self.jump_server = jump_server
        self.pre_commands = pre_commands
        self.run_cmd = run_cmd
        self.host = host
        self.ap = ap
        self.identity_data = identity_data
        self.proxies = proxies
        self.package_url = package_url


def gen_nginx_download_url(nginx_ip: str) -> str:
    return f"http://{nginx_ip}:{settings.BK_NODEMAN_NGINX_DOWNLOAD_PORT}/"


def fetch_gse_servers(
    host: models.Host,
    host_ap: models.AccessPoint,
    proxies: List[models.Host],
    install_channel: Tuple[models.Host, Dict[str, List]],
) -> Tuple:
    jump_server = None
    if host.install_channel_id:
        # 指定安装通道时，由安装通道生成相关配置
        jump_server, upstream_servers = install_channel
        bt_file_servers = ",".join(upstream_servers["btfileserver"])
        data_servers = ",".join(upstream_servers["dataserver"])
        task_servers = ",".join(upstream_servers["taskserver"])
        package_url = gen_nginx_download_url(jump_server.inner_ip)
        default_callback_url = (
            settings.BKAPP_NODEMAN_CALLBACK_URL
            if host.node_type == constants.NodeType.AGENT
            else settings.BKAPP_NODEMAN_OUTER_CALLBACK_URL
        )
        callback_url = host_ap.outer_callback_url or default_callback_url
        return jump_server, bt_file_servers, data_servers, data_servers, task_servers, package_url, callback_url

    if host.node_type == constants.NodeType.AGENT:
        bt_file_servers = ",".join(server["inner_ip"] for server in host_ap.btfileserver)
        data_servers = ",".join(server["inner_ip"] for server in host_ap.dataserver)
        task_servers = ",".join(server["inner_ip"] for server in host_ap.taskserver)
        package_url = host_ap.package_inner_url
        # 优先使用接入点配置的内网回调地址
        callback_url = host_ap.callback_url or settings.BKAPP_NODEMAN_CALLBACK_URL
    elif host.node_type == constants.NodeType.PROXY:
        bt_file_servers = ",".join(server["outer_ip"] for server in host_ap.btfileserver)
        data_servers = ",".join(server["outer_ip"] for server in host_ap.dataserver)
        task_servers = ",".join(server["outer_ip"] for server in host_ap.taskserver)
        package_url = host_ap.package_outer_url
        # 不同接入点使用不同的callback_url默认情况下接入点callback_url为空，先取接入点，为空的情况下使用原来的配置
        callback_url = host_ap.outer_callback_url or settings.BKAPP_NODEMAN_OUTER_CALLBACK_URL
    else:
        # PAGENT的场景
        proxy_ips = list(set([proxy.inner_ip for proxy in proxies]))
        jump_server = host.get_random_alive_proxy(proxies)
        bt_file_servers = ",".join(ip for ip in proxy_ips)
        data_servers = ",".join(ip for ip in proxy_ips)
        task_servers = ",".join(ip for ip in proxy_ips)
        package_url = host_ap.package_outer_url
        # 不同接入点使用不同的callback_url默认情况下接入点callback_url为空，先取接入点，为空的情况下使用原来的配置
        callback_url = host_ap.outer_callback_url or settings.BKAPP_NODEMAN_OUTER_CALLBACK_URL

    return jump_server, bt_file_servers, data_servers, data_servers, task_servers, package_url, callback_url


def choose_script_file(host: models.Host) -> str:
    """选择脚本文件"""
    if host.node_type == constants.NodeType.PROXY:
        # proxy 安装
        return "setup_proxy.sh"

    if host.install_channel_id or host.node_type == constants.NodeType.PAGENT:
        # 远程安装 P-AGENT 或者指定安装通道时，用 setup_pagent 脚本
        return constants.SetupScriptFileName.SETUP_PAGENT_PY.value

    # 其它场景，按操作系统来区分
    script_file_name = constants.SCRIPT_FILE_NAME_MAP[host.os_type]
    return script_file_name


def format_run_cmd_by_os_type(os_type: str, dest_dir: str, run_cmd=None) -> str:
    os_type = os_type.lower()
    if os_type == const.OS.WINDOWS and run_cmd:
        return run_cmd
    suffix = const.SUFFIX_MAP[os_type]
    if suffix != const.SUFFIX_MAP[const.OS.AIX]:
        shell = "bash"
    else:
        shell = suffix
    run_cmd = f"nohup {shell} {run_cmd} &> {dest_dir}nm.nohup.out &" if run_cmd else shell
    return run_cmd


def lan_node_shell_cmds_generator(
    os_type: str,
    dest_dir: str,
    script_file_name: str,
    package_url: str,
    run_cmd_params: List[str],
    options_path: List[str],
    options_value_inside_quotes: List[str],
):
    """
    直连区域 shell 命令生产器
    :param os_type: 操作系统类型
    :param dest_dir: 工作目录
    :param script_file_name: 安装脚本名称
    :param package_url: 安装包下载地址
    :param run_cmd_params: 执行参数
    :param options_path: 待转义的路径参数项，适配 Cygwin
    :param options_value_inside_quotes: 值包含 , 或 ; 的参数项
    :return:
    """
    curl_cmd = "curl"
    if os_type == constants.OsType.WINDOWS:
        dest_dir = dest_dir.replace("\\", "/")
        curl_cmd = f"{dest_dir}curl.exe"
        run_cmd_params_treated = []
        for run_cmd_param in run_cmd_params:
            if not run_cmd_param:
                continue
            try:
                option, value = run_cmd_param.split(" ", 1)
            except ValueError:
                # 适配无值参数
                run_cmd_params_treated.append(run_cmd_param)
                continue
            if option in options_path:
                value = value.replace("\\", "\\\\")
            elif option in options_value_inside_quotes:
                # Invalid option 处理 cygwin 执行 .bat 报错：Invalid option
                # Including space anywhere inside quotes will ensure that
                # parameter with semicolon or comma is passed correctly.
                # 参考：https://stackoverflow.com/questions/17747961/
                value = f'{value[:-1]} "'
            run_cmd_params_treated.append(f"{option} {value}")
    else:
        run_cmd_params_treated = list(filter(None, run_cmd_params))

    chmod_cmd = f"chmod +x {dest_dir}{script_file_name}"
    download_cmd = (
        f"{curl_cmd} {package_url}/{script_file_name} " f"-o {dest_dir}{script_file_name} --connect-timeout 5 -sSf"
    )
    run_cmd = format_run_cmd_by_os_type(
        os_type, dest_dir, f"{dest_dir}{script_file_name} {' '.join(run_cmd_params_treated)}"
    )

    if os_type == constants.OsType.WINDOWS:
        run_cmd = f"nohup {run_cmd} &> {dest_dir}nm.nohup.out &"

    return {"chmod_cmd": chmod_cmd, "download_cmd": download_cmd, "run_cmd": run_cmd}


def gen_commands(
    host: models.Host,
    pipeline_id: str,
    is_uninstall: bool,
    sub_inst_id: int,
    version: str = None,
    identity_data: Optional[models.IdentityData] = None,
    host_ap: Optional[models.AccessPoint] = None,
    proxies: Optional[List[models.Host]] = None,
    install_channel: Optional[Tuple[models.Host, Dict[str, List]]] = None,
) -> InstallationTools:
    """
    生成安装命令
    :param host: 主机信息
    :param pipeline_id: Node ID
    :param is_uninstall: 是否卸载
    :param version: 版本号
    :param sub_inst_id: 订阅实例 ID
    :param identity_data: 主机认证数据对象
    :param host_ap: 主机接入点对象
    :param proxies: 主机代理列表
    :param install_channel: 安装通道
    :return: dest_dir 目标目录, win_commands: Windows安装命令, proxies 代理列表,
             proxy 云区域所使用的代理, pre_commands 安装前命令, run_cmd 安装命令
    """
    # 批量场景请传入Optional所需对象，以避免 n+1 查询，提高执行效率
    host_ap = host_ap or host.ap
    identity_data = identity_data or host.identity
    install_channel = install_channel or host.install_channel
    proxies = proxies if proxies is not None else host.proxies
    encrypted_password = ""
    (
        jump_server,
        bt_file_servers,
        data_servers,
        data_servers,
        task_servers,
        package_url,
        callback_url,
    ) = fetch_gse_servers(host, host_ap, proxies, install_channel)
    upstream_nodes = task_servers

    # 匹配版本
    from apps.node_man.models import GseAgentDesc

    is_proxy_package = True if host.node_type == constants.NodeType.PROXY else False
    version = GseAgentDesc.fetch_client_release_version(version=version, is_proxy_package=is_proxy_package)

    agent_config = host_ap.get_agent_config(host.os_type)
    # 安装操作
    install_path = agent_config["setup_path"]
    token = aes_cipher.encrypt(f"{host.inner_ip}|{host.bk_cloud_id}|{pipeline_id}|{time.time()}|{sub_inst_id}")
    port_config = host_ap.port_config
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
        f"-G {version}",
    ]

    # 系统开启使用密码注册windows服务时，需额外传入用户名和加密密码参数，用于注册windows服务，详见setup_agent.bat脚本
    need_encrypted_password = all(
        [
            settings.REGISTER_WIN_SERVICE_WITH_PASS,
            host.os_type == constants.OsType.WINDOWS,
            # 背景：过期密码会重置为 None，导致加密失败
            # 仅在密码非空的情况下加密，防止密码过期 / 手动安装的情况下报错
            identity_data.password is not None,
        ]
    )
    if need_encrypted_password:
        # 系统开启使用密码注册windows服务时，需额外传入 -U -P参数，用于注册windows服务，详见setup_agent.bat脚本
        encrypted_password = rsa.RSAUtil(
            public_extern_key_file=os.path.join(settings.BK_SCRIPTS_PATH, "gse_public_key"),
            padding=rsa.CipherPadding.PKCS1_OAEP.value,
        ).encrypt(identity_data.password)

    check_run_commands(run_cmd_params)
    script_file_name = choose_script_file(host)

    # run_cmd: shell 运行命令，Windows 会生成兼容 cygwin 的运行命令
    # run_cmd_os_based: 根据操作系统类型所生成运行命令 Windows - bat | 其他 - shell
    run_cmd = ""
    host_tmp_path = suffix_slash(host.os_type.lower(), agent_config["temp_path"])
    dest_dir = host_tmp_path
    chmod_cmd = f"chmod +x {dest_dir}{script_file_name}"
    if script_file_name == constants.SetupScriptFileName.SETUP_PAGENT_PY.value:
        run_cmd_params.append(f"-L {settings.DOWNLOAD_PATH}")
        # P-Agent在proxy上执行，proxy都是Linux机器
        dest_dir = host_ap.get_agent_config(constants.OsType.LINUX)["temp_path"]
        dest_dir = suffix_slash(constants.OsType.LINUX, dest_dir)
        if host.is_manual:
            run_cmd_params.insert(0, f"{dest_dir}{script_file_name} ")
        host_identity = (
            identity_data.key if identity_data.auth_type == constants.AuthType.KEY else identity_data.password
        )
        host_shell = format_run_cmd_by_os_type(host.os_type, host_tmp_path)
        run_cmd_params.extend(
            [
                f"-HLIP {host.login_ip or host.inner_ip}",
                f"-HIIP {host.inner_ip}",
                f"-HA {identity_data.account}",
                f"-HP {identity_data.port}",
                f"-HI '{host_identity}'",
                f"-HC {host.bk_cloud_id}",
                f"-HNT {host.node_type}",
                f"-HOT {host.os_type.lower()}",
                f"-HDD '{host_tmp_path}'",
                f"-HPP '{settings.BK_NODEMAN_NGINX_PROXY_PASS_PORT}'",
                f"-HSN '{constants.SCRIPT_FILE_NAME_MAP[host.os_type]}'",
                f"-HS '{host_shell}'",
                f"-p '{install_path}'",
                f"-I {jump_server.inner_ip}",
                f"-o {gen_nginx_download_url(jump_server.inner_ip)}",
                f"-HEP '{encrypted_password}'" if need_encrypted_password else "",
                "-R" if is_uninstall else "",
            ]
        )

        # 通道特殊配置
        if host.install_channel_id:
            __, upstream_servers = install_channel
            agent_download_proxy = upstream_servers.get("agent_download_proxy", True)
            if not agent_download_proxy:
                # 关闭agent下载代理选项时传入
                run_cmd_params.extend([f"-ADP '{agent_download_proxy}'"])
            channel_proxy_address = upstream_servers.get("channel_proxy_address", None)
            if channel_proxy_address:
                run_cmd_params.extend([f"-CPA '{channel_proxy_address}'"])

        run_cmd_os_based = " ".join(list(filter(None, run_cmd_params)))

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
        if need_encrypted_password:
            run_cmd_params.extend(
                [
                    f"-U {identity_data.account}",
                    f'-P "{encrypted_password}"',
                ]
            )

        name__cmd_map = lan_node_shell_cmds_generator(
            os_type=host.os_type,
            dest_dir=dest_dir,
            script_file_name=script_file_name,
            package_url=package_url,
            run_cmd_params=run_cmd_params,
            options_path=["-T", "-p"],
            options_value_inside_quotes=["-e", "-a", "-k", "-P"],
        )
        chmod_cmd = name__cmd_map["chmod_cmd"]
        download_cmd = name__cmd_map["download_cmd"]
        run_cmd = name__cmd_map["run_cmd"]

        run_cmd_os_based = format_run_cmd_by_os_type(
            host.os_type, host_tmp_path, f"{dest_dir}{script_file_name} {' '.join(list(filter(None, run_cmd_params)))}"
        )

    pre_commands = [
        download_cmd,
        chmod_cmd,
    ]
    if Path(dest_dir) != Path("/tmp") and host.os_type != constants.OsType.WINDOWS:
        pre_commands.insert(0, f"mkdir -p {dest_dir}")

    install_tools = InstallationTools(
        script_file_name,
        dest_dir,
        [
            f"{dest_dir}curl.exe {package_url}/{script_file_name} -o {dest_dir}{script_file_name} -sSf",
            # 如果是 Windows 机器，run_cmd_os_based 为 bat 命令
            run_cmd_os_based,
        ],
        upstream_nodes,
        jump_server,
        pre_commands,
        # 背景：直连 Windows 支持 Cygwin
        # 对于直连机器，会优先取 run_cmd（shell），非直连 run_cmd 为空，取 run_cmd_os_based
        run_cmd or run_cmd_os_based,
        host,
        host_ap,
        identity_data,
        proxies,
        package_url,
    )

    # 非 Windows 机器使用 sudo 权限执行命令
    # PAgent 依赖 setup_pagent.py 添加 sudo
    # Windows Cygwin sudo command not found：Cygwin 本身通过 administrator 启动，无需 sudo
    if not (
        host.os_type == constants.OsType.WINDOWS
        or install_tools.identity_data.account in [constants.LINUX_ACCOUNT]
        or script_file_name == constants.SetupScriptFileName.SETUP_PAGENT_PY.value
    ):
        install_tools.run_cmd = f"sudo {install_tools.run_cmd}"
        install_tools.pre_commands = [f"sudo {pre_command}" for pre_command in install_tools.pre_commands]

    return install_tools


def check_run_commands(run_commands):
    return
    # 不对回调地址做格式化检验
    # 背景：ip:port 等转发模式也可以作为回调地址配置的方式
    # 考虑该方法位于单主机命令生成的逻辑下，将可达性验证放在接入点保存前校验逻辑，减少批量执行下对单个url执行重复校验
    # for command in run_commands:
    #     if command.startswith("-r"):
    #         if not re.match("^-r https?://.+/backend$", command):
    #             raise GenCommandsError(context=_("CALLBACK_URL不符合规范, 请联系运维人员修改。 例：http://domain.com/backend"))


def batch_gen_commands(
    hosts: List[models.Host],
    pipeline_id: str,
    is_uninstall: bool,
    host_id__sub_inst_id: Dict[int, int],
    ap_id_obj_map: Dict[int, models.AccessPoint],
    cloud_id__proxies_map: Dict[int, List[models.Host]],
    host_id__install_channel_map: Dict[int, Tuple[Optional[models.Host], Dict[str, List]]],
) -> Dict[int, InstallationTools]:
    """批量生成安装命令"""
    # 批量查出主机的属性并设置为property，避免在循环中进行ORM查询，提高效率
    host_id__sub_inst_id = host_id__sub_inst_id or host_id__sub_inst_id
    host_id__installation_tool_map = {}
    bk_host_ids = [host.bk_host_id for host in hosts]
    host_id_identity_map = {
        identity.bk_host_id: identity for identity in models.IdentityData.objects.filter(bk_host_id__in=bk_host_ids)
    }

    for host in hosts:
        host_ap = ap_id_obj_map[host.ap_id]
        # 避免部分主机认证信息丢失的情况下，通过host.identity重新创建来兜底保证不会异常
        identity_data = host_id_identity_map.get(host.bk_host_id) or host.identity

        host_id__installation_tool_map[host.bk_host_id] = gen_commands(
            host=host,
            pipeline_id=pipeline_id,
            is_uninstall=is_uninstall,
            sub_inst_id=host_id__sub_inst_id[host.bk_host_id],
            identity_data=identity_data,
            host_ap=host_ap,
            proxies=cloud_id__proxies_map.get(host.bk_cloud_id),
            install_channel=host_id__install_channel_map.get(host.bk_host_id),
        )

    return host_id__installation_tool_map


def yaml_file_parse(file_path: str):

    try:
        with open(file_path, "r", encoding="utf-8") as project_file:
            yaml_config = yaml.safe_load(project_file)
            if not isinstance(yaml_config, dict):
                raise yaml.YAMLError
            return yaml_config
    except (IOError, yaml.YAMLError):
        raise exceptions.PluginParseError(
            "failed to parse or read project_yaml -> {project_yaml_file_path}, for -> {err_msg}".format(
                project_yaml_file_path=file_path, err_msg=traceback.format_exc()
            )
        )


def parse_client_package(file_path: str) -> Dict[str, Union[bool, Union[str, Dict[str, List[str]]]]]:
    """
    解析file_path下gse client 完整安装包，获取包信息字典列表
    :param file_path: agent包所在路径
    :return:
        {
            "result": True,
            "version": "1.7.17",
            "agent": { "windows_x86": [ "gse_agent", "gsectl"] },
            "proxy": { "linux_x86_64": [ "gse_btsvr", "gse_data"] }",
            "config_templates": {
                "agent": [ {"linux_x86": [ "agent.conf", "iagent.conf"]} ] ,
                "proxy": [ {"linux_x86_64": [ "btsvr.conf", "data.conf"]} ]
            }
        },
        ...
    """
    storage = get_storage()
    if not storage.exists(name=file_path):
        raise exceptions.AgentParseError(_(f"Agent包不存在: file_path -> {file_path}"))
    # 解压压缩文件
    tmp_dir = files.mk_and_return_tmpdir()
    pre_check(tmp_dir=tmp_dir, file_path=file_path, action_type=constants.ProcType.AGENT)

    package_infos: Dict[Optional[str, Dict[str, Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    # 遍历第一层的内容，获取agent和proxy信息
    sub_abs_path = os.path.join(tmp_dir, constants.AgentPackageMap.GSE)
    if not os.path.isdir(sub_abs_path):
        raise exceptions.AgentParseError(_(f"Agent包不符合路径规则，缺失 -> {constants.AgentPackageMap.GSE} 层级"))

    for platform_dir_name in os.listdir(sub_abs_path):
        if constants.AgentPackageMap.AGENT_DIR_SUB_RE.match(platform_dir_name):
            agent_info_map = list_agent__dir_info(
                path_name=platform_dir_name, parent_path=sub_abs_path, pkg_path=file_path
            )
            package_infos[constants.NodeType.AGENT.lower()][agent_info_map["platform"]] = agent_info_map["file_list"]
        elif constants.AgentPackageMap.PROXY_DIR_SUB_RE.match(platform_dir_name):
            proxy_info_map = list_proxy__dir_info(
                path_name=platform_dir_name, parent_path=sub_abs_path, pkg_path=file_path
            )
            package_infos[constants.NodeType.PROXY.lower()][proxy_info_map["platform"]] = proxy_info_map["file_list"]
        elif constants.AgentPackageMap.SUPPORT_DIR_SUB_RE.match(platform_dir_name):
            template_info_map = list_config_template__info(
                path_name=platform_dir_name, parent_path=sub_abs_path, pkg_path=file_path
            )
            package_infos[constants.AgentPackageMap.CONFIG_TEMPLATE][constants.NodeType.AGENT.lower()].append(
                template_info_map[constants.NodeType.AGENT.lower()]
            )
            package_infos[constants.AgentPackageMap.CONFIG_TEMPLATE][constants.NodeType.PROXY.lower()].append(
                template_info_map[constants.NodeType.PROXY.lower()]
            )
    package_infos["package_tmp_path"] = tmp_dir

    project_yaml_file_path = os.path.join(sub_abs_path, constants.AgentPackageMap.PROJECTS_YAML)
    if not os.path.exists(project_yaml_file_path):
        logger.warning(
            "try to pack path-> {pkg_absolute_path} but not [project.yaml] file under file path".format(
                pkg_absolute_path=sub_abs_path
            )
        )
        package_infos["result"] = False
        package_infos["message"] = _(f"缺少 {constants.AgentPackageMap.PROJECTS_YAML}文件")
        return package_infos

    yaml_config = yaml_file_parse(file_path=project_yaml_file_path)

    try:
        yaml_config["version"] = str(yaml_config["version"])
        package_medium = yaml_config.get("medium", constants.AgentPackageMap.AGENT_DEFAULT_MEDIUM["name"])
        package_desc = yaml_config.get("desc", constants.AgentPackageMap.AGENT_DEFAULT_MEDIUM["desc"])

        package_infos.update(
            {
                "version": yaml_config["version"],
                "medium": package_medium,
                "desc": package_desc,
            }
        )
    except (KeyError, TypeError):
        logger.warning(
            "failed to get key info from project.yaml -> {project_yaml_file_path}, for -> {err_msg}".format(
                project_yaml_file_path=project_yaml_file_path, err_msg=traceback.format_exc()
            )
        )
        package_infos["result"] = False
        package_infos["message"] = _(f" {constants.AgentPackageMap.PROJECTS_YAML} 文件信息缺失")
        return package_infos

    package_infos["result"] = True
    return package_infos


def list_agent__dir_info(path_name: str, parent_path: str, pkg_path: str) -> Dict[str, Any]:
    file_list: List[str] = []

    # 将文件名解析为插件信息字典
    re_match = constants.AgentPackageMap.AGENT_DIR_SUB_RE.match(path_name)
    client_info_dict = re_match.groupdict()
    node_type = constants.NodeType.AGENT.lower()
    os_type = client_info_dict["os_type"]
    cpu_arch = client_info_dict["cpu_arch"]
    logger.info(f"pkg_name -> {pkg_path} is match for node type -> {node_type} os -> {os_type}, cpu -> {cpu_arch}")

    platform_bin_path = os.path.join(parent_path, path_name, constants.AgentPackageMap.BIN)
    # 遍历第二层的内容, 获取文件列表
    for executable_file in os.listdir(platform_bin_path):
        if not executable_file_check(file_name=executable_file, parent_path=platform_bin_path, pkg_name=pkg_path):
            continue
        file_list.append(executable_file)

    return {"platform": f"{os_type}_{cpu_arch}", "file_list": file_list}


def list_proxy__dir_info(path_name: str, parent_path: str, pkg_path: str) -> Dict[str, List[str]]:
    file_list: List[str] = []
    bin_abs_path = os.path.join(parent_path, path_name, constants.AgentPackageMap.BIN)
    for executable_file in os.listdir(bin_abs_path):
        if not executable_file_check(file_name=executable_file, parent_path=bin_abs_path, pkg_name=pkg_path):
            continue
        file_list.append(executable_file)
    return {"platform": f"{constants.OsType.LINUX.lower()}_{constants.CpuType.x86_64.lower()}", "file_list": file_list}


def executable_file_check(file_name: str, parent_path: str, pkg_name: str) -> bool:
    file_path = os.path.join(parent_path, file_name)
    if not os.path.isfile(file_path):
        logger.error(_(f"pkg_name -> {pkg_name} sub path -> {parent_path} include non-file structure  -> {file_name}"))
        return False
    return True


def list_config_template__info(path_name: str, parent_path: str, pkg_path: str) -> Dict[str, Dict[str, List[str]]]:
    config_file_map: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
    template_abs_path = os.path.join(parent_path, path_name, constants.AgentPackageMap.TEMPLATE)

    def get_agent_template_map(file_name: str) -> Dict[str, Any]:
        re_match = constants.AgentPackageMap.AGENT_CONFIG_TEMPLATE_RE.match(file_name)
        platform_info_dict = re_match.groupdict()
        os_type = platform_info_dict["os_type"]
        cpu_arch = platform_info_dict["cpu_arch"]
        config_name = platform_info_dict["config_name"]
        return {"platform": f"{os_type}_{cpu_arch}", "config": config_name}

    def get_proxy_template_map(file_name: str) -> Dict[str, Any]:
        re_match = constants.AgentPackageMap.PROXY_CONFIG_TEMPLATE_RE.match(file_name)
        platform_info_dict = re_match.groupdict()
        config_name = platform_info_dict["config_name"]
        return {"platform": f"{constants.OsType.LINUX.lower()}_{constants.CpuType.x86_64}", "config": config_name}

    if os.path.isdir(template_abs_path):
        for config_file in os.listdir(template_abs_path):
            if constants.AgentPackageMap.AGENT_CONFIG_TEMPLATE_RE.match(config_file):
                agent_single_template = get_agent_template_map(config_file)
                config_file_map[constants.NodeType.AGENT.lower()][agent_single_template["platform"]].append(
                    agent_single_template["config"]
                )
            elif constants.AgentPackageMap.PROXY_CONFIG_TEMPLATE_RE.match(config_file):
                proxy_single_template = get_proxy_template_map(config_file)
                config_file_map[constants.NodeType.PROXY.lower()][proxy_single_template["platform"]].append(
                    proxy_single_template["config"]
                )
            else:
                logger.error(
                    _(
                        f"pkg_name -> {pkg_path} sub path -> {parent_path}  "
                        f"with irregular  config template file -> {config_file}"
                    )
                )
        return config_file_map
    else:
        logger.error(
            _(
                f"pkg_name -> {pkg_path} sub path -> {parent_path}/{path_name} "
                f"without {constants.AgentPackageMap.TEMPLATE} directory"
            )
        )
        return {}


def switch_releasing_version(medium: str, version: str, switch_releasing: str, releasing: str = None):
    releasing_version_map = models.GseAgentDesc.statistics_versions(medium=medium)
    if not releasing_version_map:
        raise exceptions.SwitchReleasingVersionError(message=f"安装介质 -> {medium} 不存在")

    # 数据校验
    medium_version_map: Dict[str, Dict[str, List[str]]] = releasing_version_map

    if releasing is None:
        medium_versions = []
        for __, version_list in medium_version_map[medium].items():
            medium_versions.extend(version_list)
    else:
        medium_versions = medium_version_map[medium][releasing]

    if version not in medium_versions:
        raise exceptions.SwitchReleasingVersionError(message=f"安装介质 -> {medium} 当前不存在版本号: -> {version}")

    for releasing_type, version_list in medium_version_map[medium].items():
        if version in version_list:
            base_releasing = releasing_type
            break
    else:
        raise exceptions.SwitchReleasingVersionError(message=_(f"未找到当前版本号 -> {version}对应迭代版本"))

    if releasing == base_releasing:
        raise exceptions.SwitchReleasingVersionError(message=f"版本号 -> {version} 当前为 -> {base_releasing} 版本")

    if base_releasing == switch_releasing:
        raise exceptions.SwitchReleasingVersionError(message=f"版本号 -> {version} 已经属于 -> {switch_releasing} 版本")

    if base_releasing == constants.AgentReleasingType.RELEASE:
        raise exceptions.SwitchReleasingVersionError(message=f"{base_releasing} 版本不可主动下线")

    if (
        switch_releasing == constants.AgentReleasingType.RELEASE
        and base_releasing != constants.AgentReleasingType.GRAYSCALE
    ):
        raise exceptions.SwitchReleasingVersionError(message="非灰度版本不可直接上线")

    try:
        with transaction.atomic():
            # 切换发布版本
            if switch_releasing == constants.AgentReleasingType.RELEASE:
                models.GseAgentDesc.objects.filter(
                    releasing_type=constants.AgentReleasingType.GRAYSCALE, medium=medium
                ).update(releasing_type=constants.AgentReleasingType.OFFLINE)

            # 取消灰度版本
            if switch_releasing == constants.AgentReleasingType.OFFLINE:
                models.GseAgentDesc.objects.filter(
                    releasing_type=constants.AgentReleasingType.GRAYSCALE, medium=medium
                ).update(releasing_type=constants.AgentReleasingType.RELEASE)

            # 下线版本切换灰度
            base_grayscale_version = medium_version_map[medium].get(constants.AgentReleasingType.GRAYSCALE)
            if switch_releasing == constants.AgentReleasingType.GRAYSCALE and base_grayscale_version:
                models.GseAgentDesc.objects.filter(releasing_type=switch_releasing).update(
                    releasing_type=constants.AgentReleasingType.OFFLINE
                )
                models.GseAgentDesc.objects.filter(
                    releasing_type=constants.AgentReleasingType.OFFLINE, version=version, medium=medium
                ).update(releasing_type=switch_releasing)
            else:
                models.GseAgentDesc.objects.filter(
                    medium=medium,
                    version=version,
                ).update(releasing_type=switch_releasing)
            return {"result": True}
    except (DatabaseError, IntegrityError) as e:
        return {"result": False, "data": e}
