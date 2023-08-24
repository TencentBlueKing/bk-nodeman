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
    def get_os_type_by_os_type(cls, bk_os_type: str) -> Optional[str]:
        """根据 os_type 获取主机操作系统"""
        return constants.OS_TYPE.get(bk_os_type)

    @classmethod
    def get_os_type_by_os_name(cls, bk_os_name: str) -> Optional[str]:
        """根据 os_name 获取主机操作系统"""
        bk_os_name = bk_os_name.lower()

        for os_type, keywords in constants.OS_KEYWORDS.items():
            for keyword in keywords:
                if keyword in bk_os_name:
                    return os_type

        return None

    @classmethod
    def is_os_type_priority(cls) -> bool:
        return bool(
            models.GlobalSettings.get_config(models.GlobalSettings.KeyEnum.SYNC_CMDB_HOST_OS_TYPE_PRIORITY.value)
        )

    @classmethod
    def get_os_type(cls, host: Dict, is_os_type_priority: bool = False) -> str:
        """根据CC的主机属性，得到可能的操作系统"""
        bk_os_name = host.get("bk_os_name") or "unknown"
        bk_os_type = host.get("bk_os_type")

        os_type = cls.get_os_type_by_os_name(bk_os_name)

        if is_os_type_priority:
            os_type = cls.get_os_type_by_os_type(bk_os_type) or os_type
        else:
            os_type = os_type or cls.get_os_type_by_os_type(bk_os_type)

        # 若CMDB中区分不出操作系统，则默认是LINUX
        return os_type or constants.OsType.LINUX

    @classmethod
    def is_sync_cmdb_host_apply_cpu_arch(cls) -> bool:
        sync_cmdb_host_apply_cpu_arch = models.GlobalSettings.get_config(
            models.GlobalSettings.KeyEnum.SYNC_CMDB_HOST_APPLY_CPU_ARCH.value
        )
        return bool(sync_cmdb_host_apply_cpu_arch)

    @classmethod
    def get_cpu_arch(
        cls,
        host: Dict,
        is_sync_cmdb_host_apply_cpu_arch: bool = False,
        get_default: bool = True,
        os_type: str = constants.OsType.LINUX,
    ) -> Optional[str]:
        if is_sync_cmdb_host_apply_cpu_arch:
            cpu_arch = constants.CMDB_CPU_MAP.get(host.get("bk_cpu_architecture"))
            bk_os_bit = host.get("bk_os_bit")

            if bk_os_bit == "arm-64bit":
                return constants.CpuType.aarch64

            if cpu_arch == constants.CpuType.x86:
                # 仅在 CMDB CPU 位数不为空的情况下进行同步，其他情况返回操作系统默认的位数
                if bk_os_bit:
                    bit_suffix = "" if "32" in bk_os_bit else "_64"
                    return cpu_arch + bit_suffix
                else:
                    # 对于 AIX / SOLARIS 这里的情况单一
                    # 对于 Linux / Windows，可能是 x86 / x86_64，x86 本身属于极少数情况，此处返回 x86_64 兜底
                    # x86 等待采集器同步后，下一次同步主机时获取
                    return constants.DEFAULT_OS_CPU_MAP.get(os_type, constants.CpuType.x86_64)
            # aarch64
            elif cpu_arch:
                return cpu_arch

        if get_default:
            return constants.DEFAULT_OS_CPU_MAP.get(os_type, constants.CpuType.x86_64)

        return None

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
