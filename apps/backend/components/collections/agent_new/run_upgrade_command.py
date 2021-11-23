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
from apps.node_man.models import JobSubscriptionInstanceMap

from .base import AgentCommonData, AgentExecuteScriptService

"""
1. 停止agent，此时无法从Job获取任务结果
2. 解压升级包到目标路径，使用 -aot 参数把已存在的二进制文件重命名
3. 启动agent
"""
WINDOWS_SCRIPTS_TEMPLATE = (
    'reg add "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" '
    '/v gse_agent /t reg_sz /d "{setup_path}\\agent\\bin\\gsectl.bat start" /f 1>nul 2>&1'
    " && start gsectl.bat stop && ping -n 20 127.0.0.1 >> c:\\ping_ip.txt && {temp_path}\\7z.exe x"
    " {temp_path}\\{package_name} -o{temp_path} -y 1>nul 2>&1 && {temp_path}\\7z.exe x "
    "{temp_path}\\{package_name_tar} -aot -o{setup_path} -y 1>nul 2>&1 && gsectl.bat start"
)

PROXY_RELOAD_SCRIPTS_TEMPLATE = """
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
AGENT_RELOAD_SCRIPTS_TEMPLATE = "cd {setup_path}/{node_type}/bin && ./gse_agent --reload || ./gsectl restart all"
NODE_TYPE__RELOAD_CMD_TPL_MAP = {
    constants.NodeType.PROXY.lower(): PROXY_RELOAD_SCRIPTS_TEMPLATE,
    constants.NodeType.AGENT.lower(): AGENT_RELOAD_SCRIPTS_TEMPLATE,
}


class RunUpgradeCommandService(AgentExecuteScriptService):
    @property
    def script_name(self):
        return "upgrade_command"

    def get_script_content(self, data, common_data: AgentCommonData, host: models.Host) -> str:
        # 获取主机基本属性
        agent_config = common_data.host_id__ap_map[host.bk_host_id].get_agent_config(host.os_type)
        temp_path = agent_config["temp_path"]
        setup_path = agent_config["setup_path"]
        package_type = data.get_one_of_inputs("package_type")
        package_name = f"gse_{package_type}-{host.os_type.lower()}-{host.cpu_arch}_upgrade.tgz"
        # 排除掉PAGENT情况
        node_type = "proxy" if host.node_type == constants.NodeType.PROXY else "agent"

        if host.os_type == constants.OsType.WINDOWS:
            scripts = WINDOWS_SCRIPTS_TEMPLATE.format(
                setup_path=setup_path,
                temp_path=temp_path,
                package_name=package_name,
                package_name_tar=package_name.replace("tgz", "tar"),
            )
            return scripts
        else:
            path = os.path.join(settings.BK_SCRIPTS_PATH, "upgrade_agent.sh.tpl")
            with open(path, encoding="utf-8") as fh:
                scripts = fh.read()
            reload_cmd = NODE_TYPE__RELOAD_CMD_TPL_MAP[node_type].format(setup_path=setup_path, node_type=node_type)
            scripts = scripts.format(
                setup_path=setup_path,
                temp_path=temp_path,
                package_name=package_name,
                node_type=node_type,
                reload_cmd=reload_cmd,
            )
            return scripts

    def _schedule(self, data, parent_data, callback_data=None):
        """
        取消对windows机器的轮询，将windows的任务取消轮询，直接设置为True
        TODO 是否需要设置SKIP之类的状态?
        """
        common_data = self.get_common_data(data)
        bk_host_ids = common_data.bk_host_ids
        sub_instance_ids = common_data.subscription_instance_ids
        # 记录已经更新的windows主机集合，防止多次更新
        is_updated_win_sub_ids: List[int] = []
        for sub_instance_id, bk_host_id in zip(sub_instance_ids, bk_host_ids):
            host_os_type = common_data.host_id_obj_map[bk_host_id].os_type
            if host_os_type == constants.OsType.WINDOWS and sub_instance_id not in is_updated_win_sub_ids:
                job_sub_ins_map = JobSubscriptionInstanceMap.objects.filter(
                    node_id=self.id, subscription_instance_ids__contains=[sub_instance_id]
                )
                is_updated_win_sub_ids.extend(job_sub_ins_map.first().subscription_instance_ids)
                job_sub_ins_map.update(status=constants.BkJobStatus.SUCCEEDED)

        super()._schedule(data, parent_data, callback_data)
