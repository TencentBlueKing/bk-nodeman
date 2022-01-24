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

from collections import Counter
from itertools import groupby
from typing import Any, Dict, List, Optional, Union

from django.db.models import QuerySet

from apps.backend.constants import InstNodeType
from apps.node_man import constants, models
from apps.node_man.handlers.cmdb import CmdbHandler
from apps.utils.local import get_request


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

    @staticmethod
    def fetch_set_ids(bk_biz_id: int, target_inst_id: int, action: Optional[str] = None) -> list:
        """
        根据业务及节点id获取节点下全部集群ID
        :param bk_biz_id: 业务ID
        :param target_inst_id: 节点实例ID
        :param action: iam action type
        :return: 集群ID列表
        """
        params = {"bk_biz_id": bk_biz_id, "is_superuser": get_request().user.is_superuser, "with_biz_node": True}
        if action:
            params.update({"action": action})

        biz_topo = CmdbHandler().fetch_topo(**params)
        stack = [biz_topo]
        target_node = None

        while stack:
            cur_node = stack.pop()
            if cur_node["id"] == target_inst_id:
                target_node = cur_node
                break
            stack.extend(cur_node["children"])

        if not target_node:
            return []

        bk_set_ids = []
        node_stack = [target_node]

        while node_stack:
            cur_node = node_stack.pop()
            if cur_node["type"] == InstNodeType.SET:
                bk_set_ids.append(cur_node["id"])
                continue
            node_stack.extend(cur_node["children"])
        return bk_set_ids

    @classmethod
    def parse_nodes2conditions(
        cls, nodes: List[Dict[str, Any]], operate_bizs: Optional[List[int]] = None, action: Optional[str] = None
    ) -> List[Dict]:
        """
        将拓扑节点列表转换为主机查询条件
        :param nodes:
        :param operate_bizs:
        :param action: iam action type
        :return:
        """
        conditions = []
        for bk_biz_id, nodes in groupby(sorted(nodes, key=lambda x: x["bk_biz_id"]), key=lambda x: x["bk_biz_id"]):
            if not (operate_bizs is None or bk_biz_id in operate_bizs):
                continue
            value = {"bk_biz_id": bk_biz_id, "bk_set_ids": [], "bk_module_ids": []}
            for node in nodes:
                if node["bk_obj_id"] in [InstNodeType.BIZ, InstNodeType.SET, InstNodeType.MODULE]:
                    if node["bk_obj_id"] != InstNodeType.BIZ:
                        value["bk_{obj}_ids".format(obj=node["bk_obj_id"])].append(node["bk_inst_id"])
                else:
                    value["bk_set_ids"].extend(
                        cls.fetch_set_ids(bk_biz_id=bk_biz_id, target_inst_id=node["bk_inst_id"], action=action)
                    )
            conditions.append({"key": "topology", "value": value})
        return conditions

    @classmethod
    def parse_conditions2host_ids(cls, conditions: List[Dict]) -> List[int]:
        bk_host_ids = []
        bk_biz_ids = set()
        for condition in conditions:
            if condition["key"] != "topology":
                continue
            # 集群与模块的精准搜索
            biz = condition["value"].get("bk_biz_id")
            sets = condition["value"].get("bk_set_ids", [])
            modules = condition["value"].get("bk_module_ids", [])
            # 传入拓扑是一个业务，无需请求cc，直接从数据库获取bk_host_id
            if len(sets) == 0 and len(modules) == 0:
                bk_biz_ids.add(biz)
                continue
            host_ids = CmdbHandler().fetch_host_ids_by_biz(biz, sets, modules)
            bk_host_ids.extend(host_ids)
        # 非空再执行DB请求，减少无效IO
        if bk_biz_ids:
            bk_host_ids.extend(
                list(models.Host.objects.filter(bk_biz_id__in=bk_biz_ids).values_list("bk_host_id", flat=True))
            )
        return list(set(bk_host_ids))

    @staticmethod
    def get_agent_status_counter(hosts_sql: QuerySet) -> Dict[str, int]:
        statuses = list(hosts_sql.values_list("status", flat=True))
        agent_status_counter = dict(Counter(statuses))
        agent_status_counter["total"] = len(statuses)

        return {
            "total": agent_status_counter["total"],
            constants.ProcStateType.RUNNING: agent_status_counter.get(constants.ProcStateType.RUNNING, 0),
            constants.ProcStateType.NOT_INSTALLED: agent_status_counter.get(constants.ProcStateType.NOT_INSTALLED, 0),
            constants.ProcStateType.TERMINATED: agent_status_counter["total"]
            - (
                agent_status_counter.get(constants.ProcStateType.RUNNING, 0)
                + agent_status_counter.get(constants.ProcStateType.NOT_INSTALLED, 0)
            ),
        }

    @classmethod
    def list_host_ids_by_topo_node(
        cls, topo_node: Dict[str, Any], only_ids=True, action=None
    ) -> Union[Dict[str, Any], List[int]]:
        if topo_node["bk_obj_id"] == constants.CmdbObjectId.BIZ:
            topo_node["bk_inst_id"] = topo_node["bk_biz_id"]
        bk_host_ids = cls.parse_conditions2host_ids(cls.parse_nodes2conditions(nodes=[topo_node], action=action))
        if only_ids:
            return bk_host_ids
        return {"bk_host_ids": bk_host_ids, **topo_node}

    @classmethod
    def list_scope_host_ids(cls, scope: Dict) -> List[int]:
        bk_host_ids = []
        if scope["node_type"] == models.Subscription.NodeType.INSTANCE:
            bk_host_ids = [node["bk_host_id"] for node in scope["nodes"]]
        elif scope["node_type"] == models.Subscription.NodeType.TOPO:
            bk_host_ids = cls.parse_conditions2host_ids(cls.parse_nodes2conditions(nodes=scope["nodes"]))
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
        field__cmdb_field__map = {"ip": "bk_host_innerip"}

        host_info = {}
        for field in fields:
            if field == "os_type":
                host_info[field] = cls.get_os_type(cmdb_host_info)
                continue

            cmdb_field = field__cmdb_field__map.get(field, field)
            host_info[field] = cmdb_host_info.get(cmdb_field)
        return host_info
