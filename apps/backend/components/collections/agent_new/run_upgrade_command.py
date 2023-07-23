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
import os
import typing

from django.conf import settings

from apps.node_man import constants, models

from .base import AgentCommonData, AgentExecuteScriptService

# Windows 升级命令模板
# 1. 停止 agent，此时无法从Job获取任务结果
# 2. 解压升级包到目标路径，使用 -aot 参数把已存在的二进制文件重命名
# 3. 启动agent
WINDOWS_UPGRADE_CMD_TEMPLATE = (
    'reg add "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" '
    '/v gse_agent /t reg_sz /d "{setup_path}\\agent\\bin\\gsectl.bat start" /f 1>nul 2>&1'
    " && start gsectl.bat stop"
    " && ping -n 20 127.0.0.1 >> c:\\ping_ip.txt"
    " && {temp_path}\\7z.exe x {temp_path}\\{package_name} -so |"
    " {temp_path}\\7z.exe x -aot -si -ttar -o{setup_path} 1>nul 2>&1"
    " && gsectl.bat start"
)

# Proxy 重载配置命令模板
PROXY_RELOAD_CMD_TEMPLATE = """
result=0
count=0
for proc in {procs}; do
     [ -f {setup_path}/{node_type}/bin/$proc ] && cd {setup_path}/{node_type}/bin && ./$proc --reload && \
     count=$((count + 1))
     sleep 1
     result=$((result + $?))
done
if [[ $result -gt 0 || $count -lt 3 ]]; then
   cd {setup_path}/{node_type}/bin && ./gsectl restart all
fi
"""

# Agent 重载配置命令模板
AGENT_RELOAD_CMD_TEMPLATE = "cd {setup_path}/{node_type}/bin && ./{procs} --reload || ./gsectl restart all"


# 进程拉起配置命令
PROCESS_PULL_CONFIGURATION_CMD = """setup_startup_scripts
remove_crontab
"""

# 节点类型 - 重载命令模板映射关系
LEGACY_NODE_TYPE__RELOAD_CMD_TPL_MAP = {
    constants.NodeType.PROXY.lower(): PROXY_RELOAD_CMD_TEMPLATE,
    constants.NodeType.AGENT.lower(): AGENT_RELOAD_CMD_TEMPLATE,
}


# 新版本 Agent 具有 systemd / crontab 等多种拉起方式，systemd 模式下 reload 会导致进程拉不起来
# 鉴于 reload 和 start 逻辑均是采取干掉进程再恢复的逻辑，统一采用 restart
NODE_TYPE__RELOAD_CMD_TPL_MAP = {
    constants.NodeType.PROXY.lower(): "cd {setup_path}/{node_type}/bin && ./gsectl restart all",
    constants.NodeType.AGENT.lower(): "cd {setup_path}/{node_type}/bin && ./gsectl restart",
}


class RunUpgradeCommandService(AgentExecuteScriptService):
    @property
    def script_name(self):
        return "upgrade_command"

    def get_script_content(self, data, common_data: AgentCommonData, host: models.Host) -> str:
        agent_upgrade_pkg_name = self.get_agent_pkg_name(common_data, host, is_upgrade=True)
        general_node_type = self.get_general_node_type(host.node_type)
        agent_config = common_data.host_id__ap_map[host.bk_host_id].get_agent_config(host.os_type)

        if host.os_type == constants.OsType.WINDOWS:
            scripts = WINDOWS_UPGRADE_CMD_TEMPLATE.format(
                setup_path=agent_config["setup_path"],
                temp_path=agent_config["temp_path"],
                package_name=agent_upgrade_pkg_name,
            )
            return scripts
        else:
            tpl_path = os.path.join(settings.BK_SCRIPTS_PATH, "upgrade_agent.sh.tpl")
            with open(tpl_path, encoding="utf-8") as fh:
                scripts = fh.read()

            if common_data.agent_step_adapter.is_legacy:
                process_pull_configuration_cmd: str = PROCESS_PULL_CONFIGURATION_CMD

                if host.node_type == constants.NodeType.PROXY:
                    procs: typing.List[str] = ["gse_agent", "gse_transit", "gse_btsvr", "gse_data"]
                else:
                    procs: typing.List[str] = ["gse_agent"]

                reload_cmd = LEGACY_NODE_TYPE__RELOAD_CMD_TPL_MAP[general_node_type].format(
                    setup_path=agent_config["setup_path"], node_type=general_node_type, procs=" ".join(procs)
                )

            else:
                # 新版本 Agent，通过 gsectl 配置进程拉起方式
                process_pull_configuration_cmd: str = ""
                reload_cmd = NODE_TYPE__RELOAD_CMD_TPL_MAP[general_node_type]

            scripts = scripts.format(
                setup_path=agent_config["setup_path"],
                temp_path=agent_config["temp_path"],
                package_name=agent_upgrade_pkg_name,
                node_type=general_node_type,
                reload_cmd=reload_cmd,
                process_pull_configuration_cmd=process_pull_configuration_cmd,
                pkg_cpu_arch=host.cpu_arch,
            )
            return scripts
