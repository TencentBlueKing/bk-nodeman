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
from dataclasses import dataclass, fields
from typing import Dict, List

from apps.core.files.storage import get_storage
from apps.node_man import constants, models

from .base import AgentCommonData, AgentTransferFileService


@dataclass
class PushAgentPkgCommonData(AgentCommonData):
    # 云区域ID -> 存活的 Proxy 列表 映射
    cloud_id__proxies_map: Dict[int, List[models.Host]]
    # 安装通道ID -> 安装通道对象 映射
    install_channel_id__host_objs_map: Dict[int, List[models.Host]]


class PushAgentPkgToProxyService(AgentTransferFileService):
    """
    下发 Agent 安装包到 Proxy，适用于 P-Agent 安装、安装通道安装等场景
    """

    def _execute(self, data, parent_data, common_data: AgentCommonData):
        # 提前批量查询安装通道、路径等数据，避免在 get_target_servers/get_job_file_params 中循环对单机进行查询
        cloud_ids = {host.bk_cloud_id for host in common_data.host_id_obj_map.values()}
        gse_version = data.get_one_of_inputs("meta", {}).get("GSE_VERSION")
        cloud_id__proxies_map = self.get_cloud_id__proxies_map(cloud_ids, common_data.ap_id_obj_map, gse_version)
        install_channel_ids = [
            host.install_channel_id for host in common_data.host_id_obj_map.values() if host.install_channel_id
        ]
        install_channel_id__host_objs_map = models.InstallChannel.install_channel_id__host_objs_map(install_channel_ids)
        push_agent_pkg_common_data = PushAgentPkgCommonData(
            cloud_id__proxies_map=cloud_id__proxies_map,
            install_channel_id__host_objs_map=install_channel_id__host_objs_map,
            **{field.name: getattr(common_data, field.name) for field in fields(common_data)}
        )
        return super()._execute(data, parent_data, push_agent_pkg_common_data)

    def get_target_servers(self, data, common_data: PushAgentPkgCommonData, host: models.Host):
        """
        查询主机所属云区域的 proxies，或者安装通道 jump server 的机器
        """
        target_servers = {"ip_list": [], "host_id_list": []}
        if host.install_channel_id:
            for install_channel_host in common_data.install_channel_id__host_objs_map[host.install_channel_id]:
                target_servers["ip_list"].append(
                    {"bk_cloud_id": install_channel_host.bk_cloud_id, "ip": install_channel_host.inner_ip}
                )
                target_servers["host_id_list"].append(install_channel_host.bk_host_id)
        else:
            for proxy in common_data.cloud_id__proxies_map[host.bk_cloud_id]:
                # 只对存活的 Proxy 分发文件，提高任务成功率
                if proxy.status != constants.ProcStateType.RUNNING:
                    continue
                target_servers["ip_list"].append({"bk_cloud_id": proxy.bk_cloud_id, "ip": proxy.inner_ip})
                target_servers["host_id_list"].append(proxy.bk_host_id)
        return target_servers

    def get_job_file_params(self, data, common_data: AgentCommonData, host: models.Host):
        storage = get_storage()
        agent_dir = self.get_agent_pkg_dir(common_data, host)
        pkg_name = self.get_agent_pkg_name(common_data, host, return_name_with_cpu_tmpl=True)

        if common_data.agent_step_adapter.is_legacy:
            file_list = []
            # 由于实际安装前 CPU 架构未知，此处对同操作系统的各类架构包进行一并下发
            for cpu_arch in constants.CPU_TUPLE:
                pkg_path = "/".join([agent_dir, pkg_name.format(cpu_arch=cpu_arch)])
                if storage.exists(pkg_path):
                    file_list.append(pkg_path)
            job_file_params = [{"file_list": file_list, "file_target_path": agent_dir}]
        else:
            cpu_arch_list, _ = storage.listdir(agent_dir)
            job_file_params = [
                {
                    "file_list": ["/".join([agent_dir, cpu_arch, pkg_name])],
                    "file_target_path": "/".join([agent_dir, cpu_arch]),
                }
                for cpu_arch in cpu_arch_list
            ]
        return job_file_params

    def get_job_param_os_type(self, host: models.Host) -> str:
        # Proxy 或者安装通道跳板机 要求是 Linux 机器
        return constants.OsType.LINUX
