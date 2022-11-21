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

from typing import Any, Dict, List, Optional, Set

from apps.core.ipchooser.tools.base import HostQueryHelper
from apps.node_man import constants, models


class HostV2Tools:
    @classmethod
    def get_os_type(cls, host: Dict) -> str:
        """根据CC的主机属性，得到可能的操作系统"""
        bk_os_name = host.get("bk_os_name") or "unknown"
        bk_os_type = host.get("bk_os_type")
        os_name = bk_os_name.lower()

        linux_keywords = ["linux", "ubuntu", "centos", "redhat", "suse", "debian", "fedora"]
        windows_keywords = ["windows", "xserver"]
        aix_keywords = ["aix"]

        for linux_keyword in linux_keywords:
            if linux_keyword in os_name:
                return constants.OsType.LINUX

        for windows_keyword in windows_keywords:
            if windows_keyword in os_name:
                return constants.OsType.WINDOWS

        for aix_keyword in aix_keywords:
            if aix_keyword in os_name:
                return constants.OsType.AIX

        if bk_os_type in constants.OS_TYPE:
            return constants.OS_TYPE[bk_os_type]

        # 若CMDB中区分不出操作系统，则默认是LINUX
        return constants.OsType.LINUX

    @classmethod
    def get_cpu_arch(cls, host: Dict) -> str:
        os_type = cls.get_os_type(host)
        # 暂时通过操作系统区分CPU架构，后续通过CMDB的CPU架构字段区分
        return constants.DEFAULT_OS_CPU_MAP.get(os_type, constants.CpuType.x86_64)

    @classmethod
    def list_scope_host_ids(cls, scope: Dict) -> List[int]:
        bk_host_ids = []
        if scope["node_type"] == models.Subscription.NodeType.INSTANCE:
            bk_host_ids = [node["bk_host_id"] for node in scope["nodes"]]
        elif scope["node_type"] == models.Subscription.NodeType.TOPO:
            bk_host_ids: List[int] = HostQueryHelper.query_hosts_base(
                node_list=scope["nodes"], conditions=[]
            ).values_list("bk_host_id", flat=True)
        return bk_host_ids

    @classmethod
    def list_scope_hosts(cls, scope: Dict) -> List[Dict[str, Any]]:
        host_infos = []
        bk_host_ids = cls.list_scope_host_ids(scope)
        for host_info in list(
            models.Host.objects.filter(bk_host_id__in=bk_host_ids).values("bk_host_id", "os_type", "cpu_arch")
        ):
            host_info["os"] = host_info["os_type"].lower() or constants.OsType.LINUX.lower()
            host_infos.append(host_info)
        return host_infos

    @classmethod
    def get_bk_host_id_plugin_version_map(cls, project: str, bk_host_ids: List[int]) -> Dict[int, str]:
        proc_statuses = list(
            models.ProcessStatus.objects.filter(
                name=project,
                bk_host_id__in=set(bk_host_ids),
                is_latest=True,
                source_type=models.ProcessStatus.SourceType.DEFAULT,
            ).values("bk_host_id", "version")
        )
        return {proc_status["bk_host_id"]: proc_status["version"] for proc_status in proc_statuses}

    @classmethod
    def retrieve_host_info(cls, cmdb_host_info: Dict, fields: List[str] = None) -> Dict:
        fields = fields or ["ip", "bk_biz_id", "bk_cloud_id", "os_type"]
        host_info = {}
        for field in fields:
            if field == "os_type":
                host_info[field] = cls.get_os_type(cmdb_host_info)
                continue
            elif field == "ip":
                host_info[field] = cmdb_host_info.get("bk_host_innerip") or cmdb_host_info.get("bk_host_innerip_v6")
                continue
            host_info[field] = cmdb_host_info.get(field)
        return host_info

    @classmethod
    def host_infos_deduplication(cls, host_infos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        根据 bk_host_id 对主机信息列表进行去重
        :param host_infos: 主机信息列表
        :return:
        """
        recorded_host_ids: Set[int] = set()
        host_infos_after_deduplication: List[Dict[str, Any]] = []
        for host_info in host_infos:
            bk_host_id: int = host_info["bk_host_id"]
            if bk_host_id in recorded_host_ids:
                continue
            recorded_host_ids.add(bk_host_id)
            host_infos_after_deduplication.append(host_info)
        return host_infos_after_deduplication

    @classmethod
    def get_host_infos_with_the_same_ips(
        cls,
        host_infos_gby_ip_key: Dict[str, List[Dict[str, Any]]],
        host_info: Dict[str, Any],
        ip_field_names: List[str],
    ) -> List[Dict[str, Any]]:
        """
        按 IP 信息聚合主机信息
        :param host_infos_gby_ip_key:
        :param host_info: 主机信息
        :param ip_field_names: host_info 中的 IP 字段名
        :return: 聚合并去重的主机信息列表
        """
        host_infos_with_the_same_ips: List[Dict[str, Any]] = []
        for ip_field_name in ip_field_names:
            ip: Optional[str] = host_info.get(ip_field_name)
            bk_addressing: str = host_info.get("bk_addressing") or constants.CmdbAddressingType.STATIC.value
            ip_key: str = f"{bk_addressing}:{host_info['bk_cloud_id']}:{ip}"
            host_infos_with_the_same_ips.extend(host_infos_gby_ip_key.get(ip_key, []))

        return cls.host_infos_deduplication(host_infos_with_the_same_ips)
