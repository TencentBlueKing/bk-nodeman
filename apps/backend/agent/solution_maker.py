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
import abc
import base64
import json
import time
import typing
from pathlib import Path

from bkcrypto.asymmetric.ciphers import BaseAsymmetricCipher
from bkcrypto.constants import AsymmetricCipherType
from bkcrypto.contrib.django.ciphers import (
    asymmetric_cipher_manager,
    symmetric_cipher_manager,
)
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from apps.backend.api import constants as backend_api_constants
from apps.backend.subscription.steps.agent_adapter.base import AgentSetupInfo
from apps.core.script_manage.base import ScriptHook
from apps.node_man import constants, models
from apps.utils import basic


class ExecutionSolutionStepContent:
    def __init__(
        self,
        name: str,
        text: str,
        description: str,
        child_dir: str = None,
        always_download: bool = False,
        show_description: bool = True,
    ):
        self.name = name
        self.text = text
        self.description = description
        self.child_dir = child_dir
        self.show_description = show_description
        self.always_download = always_download


class ExecutionSolutionStep:
    def __init__(self, step_type: str, description: str, contents: typing.List[ExecutionSolutionStepContent]):
        self.type = step_type
        self.contents = contents
        self.description = description


class ExecutionSolution:
    def __init__(
        self,
        solution_type: str,
        description: str,
        steps: typing.List[ExecutionSolutionStep],
        target_host_solutions: typing.Optional[typing.List["ExecutionSolution"]] = None,
    ):
        self.type = solution_type
        self.description = description
        self.steps = steps
        self.target_host_solutions: typing.List["ExecutionSolution"] = target_host_solutions or []


class ExecutionSolutionTools:
    @staticmethod
    def need_jump_server(host: models.Host) -> bool:
        """
        目标机器是否需要借助跳板机
        :param host: 主机信息
        :return:
        """
        # 远程安装 P-AGENT 或者指定安装通道时，需要跳板执行
        return host.install_channel_id or host.node_type == constants.NodeType.PAGENT

    @classmethod
    def choose_script_file(cls, host: models.Host, is_execute_on_target: bool) -> str:
        """
        选择脚本文件
        :param host: 主机信息
        :param is_execute_on_target:是否直接在目标机器上执行
        :return:
        """
        if host.node_type == constants.NodeType.PROXY:
            # proxy 安装
            return constants.SetupScriptFileName.SETUP_PROXY_SH.value

        if cls.need_jump_server(host) and not is_execute_on_target:
            # 需要跳板且通过代理执行安装，使用 setup_pagent 脚本
            return constants.SetupScriptFileName.SETUP_PAGENT_PY.value

        # 其它场景，按操作系统来区分
        script_file_name = constants.SCRIPT_FILE_NAME_MAP[host.os_type]
        return script_file_name


class BaseExecutionSolutionMaker(metaclass=abc.ABCMeta):
    # 是否直接在目标机器上执行
    IS_EXECUTE_ON_TARGET_HOST: bool = True

    def __init__(
        self,
        agent_setup_info: AgentSetupInfo,
        host: models.Host,
        host_ap: models.AccessPoint,
        identity_data: models.IdentityData,
        install_channel: typing.Optional[typing.Tuple[models.Host, typing.Dict[str, typing.List]]],
        gse_servers_info: typing.Dict[str, typing.Any],
        sub_inst_id: int,
        pipeline_id: str,
        is_uninstall: bool,
        is_combine_cmd_step: typing.Optional[bool] = False,
        token: typing.Optional[str] = None,
        script_hook_objs: typing.Optional[typing.List[ScriptHook]] = None,
    ):
        self.agent_setup_info = agent_setup_info
        self.host = host
        self.host_ap = host_ap
        self.identity_data = identity_data
        self.install_channel = install_channel
        self.gse_servers_info = gse_servers_info
        self.sub_inst_id = sub_inst_id
        self.pipeline_id = pipeline_id
        self.is_uninstall = is_uninstall
        self.is_combine_cmd_step = is_combine_cmd_step
        self.script_hook_objs: typing.List[ScriptHook] = script_hook_objs or []

        self.script_file_name: str = ExecutionSolutionTools.choose_script_file(
            self.host, self.IS_EXECUTE_ON_TARGET_HOST
        )
        self.agent_config: typing.Dict[str, typing.Any] = self.host_ap.get_agent_config(self.host.os_type)
        self.dest_dir: str = basic.suffix_slash(self.host.os_type.lower(), self.agent_config["temp_path"])

        if token:
            # 允许 token 传递，以便代理（Proxy）make 目标执行方案时复用 token，保证 token 一致
            self.token = token
        else:
            self.token: str = symmetric_cipher_manager.cipher().encrypt(
                f"{self.host.bk_host_id}|{self.host.inner_ip or self.host.inner_ipv6}|{self.host.bk_cloud_id}|"
                f"{self.pipeline_id}|{time.time()}|{self.sub_inst_id}|{self.host_ap.id}"
            )

    def get_http_proxy_url(self) -> str:
        jump_server: models.Host = self.gse_servers_info["jump_server"]
        jump_server_lan_ip: str = jump_server.inner_ip or jump_server.inner_ipv6
        if basic.is_v6(jump_server_lan_ip):
            jump_server_lan_ip = f"[{jump_server_lan_ip}]"
        return "http://{jump_server_lan_ip}:{jump_server_port}".format(
            jump_server_lan_ip=jump_server_lan_ip, jump_server_port=settings.BK_NODEMAN_NGINX_PROXY_PASS_PORT
        )

    def get_setup_type_alias(self):
        return _("卸载") if self.is_uninstall else _("安装")

    def get_package_url(self) -> str:
        """
        获取包下载
        :return:
        """
        if ExecutionSolutionTools.need_jump_server(self.host):
            jump_server: models.Host = self.gse_servers_info["jump_server"]
            jump_server_lan_ip: str = jump_server.inner_ip or jump_server.inner_ipv6
            if basic.is_v6(jump_server_lan_ip):
                jump_server_lan_ip = f"[{jump_server_lan_ip}]"
            return "http://{jump_server_lan_ip}:{proxy_nginx_pass_port}".format(
                jump_server_lan_ip=jump_server_lan_ip, proxy_nginx_pass_port=settings.BK_NODEMAN_NGINX_DOWNLOAD_PORT
            )
        else:
            return self.gse_servers_info["package_url"]

    def get_agent_tools_url(self, file_relative_path: str) -> str:
        """
        获取 Agent 设置工具下载地址
        :param file_relative_path:
        :return:
        """
        agent_tools_url: str = "/".join(
            list(
                filter(
                    None,
                    [
                        # 工具下载走的是接入点的包源，非直连挂代理
                        self.gse_servers_info["package_url"],
                        self.agent_setup_info.agent_tools_relative_dir,
                        file_relative_path,
                    ],
                )
            )
        )
        return agent_tools_url

    def need_encrypted_password(self) -> bool:
        return all(
            [
                settings.REGISTER_WIN_SERVICE_WITH_PASS,
                self.host.os_type == constants.OsType.WINDOWS,
                # 背景：过期密码会重置为 None，导致加密失败
                # 仅在密码非空的情况下加密，防止密码过期 / 手动安装的情况下报错
                self.identity_data.password is not None,
            ]
        )

    def adjust_cmd_proxy_config(self, cmd: str, option: typing.Optional[str] = None) -> str:
        # 直连无需启用代理
        if not ExecutionSolutionTools.need_jump_server(self.host):
            return cmd

        option: str = option or "-x"
        http_proxy_url: str = self.get_http_proxy_url()

        def _enable_proxy_config() -> str:
            return f"{cmd} {option} {http_proxy_url}"

        if self.host.install_channel_id:
            # 通过安装通道安装允许配置是否启用下载代理
            __, upstream_servers = self.install_channel
            agent_download_proxy: bool = upstream_servers.get("agent_download_proxy", True)
            #  启用下载代理
            if agent_download_proxy:
                cmd = _enable_proxy_config()
        else:
            # 非直连默认启用下载代理
            cmd = _enable_proxy_config()

        return cmd

    def get_run_cmd_base_params(self) -> typing.List[str]:
        port_config: typing.Dict[str, typing.Any] = self.host_ap.port_config
        run_cmd_params: typing.List[str] = [
            # 端口信息
            f'-O {port_config.get("io_port")}',
            f'-E {port_config.get("file_svr_port")}',
            f'-A {port_config.get("data_port")}',
            f'-V {port_config.get("btsvr_thrift_port")}',
            f'-B {port_config.get("bt_port")}',
            f'-S {port_config.get("bt_port_start")}',
            f'-Z {port_config.get("bt_port_end")}',
            f'-K {port_config.get("tracker_port")}',
            # gse 服务信息
            f'-e "{self.gse_servers_info["bt_file_servers"]}"',
            f'-a "{self.gse_servers_info["data_servers"]}"',
            f'-k "{self.gse_servers_info["task_servers"]}"',
            # 文件下载 / 回调服务信息
            f"-l {self.get_package_url()}",
            f"-r {self.gse_servers_info['callback_url']}",
            # 目标主机信息
            f"-i {self.host.bk_cloud_id}",
            f"-I {self.host.inner_ip or self.host.inner_ipv6}",
            # 安装/下载配置
            f"-T {self.dest_dir}",
            f"-p {self.agent_config['setup_path']}",
            f"-c {self.token}",
            f"-s {self.pipeline_id}",
        ]

        # 系统开启使用密码注册 Windows 服务时，需额外传入 -U -P 参数，用于注册 Windows 服务，详见 setup_agent.bat 脚本
        if self.need_encrypted_password():
            # GSE 密码注册场景暂不启用国密，使用固定 RSA 的方式
            cipher: BaseAsymmetricCipher = asymmetric_cipher_manager.cipher(
                using="gse", cipher_type=AsymmetricCipherType.RSA.value
            )
            encrypted_password: str = cipher.encrypt(self.identity_data.password)

            run_cmd_params.extend(
                [
                    f"-U {self.identity_data.account}",
                    # 注意 -P 参数是base64，其中的 等号(=) 会被吃掉，需要添加 双引号("") 来规避此问题
                    f'-P "{encrypted_password}"',
                ]
            )

        if ExecutionSolutionTools.need_jump_server(self.host):
            run_cmd_params.extend(["-N PROXY", f"-x {self.get_http_proxy_url()}"])
        else:
            run_cmd_params.extend(["-N SERVER"])

        # 新版本 Agent 需要补充构件信息
        if not self.agent_setup_info.is_legacy:
            run_cmd_params.extend([f"-n {self.agent_setup_info.name}", f"-t {self.agent_setup_info.version}"])

        # 因 bat 脚本逻辑，-R 参数只能放在最后一位
        if self.is_uninstall:
            run_cmd_params.extend(["-R"])
        if self.agent_setup_info.force_update_agent_id:
            run_cmd_params.extend(["-F"])

        return list(filter(None, run_cmd_params))

    def add_sudo_to_cmds(self, execution_solution: ExecutionSolution):
        # 非 Windows 机器使用 sudo 权限执行命令
        # PAgent 依赖 setup_pagent.py 添加 sudo
        # Windows Cygwin sudo command not found：Cygwin 本身通过 administrator 启动，无需 sudo
        if any(
            [
                self.host.os_type == constants.OsType.WINDOWS,
                self.identity_data.account in [constants.LINUX_ACCOUNT],
                self.script_file_name == constants.SetupScriptFileName.SETUP_PAGENT_PY.value,
            ]
        ):
            return

        for execution_solution_step in execution_solution.steps:
            if execution_solution_step.type != constants.CommonExecutionSolutionStepType.COMMANDS.value:
                continue
            for execution_solution_content in execution_solution_step.contents:
                if execution_solution_content.name == "run_cmd":
                    shell_pkg: str = ("bash", "ksh")[self.host.os_type == constants.OsType.AIX]
                    execution_solution_content.text = f'sudo {shell_pkg} -c "{execution_solution_content.text}"'
                else:
                    execution_solution_content.text = f"sudo {execution_solution_content.text}"

    def combine_cmd_step(self, execution_solution: ExecutionSolution):
        for execution_solution_step in execution_solution.steps:
            if execution_solution_step.type != constants.CommonExecutionSolutionStepType.COMMANDS.value:
                continue
            cmds: typing.List[str] = [content.text for content in execution_solution_step.contents]
            if len(cmds) <= 1:
                continue
            if execution_solution.type == constants.CommonExecutionSolutionType.BATCH.value:
                text: str = " && ".join(cmds)
            else:
                shell_pkg: str = ("bash", "ksh")[self.host.os_type == constants.OsType.AIX]
                text: str = "{shell_pkg} -c 'exec 2>&1 && {multi_cmds_str}'".format(
                    shell_pkg=shell_pkg, multi_cmds_str=" && ".join(cmds)
                )

            execution_solution_step.contents = [
                ExecutionSolutionStepContent(
                    name="combine",
                    text=text,
                    description=execution_solution_step.description,
                    show_description=False,
                )
            ]

    def get_create_pre_dirs_step(self, is_shell_adapter: bool = False) -> ExecutionSolutionStep:
        """
        获取前置依赖路径创建命令
        :param is_shell_adapter: 是否适配 shell 命令
        :return:
        """
        # 目前依赖文件路径相关配置分两类：1-文件名路径，创建上级目录，2-目录路径，暂无需求
        filepath_config_names: typing.List[str] = []

        if self.host.os_type != constants.OsType.WINDOWS:
            filepath_config_names.extend(["dataipc"])

        dirs_to_be_created: typing.Set[str] = {self.dest_dir}
        # 获取到相应操作系统
        agent_config: typing.Dict[str, typing.Any] = self.host_ap.get_agent_config(self.host.os_type)
        for filepath_config_name in filepath_config_names:
            filepath: str = agent_config.get(filepath_config_name)
            if not filepath:
                continue
            filedir: str = str(Path(filepath).parent)
            # 冗余创建检测
            if filedir not in [".", "..", "/var/run", "/var/lib", "/var/log", "/var/run/", "/var/lib/", "/var/log/"]:
                dirs_to_be_created.add(filedir)

        create_pre_dir_step: ExecutionSolutionStep = ExecutionSolutionStep(
            step_type=constants.CommonExecutionSolutionStepType.COMMANDS.value,
            description=str(_("创建依赖目录")),
            contents=[],
        )
        create_dir_cmd_tmpl: str = ("mkdir {dir}", "mkdir -p {dir}")[
            is_shell_adapter or self.host.os_type != constants.OsType.WINDOWS
        ]
        for index, dir_to_be_created in enumerate(sorted(dirs_to_be_created)):
            # shell 适配
            if is_shell_adapter:
                dir_to_be_created = dir_to_be_created.replace("\\", "/")

            create_pre_dir_step.contents.append(
                ExecutionSolutionStepContent(
                    name=f"create_dir_cmd_{index}",
                    text=create_dir_cmd_tmpl.format(dir=dir_to_be_created),
                    description=str(_("创建 {dir}").format(dir=dir_to_be_created)),
                    show_description=False,
                )
            )

        return create_pre_dir_step

    def build_script_hook_steps(self, is_shell_adapter: bool = False) -> typing.List[ExecutionSolutionStep]:
        """
        构造脚本钩子步骤
        :param is_shell_adapter: 是否需要进行 shell 适配
        :return:
        """
        # 是否为 batch 方案
        is_batch: bool = self.host.os_type == constants.OsType.WINDOWS and not is_shell_adapter
        dest_dir: str = (self.dest_dir, self.dest_dir.replace("\\", "/"))[is_shell_adapter]
        curl_cmd: str = ("curl", f"{dest_dir}curl.exe")[is_batch]

        script_hook_steps: typing.List[ExecutionSolutionStep] = []
        for script_hook_obj in self.script_hook_objs:
            if script_hook_obj.script_info_obj.oneline:
                # 如果可以一行命令执行，直接执行相应的命令
                script_hook_steps.append(
                    ExecutionSolutionStep(
                        step_type=constants.CommonExecutionSolutionStepType.COMMANDS.value,
                        description=str(script_hook_obj.script_info_obj.description),
                        contents=[
                            ExecutionSolutionStepContent(
                                name="run_cmd",
                                text=script_hook_obj.script_info_obj.oneline,
                                description=str(script_hook_obj.script_info_obj.description),
                                show_description=False,
                            ),
                        ],
                    )
                )
                continue

            download_cmd = (
                f"{curl_cmd} {self.gse_servers_info['package_url']}/{script_hook_obj.script_info_obj.path} "
                f"-o {dest_dir}{script_hook_obj.script_info_obj.filename} --connect-timeout 5 -sSfg"
            )
            download_cmd = self.adjust_cmd_proxy_config(download_cmd)
            script_hook_step = ExecutionSolutionStep(
                step_type=constants.CommonExecutionSolutionStepType.COMMANDS.value,
                description=str(script_hook_obj.script_info_obj.description),
                contents=[
                    ExecutionSolutionStepContent(
                        name="download_cmd",
                        text=download_cmd,
                        description=str(_("下载 {filename}").format(filename=script_hook_obj.script_info_obj.filename)),
                        show_description=False,
                    ),
                ],
            )
            # 非 batch 方案需要为脚本授权
            if not is_batch:
                script_hook_step.contents.append(
                    ExecutionSolutionStepContent(
                        name="chmod_cmd",
                        text=f"chmod +x {dest_dir}{script_hook_obj.script_info_obj.filename}",
                        description=str(
                            _("为 {filename} 添加执行权限").format(filename=script_hook_obj.script_info_obj.filename)
                        ),
                        show_description=False,
                    )
                )

            script_hook_step.contents.append(
                ExecutionSolutionStepContent(
                    name="run_cmd",
                    text=f"{dest_dir}{script_hook_obj.script_info_obj.filename}",
                    description=str(_("执行 {filename}").format(filename=script_hook_obj.script_info_obj.filename)),
                    show_description=False,
                ),
            )

            script_hook_steps.append(script_hook_step)

        return script_hook_steps

    @abc.abstractmethod
    def _make(self) -> ExecutionSolution:
        raise NotImplementedError

    def make(self) -> ExecutionSolution:
        execution_solution: ExecutionSolution = self._make()
        if self.is_combine_cmd_step:
            self.combine_cmd_step(execution_solution)
        self.add_sudo_to_cmds(execution_solution)
        return execution_solution


class ShellExecutionSolutionMaker(BaseExecutionSolutionMaker):
    def shell_cmd_adapter(
        self,
        run_cmd_params: typing.List[str],
        options_path: typing.List[str],
        options_value_inside_quotes: typing.List[str],
    ) -> typing.Dict[str, str]:
        """
        shell 命令适配器
        :param run_cmd_params: 执行参数
        :param options_path: 待转义的路径参数项，适配 Cygwin
        :param options_value_inside_quotes: 值包含 , 或 ; 的参数项
        :return:
        """
        dest_dir: str = self.dest_dir
        if self.host.os_type == constants.OsType.WINDOWS:
            # Windows shell 适配
            dest_dir = self.dest_dir.replace("\\", "/")
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

        run_cmd: str = f"{dest_dir}{self.script_file_name} {' '.join(run_cmd_params_treated)}"
        # 异步执行封装
        if self.host.os_type == constants.OsType.WINDOWS:
            run_cmd = f"nohup {run_cmd} &> {dest_dir}nm.nohup.out &"
        else:
            suffix: str = backend_api_constants.SUFFIX_MAP[self.host.os_type.lower()]
            if suffix != backend_api_constants.SUFFIX_MAP[backend_api_constants.OS.AIX]:
                shell: str = "bash"
            else:
                shell: str = suffix
            run_cmd = f"nohup {shell} {run_cmd} &> {self.dest_dir}nm.nohup.out &"

        curl_cmd: str = ("curl", f"{dest_dir}curl.exe")[self.host.os_type == constants.OsType.WINDOWS]
        download_cmd = (
            f"{curl_cmd} {self.get_agent_tools_url(self.script_file_name)} "
            f"-o {dest_dir}{self.script_file_name} --connect-timeout 5 -sSfg"
        )
        download_cmd = self.adjust_cmd_proxy_config(download_cmd)

        return {"dest_dir": dest_dir, "run_cmd": run_cmd, "download_cmd": download_cmd}

    def _make(self) -> ExecutionSolution:
        # 生成安装脚本执行命令
        run_cmd_params: typing.List[str] = self.get_run_cmd_base_params()
        cmd_name__cmd_map: typing.Dict[str, str] = self.shell_cmd_adapter(
            run_cmd_params=run_cmd_params,
            options_path=["-T", "-p"],
            options_value_inside_quotes=["-e", "-a", "-k", "-P"],
        )

        solution_description: str = _("通过 {solution_type_alias} 进行{setup_type_alias}").format(
            solution_type_alias=constants.CommonExecutionSolutionType.get_member_value__alias_map()[
                constants.CommonExecutionSolutionType.SHELL.value
            ],
            setup_type_alias=self.get_setup_type_alias(),
        )
        if self.host.os_type == constants.OsType.WINDOWS:
            solution_description: str = _("{solution_description}（若目标机器已安装 Cygwin，推荐使用该方案，否则请使用【{batch}】方案）").format(
                solution_description=solution_description, batch=constants.CommonExecutionSolutionType.BATCH.value
            )

        execution_solution: ExecutionSolution = ExecutionSolution(
            solution_type=constants.CommonExecutionSolutionType.SHELL.value,
            description=str(solution_description),
            steps=self.build_script_hook_steps(is_shell_adapter=True),
        )

        if self.host.os_type == constants.OsType.WINDOWS:
            # Windows 需要下载依赖文件
            dependence_download_cmds_step: ExecutionSolutionStep = ExecutionSolutionStep(
                step_type=constants.CommonExecutionSolutionStepType.COMMANDS.value,
                description=str(_("依赖文件下载")),
                contents=[],
            )
            for name, description in constants.AgentWindowsDependencies.get_member_value__alias_map().items():
                # 默认 Cygwin 自带 curl
                # 若不存在引导安装：https://stackoverflow.com/questions/3647569/
                dependence_download_cmd: str = (
                    f"curl {self.gse_servers_info['package_url']}/{name} "
                    f"-o {cmd_name__cmd_map['dest_dir']}{name} --connect-timeout 5 -sSfg"
                )
                dependence_download_cmd = self.adjust_cmd_proxy_config(dependence_download_cmd)
                dependence_download_cmds_step.contents.append(
                    ExecutionSolutionStepContent(name=name, text=dependence_download_cmd, description=str(description))
                )

            execution_solution.steps.append(dependence_download_cmds_step)

        # 依赖目录创建作为第一个步骤
        execution_solution.steps.insert(0, self.get_create_pre_dirs_step(is_shell_adapter=True))
        execution_solution.steps.append(
            ExecutionSolutionStep(
                step_type=constants.CommonExecutionSolutionStepType.COMMANDS.value,
                description=str(
                    _("下载{setup_type_alias}脚本并赋予执行权限").format(setup_type_alias=self.get_setup_type_alias())
                ),
                contents=[
                    ExecutionSolutionStepContent(
                        name="download_cmd",
                        text=cmd_name__cmd_map["download_cmd"],
                        description=str(
                            _("下载{setup_type_alias}脚本").format(setup_type_alias=self.get_setup_type_alias())
                        ),
                        show_description=False,
                    ),
                    ExecutionSolutionStepContent(
                        name="chmod_cmd",
                        text=f"chmod +x {cmd_name__cmd_map['dest_dir']}{self.script_file_name}",
                        description=str(
                            _("为 {script_file_name} 添加执行权限").format(script_file_name=self.script_file_name)
                        ),
                        show_description=False,
                    ),
                ],
            )
        )
        execution_solution.steps.append(
            ExecutionSolutionStep(
                step_type=constants.CommonExecutionSolutionStepType.COMMANDS.value,
                description=str(_("执行{setup_type_alias}脚本").format(setup_type_alias=self.get_setup_type_alias())),
                contents=[
                    ExecutionSolutionStepContent(
                        name="run_cmd",
                        text=cmd_name__cmd_map["run_cmd"],
                        description=str(
                            _("执行{setup_type_alias}脚本").format(setup_type_alias=self.get_setup_type_alias())
                        ),
                        show_description=False,
                    ),
                ],
            )
        )
        return execution_solution


class BatchExecutionSolutionMaker(BaseExecutionSolutionMaker):
    def _make(self) -> ExecutionSolution:
        # 1. 准备阶段：创建目录
        create_pre_dirs_step: ExecutionSolutionStep = self.get_create_pre_dirs_step()

        # 2. 依赖下载
        dependencies_step: ExecutionSolutionStep = ExecutionSolutionStep(
            step_type=constants.CommonExecutionSolutionStepType.DEPENDENCIES.value,
            description=str(_("下载依赖文件到 {dest_dir} 下").format(dest_dir=self.dest_dir)),
            contents=[
                ExecutionSolutionStepContent(
                    name=name,
                    text=f"{self.gse_servers_info['package_url']}/{name}",
                    description=str(description),
                    show_description=False,
                )
                for name, description in constants.AgentWindowsDependencies.get_member_value__alias_map().items()
            ],
        )

        dependencies_step.contents.append(
            ExecutionSolutionStepContent(
                name="setup_agent.bat",
                text=f"{self.get_agent_tools_url(self.script_file_name)}",
                description="Install Scripts",
                child_dir=self.agent_setup_info.agent_tools_relative_dir,
                # 在云区域场景下需要实时更新
                always_download=True,
                show_description=False,
            )
        )

        # 3. 执行安装命令
        # download_cmd: str = (
        #     f"{self.dest_dir}curl.exe {self.get_agent_tools_url(self.script_file_name)} "
        #     f"-o {self.dest_dir}{self.script_file_name} -sSfg"
        # )
        # download_cmd = self.adjust_cmd_proxy_config(download_cmd)
        run_cmd: str = f"{self.dest_dir}{self.script_file_name} {' '.join(self.get_run_cmd_base_params())}"

        run_cmds_step: ExecutionSolutionStep = ExecutionSolutionStep(
            step_type=constants.CommonExecutionSolutionStepType.COMMANDS.value,
            description=str(_("执行{setup_type_alias}命令").format(setup_type_alias=self.get_setup_type_alias())),
            contents=[
                # ExecutionSolutionStepContent(
                #     name="download_cmd",
                #     text=download_cmd,
                #     description=str(_("下载{setup_type_alias}脚本").format(setup_type_alias=self.get_setup_type_alias())),
                #     show_description=False,
                # ),
                ExecutionSolutionStepContent(
                    name="run_cmd",
                    text=run_cmd,
                    description=str(_("执行{setup_type_alias}脚本").format(setup_type_alias=self.get_setup_type_alias())),
                    show_description=False,
                ),
            ],
        )

        return ExecutionSolution(
            solution_type=constants.CommonExecutionSolutionType.BATCH.value,
            description=str(
                _("通过 {solution_type_alias} 进行{setup_type_alias}").format(
                    solution_type_alias=constants.CommonExecutionSolutionType.get_member_value__alias_map()[
                        constants.CommonExecutionSolutionType.BATCH.value
                    ],
                    setup_type_alias=self.get_setup_type_alias(),
                )
            ),
            steps=[
                create_pre_dirs_step,
                dependencies_step,
                # 脚本的执行可能会有依赖受限，放置到依赖下载步骤之后
                *self.build_script_hook_steps(),
                run_cmds_step,
            ],
        )


class ProxyExecutionSolutionMaker(BaseExecutionSolutionMaker):

    IS_EXECUTE_ON_TARGET_HOST = False

    def get_run_cmd_base_params(self) -> typing.List[str]:
        host_identity: str = (self.identity_data.password, self.identity_data.key)[
            self.identity_data.auth_type == constants.AuthType.KEY
        ]
        login_ip: str = basic.compressed_ip(self.host.login_ip or self.host.inner_ip or self.host.inner_ipv6)
        run_cmd_params: typing.List[str] = [
            # 文件下载 / 回调服务信息
            f"-l {self.gse_servers_info['package_url']}",
            f"-r {self.gse_servers_info['callback_url']}",
            # 安装/下载配置
            f"-L {settings.DOWNLOAD_PATH}",
            f"-c {self.token}",
            f"-s {self.pipeline_id}",
            # 目标机器主机信息
            f"-HNT {self.host.node_type}",
            f"-HIIP {self.host.inner_ip or self.host.inner_ipv6}",
            f"-HC {self.host.bk_cloud_id}",
            f"-HOT {self.host.os_type.lower()}",
            # 目标机器登录信息
            f"-HI '{host_identity}'",
            f"-HP {self.identity_data.port}",
            f"-HAT {self.identity_data.auth_type}",
            f"-HA {self.identity_data.account}",
            f"-HLIP {login_ip}",
            # 目标机器安装配置
            f"-HDD '{self.dest_dir}'",
            # 代理机器配置
            f"-HPP '{settings.BK_NODEMAN_NGINX_PROXY_PASS_PORT}'",
            # 代理机器主机信息
            f"-I {self.gse_servers_info['jump_server'].inner_ip or self.gse_servers_info['jump_server'].inner_ipv6}",
        ]

        # 通道特殊配置
        if self.host.install_channel_id:
            __, upstream_servers = self.install_channel
            channel_proxy_address = upstream_servers.get("channel_proxy_address", None)
            if channel_proxy_address:
                run_cmd_params.extend([f"-CPA '{channel_proxy_address}'"])

        return list(filter(None, run_cmd_params))

    def _make(self) -> ExecutionSolution:

        solution_steps: typing.List[ExecutionSolutionStep] = []
        run_cmd_params: typing.List[str] = self.get_run_cmd_base_params()
        # 通过代理执行，代理都是 Linux 机器
        dest_dir = basic.suffix_slash(
            constants.OsType.LINUX, self.host_ap.get_agent_config(constants.OsType.LINUX)["temp_path"]
        )

        if self.host.is_manual:
            # 手动安装需要补充脚本执行路径
            run_cmd_params.insert(0, f"{dest_dir}{self.script_file_name}")
            # 手动安装情况下，需要补充安装脚本下载步骤
            download_cmd: str = (
                f"if [ ! -e {dest_dir}{self.script_file_name} ] || "
                f"[ `curl {self.get_agent_tools_url(self.script_file_name)} -sg | md5sum | awk '{{print $1}}'` "
                f"!= `md5sum {dest_dir}{self.script_file_name} | awk '{{print $1}}'` ]; then "
                f"curl {self.get_agent_tools_url(self.script_file_name)} -o {dest_dir}{self.script_file_name} "
                f"--connect-timeout 5 -sSfg && chmod +x {dest_dir}{self.script_file_name}; fi"
            )
            solution_steps.append(
                ExecutionSolutionStep(
                    step_type=constants.CommonExecutionSolutionStepType.COMMANDS.value,
                    description=str(_("下载{setup_type_alias}脚本").format(setup_type_alias=self.get_setup_type_alias())),
                    contents=[
                        ExecutionSolutionStepContent(
                            name="download_cmd",
                            text=download_cmd,
                            description=str(
                                _("下载{setup_type_alias}脚本").format(setup_type_alias=self.get_setup_type_alias())
                            ),
                            show_description=False,
                        )
                    ],
                )
            )

        # 补充执行目标方案
        target_host_solutions: typing.List[ExecutionSolution] = []
        target_host_solution_classes: typing.List[typing.Type[BaseExecutionSolutionMaker]] = [
            ShellExecutionSolutionMaker
        ]
        if self.host.os_type == constants.OsType.WINDOWS:
            target_host_solution_classes.append(BatchExecutionSolutionMaker)
        for target_host_solution_class in target_host_solution_classes:
            target_host_solutions.append(
                target_host_solution_class(
                    agent_setup_info=self.agent_setup_info,
                    host=self.host,
                    host_ap=self.host_ap,
                    identity_data=self.identity_data,
                    install_channel=self.install_channel,
                    gse_servers_info=self.gse_servers_info,
                    sub_inst_id=self.sub_inst_id,
                    pipeline_id=self.pipeline_id,
                    is_uninstall=self.is_uninstall,
                    is_combine_cmd_step=self.is_combine_cmd_step,
                    # 复用代理的 token
                    token=self.token,
                    script_hook_objs=self.script_hook_objs,
                ).make()
            )
        # 将执行方案通过 json + base64 编码，作为参数传入代理执行脚本
        run_cmd_params.append(
            f"-HSJB {base64.b64encode(json.dumps(basic.obj_to_dict(target_host_solutions)).encode()).decode()}"
        )

        solution_steps.append(
            ExecutionSolutionStep(
                step_type=constants.CommonExecutionSolutionStepType.COMMANDS.value,
                description=str(_("执行{setup_type_alias}脚本").format(setup_type_alias=self.get_setup_type_alias())),
                contents=[
                    ExecutionSolutionStepContent(
                        name="run_cmd",
                        text=" ".join(run_cmd_params),
                        description=str(
                            _("执行{setup_type_alias}脚本").format(setup_type_alias=self.get_setup_type_alias())
                        ),
                        show_description=False,
                    )
                ],
            )
        )

        return ExecutionSolution(
            solution_type=constants.CommonExecutionSolutionType.SHELL.value,
            description=str(
                _("通过 {solution_type_alias} 在代理上进行{setup_type_alias}").format(
                    solution_type_alias=constants.CommonExecutionSolutionType.get_member_value__alias_map()[
                        constants.CommonExecutionSolutionType.SHELL.value
                    ],
                    setup_type_alias=self.get_setup_type_alias(),
                )
            ),
            steps=solution_steps,
            target_host_solutions=target_host_solutions,
        )
