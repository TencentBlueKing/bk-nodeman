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
import traceback
from typing import Any, Dict, List, Optional, Tuple, Type

import yaml
from django.conf import settings

from apps.backend import exceptions
from apps.node_man import constants, models

from ...utils import basic
from . import solution_maker

logger = logging.getLogger("app")


class InstallationTools:
    def __init__(
        self,
        execution_solutions: List[solution_maker.ExecutionSolution],
        upstream_nodes: str,
        jump_server: models.Host,
        proxies: List[models.Host],
        is_need_jump_server: bool,
        host: models.Host,
        ap: models.AccessPoint,
        identity_data: models.IdentityData,
        dest_dir: str,
        package_url: str,
    ):
        """
        :param execution_solutions: 执行方案
        :param upstream_nodes: 上游节点，通常为 proxy 或者安装通道指定的上游
        :param jump_server: 跳板服务器，通常为 proxy 或者安装通道的跳板机
        :param is_need_jump_server: 是否需要跳板执行
        :param host: 主机对象
        :param ap: 接入点对象
        :param identity_data: 认证数据对象
        :param proxies: 代理列表
        :param package_url 文件下载链接
        """
        # 跳板执行相关配置
        self.proxies = proxies
        self.upstream_nodes = upstream_nodes
        self.jump_server = jump_server
        self.proxies = proxies
        self.is_need_jump_server = is_need_jump_server

        # 主机信息
        self.host = host
        self.ap = ap
        self.identity_data = identity_data

        # 包下载路径
        self.package_url = package_url

        # 临时目录
        self.dest_dir = dest_dir

        # 执行方案
        self.type__execution_solution_map: Dict[str, solution_maker.ExecutionSolution] = {
            execution_solution.type: execution_solution for execution_solution in execution_solutions
        }


def gen_nginx_download_url(nginx_ip: str) -> str:
    return f"http://{nginx_ip}:{settings.BK_NODEMAN_NGINX_DOWNLOAD_PORT}/"


def fetch_gse_servers_info(
    host: models.Host,
    host_ap: models.AccessPoint,
    proxies: List[models.Host],
    install_channel: Tuple[models.Host, Dict[str, List]],
) -> Dict[str, Any]:
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

    elif host.node_type == constants.NodeType.AGENT:
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

    return {
        "jump_server": jump_server,
        "bt_file_servers": bt_file_servers,
        "data_servers": data_servers,
        "task_servers": task_servers,
        "package_url": package_url,
        "callback_url": callback_url,
    }


def gen_commands(
    host: models.Host,
    pipeline_id: str,
    is_uninstall: bool,
    sub_inst_id: int,
    identity_data: Optional[models.IdentityData] = None,
    host_ap: Optional[models.AccessPoint] = None,
    proxies: Optional[List[models.Host]] = None,
    install_channel: Optional[Tuple[models.Host, Dict[str, List]]] = None,
    is_combine_cmd_step: bool = False,
) -> InstallationTools:
    """
    生成安装命令
    :param is_combine_cmd_step:
    :param host: 主机信息
    :param pipeline_id: Node ID
    :param is_uninstall: 是否卸载
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
    gse_servers_info: Dict[str, Any] = fetch_gse_servers_info(
        host=host, host_ap=host_ap, proxies=proxies, install_channel=install_channel
    )
    dest_dir: str = basic.suffix_slash(host.os_type, host_ap.get_agent_config(host.os_type)["temp_path"])

    execution_solutions: List[solution_maker.ExecutionSolution] = []
    solution_classes: List[Type[solution_maker.BaseExecutionSolutionMaker]] = []
    is_need_jump_server: bool = solution_maker.ExecutionSolutionTools.need_jump_server(host)
    if is_need_jump_server:
        solution_classes.append(solution_maker.ProxyExecutionSolutionMaker)
    else:
        # shell 是直连主机的通用执行方案
        solution_classes.append(solution_maker.ShellExecutionSolutionMaker)
        # Windows 需要提供 batch 执行方案
        if host.os_type == constants.OsType.WINDOWS:
            solution_classes.append(solution_maker.BatchExecutionSolutionMaker)

    for solution_class in solution_classes:
        execution_solutions.append(
            solution_class(
                host=host,
                host_ap=host_ap,
                identity_data=identity_data,
                install_channel=install_channel,
                gse_servers_info=gse_servers_info,
                sub_inst_id=sub_inst_id,
                pipeline_id=pipeline_id,
                is_uninstall=is_uninstall,
                is_combine_cmd_step=is_combine_cmd_step,
            ).make()
        )

    return InstallationTools(
        execution_solutions=execution_solutions,
        upstream_nodes=gse_servers_info["task_servers"],
        jump_server=gse_servers_info["jump_server"],
        proxies=proxies,
        is_need_jump_server=is_need_jump_server,
        host=host,
        ap=host_ap,
        identity_data=identity_data,
        dest_dir=dest_dir,
        package_url=gse_servers_info["package_url"],
    )


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
