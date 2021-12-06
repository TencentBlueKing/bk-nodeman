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
import os
from typing import List

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
    " && start gsectl.bat stop && ping -n 20 127.0.0.1 >> c:\\ping_ip.txt && {temp_path}\\7z.exe x"
    " {temp_path}\\{package_name} -o{temp_path} -y 1>nul 2>&1 && {temp_path}\\7z.exe x "
    "{temp_path}\\{package_name_tar} -aot -o{setup_path} -y 1>nul 2>&1 && gsectl.bat start"
)

# Proxy 重载配置命令模板
PROXY_RELOAD_CMD_TEMPLATE = """
result=0
count=0
for proc in gse_agent gse_transit gse_btsvr gse_data; do
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
AGENT_RELOAD_CMD_TEMPLATE = "cd {setup_path}/{node_type}/bin && ./gse_agent --reload || ./gsectl restart all"

# 节点类型 - 重载命令模板映射关系
NODE_TYPE__RELOAD_CMD_TPL_MAP = {
    constants.NodeType.PROXY.lower(): PROXY_RELOAD_CMD_TEMPLATE,
    constants.NodeType.AGENT.lower(): AGENT_RELOAD_CMD_TEMPLATE,
}


class RunUpgradeCommandService(AgentExecuteScriptService):
    @property
    def script_name(self):
        return "upgrade_command"

    def get_script_content(self, data, common_data: AgentCommonData, host: models.Host) -> str:
        agent_upgrade_pkg_name = self.get_agent_upgrade_pkg_name(host)
        general_node_type = self.get_general_node_type(host.node_type)
        agent_config = common_data.host_id__ap_map[host.bk_host_id].get_agent_config(host.os_type)

        if host.os_type == constants.OsType.WINDOWS:
            scripts = WINDOWS_UPGRADE_CMD_TEMPLATE.format(
                setup_path=agent_config["setup_path"],
                temp_path=agent_config["temp_path"],
                package_name=agent_upgrade_pkg_name,
                package_name_tar=agent_upgrade_pkg_name.replace("tgz", "tar"),
            )
            return scripts
        else:
            path = os.path.join(settings.BK_SCRIPTS_PATH, "upgrade_agent.sh.tpl")
            with open(path, encoding="utf-8") as fh:
                scripts = fh.read()
            reload_cmd = NODE_TYPE__RELOAD_CMD_TPL_MAP[general_node_type].format(
                setup_path=agent_config["setup_path"], node_type=general_node_type
            )
            scripts = scripts.format(
                setup_path=agent_config["setup_path"],
                temp_path=agent_config["temp_path"],
                package_name=agent_upgrade_pkg_name,
                node_type=general_node_type,
                reload_cmd=reload_cmd,
            )
            return scripts

    def _execute(self, data, parent_data, common_data: AgentCommonData):
        super()._execute(data, parent_data, common_data)

        # Windows 重启 Agent 会导致无法在作业平台获取脚本执行结果，此时默认该步骤成功
        skip_job_instance_ids: List[int] = []
        for job_instance_id, call_params in self.job_instance_id__call_params_map.items():
            # 通过调用参数判断 job_instance_id 是否执行的是 Windows 机器
            os_type = call_params["job_params"]["os_type"]
            if os_type == constants.OsType.WINDOWS:
                skip_job_instance_ids.append(job_instance_id)

        models.JobSubscriptionInstanceMap.objects.filter(
            node_id=self.id, job_instance_id__in=skip_job_instance_ids
        ).update(status=constants.BkJobStatus.SUCCEEDED)
