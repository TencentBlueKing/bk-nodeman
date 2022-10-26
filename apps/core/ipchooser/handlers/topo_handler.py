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
import typing
from collections import defaultdict

from django.db.models import QuerySet

from apps.node_man import constants as node_man_constants
from apps.utils import concurrent

from .. import constants, types
from ..query import resource
from ..tools import base, topo_tool
from .base import BaseHandler

logger = logging.getLogger("app")


class TopoHandler:
    @staticmethod
    def format_tree(topo_tree: types.TreeNode) -> types.ReadableTreeNode:
        bk_biz_id: int = topo_tree["bk_inst_id"]
        topo_tree_stack: typing.List[types.TreeNode] = [topo_tree]
        # 定义一个通过校验的配置根节点及栈结构，同步 topo_tree_stack 进行遍历写入
        formatted_topo_tree: types.ReadableTreeNode = {}
        formatted_topo_tree_stack: typing.List[types.ReadableTreeNode] = [formatted_topo_tree]

        # 空间换时间，迭代模拟递归
        while topo_tree_stack:
            # 校验节点
            node = topo_tree_stack.pop()
            # 与 topo_tree_stack 保持相同的遍历顺序，保证构建拓扑树与给定的一致
            formatted_node = formatted_topo_tree_stack.pop()
            formatted_node.update(
                {
                    "instance_id": node["bk_inst_id"],
                    "instance_name": node["bk_inst_name"],
                    "object_id": node["bk_obj_id"],
                    "object_name": node["bk_obj_name"],
                    "meta": BaseHandler.get_meta_data(bk_biz_id),
                    "count": node.get("count", 0),
                    "child": [],
                    "lazy": False,
                }
            )
            child_nodes = node.get("child", [])
            topo_tree_stack.extend(child_nodes)
            formatted_node["child"] = [{} for __ in range(len(child_nodes))]
            formatted_topo_tree_stack.extend(formatted_node["child"])

        return formatted_topo_tree

    @classmethod
    def trees(cls, scope_list: types.ScopeList) -> typing.List[typing.Dict]:
        topo_trees: typing.List[typing.Dict] = []
        if len(scope_list) == 0:
            return []
        if len(scope_list) == 1:
            return [cls.format_tree(topo_tool.TopoTool.get_topo_tree_with_count(scope_list[0]["bk_biz_id"]))]

        bk_biz_ids: typing.List[int] = [scope["bk_biz_id"] for scope in scope_list]
        biz_id__info_map: typing.Dict[int, typing.Dict] = {
            biz_info["bk_biz_id"]: biz_info for biz_info in resource.ResourceQueryHelper.fetch_biz_list(bk_biz_ids)
        }
        biz_id__host_count_map: typing.Dict[int, int] = topo_tool.TopoTool.get_biz_id__host_count_map()
        for biz_id in bk_biz_ids:
            topo_trees.append(
                {
                    "instance_id": biz_id,
                    "instance_name": biz_id__info_map.get(biz_id, {}).get("bk_biz_name", biz_id),
                    "object_id": constants.ObjectType.BIZ.value,
                    "object_name": constants.ObjectType.get_member_value__alias_map()[constants.ObjectType.BIZ.value],
                    "meta": BaseHandler.get_meta_data(biz_id),
                    "child": [],
                    "count": biz_id__host_count_map.get(biz_id, 0),
                    "lazy": True,
                }
            )

        return sorted(topo_trees, key=lambda tree: tree["instance_id"])

    @staticmethod
    def query_path(node_list: typing.List[types.TreeNode]) -> typing.List[typing.List[types.TreeNode]]:
        if not node_list:
            return []
        nodes_gby_biz_id: typing.Dict[int, typing.List[types.TreeNode]] = defaultdict(list)
        for node in node_list:
            nodes_gby_biz_id[node["meta"]["bk_biz_id"]].append(
                {"bk_inst_id": node["instance_id"], "bk_obj_id": node["object_id"]}
            )

        params_list: typing.List[typing.Dict[str, typing.Any]] = []
        for biz_id, bk_nodes in nodes_gby_biz_id.items():
            params_list.append({"bk_biz_id": biz_id, "node_list": bk_nodes})
        node_with_paths: typing.List[types.TreeNode] = concurrent.batch_call(
            func=topo_tool.TopoTool.find_topo_node_paths, params_list=params_list, extend_result=True
        )

        inst_id__path_map: typing.Dict[int, typing.List[types.TreeNode]] = {}
        for node_with_path in node_with_paths:
            inst_id__path_map[node_with_path["bk_inst_id"]] = node_with_path.get("bk_path", [])

        node_paths_list: typing.List[typing.List[types.TreeNode]] = []
        for node in node_list:
            if node["instance_id"] not in inst_id__path_map:
                node_paths_list.append([])
                continue

            node_paths_list.append(
                [
                    {
                        "meta": node["meta"],
                        "object_id": path_node["bk_obj_id"],
                        "object_name": path_node["bk_obj_name"],
                        "instance_id": path_node["bk_inst_id"],
                        "instance_name": path_node["bk_inst_name"],
                    }
                    for path_node in inst_id__path_map[node["instance_id"]]
                ]
            )
        return node_paths_list

    @classmethod
    def query_hosts(
        cls,
        readable_node_list: typing.List[types.ReadableTreeNode],
        conditions: typing.List[types.Condition],
        limit_host_ids: typing.Optional[typing.List[int]],
        start: int,
        page_size: int,
    ) -> typing.Dict:
        """
        查询主机
        :param readable_node_list: 拓扑节点
        :param conditions: 查询条件
        :param limit_host_ids: 限制检索的主机 ID 列表
        :param start: 数据起始位置
        :param page_size: 拉取数据数量
        :return:
        """
        if not readable_node_list:
            # 不存在查询节点提前返回，减少非必要 IO
            return {"total": 0, "data": []}

        # 查询主机
        host_queryset: QuerySet = base.HostQueryHelper.query_hosts_base(
            node_list=[BaseHandler.format2tree_node(node) for node in readable_node_list],
            conditions=conditions,
            limit_host_ids=limit_host_ids,
        )
        # 执行分页
        host_page_queryset: QuerySet = base.HostQuerySqlHelper.paginate_queryset(
            queryset=host_queryset, start=start, page_size=page_size
        )
        # 获取主机信息
        host_fields: typing.List[str] = constants.CommonEnum.DEFAULT_HOST_FIELDS.value
        untreated_host_infos: typing.List[types.HostInfo] = list(host_page_queryset.values(*host_fields))

        return {"total": host_queryset.count(), "data": BaseHandler.format_hosts(untreated_host_infos)}

    @classmethod
    def query_host_id_infos(
        cls,
        readable_node_list: typing.List[types.ReadableTreeNode],
        conditions: typing.List[types.Condition],
        limit_host_ids: typing.Optional[typing.List[int]],
        start: int,
        page_size: int,
    ) -> typing.Dict:
        """
        查询主机 ID 信息
        :param readable_node_list: 拓扑节点
        :param conditions: 查询条件
        :param limit_host_ids: 限制检索的主机 ID 列表
        :param start: 数据起始位置
        :param page_size: 拉取数据数量
        :return:
        """
        if not readable_node_list:
            # 不存在查询节点提前返回，减少非必要 IO
            return {"total": 0, "data": []}

        # 查询主机
        host_queryset: QuerySet = base.HostQueryHelper.query_hosts_base(
            node_list=[BaseHandler.format2tree_node(node) for node in readable_node_list],
            conditions=conditions,
            limit_host_ids=limit_host_ids,
        )
        # 执行分页
        host_page_queryset: QuerySet = base.HostQuerySqlHelper.paginate_queryset(
            queryset=host_queryset, start=start, page_size=page_size
        )
        # 指定查询主机的必要字段
        untreated_host_infos: typing.List[types.HostInfo] = list(
            host_page_queryset.values("bk_host_id", "inner_ip", "inner_ipv6", "bk_cloud_id", "bk_biz_id")
        )
        treated_host_infos: typing.List[types.HostInfo] = []
        for untreated_host_info in untreated_host_infos:
            treated_host_infos.append(
                {
                    "meta": BaseHandler.get_meta_data(untreated_host_info["bk_biz_id"]),
                    "host_id": untreated_host_info["bk_host_id"],
                    "cloud_id": untreated_host_info["bk_cloud_id"],
                    "ip": untreated_host_info["inner_ip"],
                    "ipv6": untreated_host_info["inner_ipv6"],
                }
            )

        return {"total": host_queryset.count(), "data": treated_host_infos}

    @classmethod
    def agent_statistics(cls, readable_node_list: typing.List[types.ReadableTreeNode]) -> typing.List[typing.Dict]:
        """
        获取多个拓扑节点的主机 Agent 状态统计信息
        :param readable_node_list: 可读的节点信息列表
        :return:
        """
        # 获取 Agent 状态统计信息
        agent_statistic_infos: typing.List[typing.Dict] = topo_tool.TopoTool.fetch_agent_statistics_infos(
            node_list=[BaseHandler.format2tree_node(node) for node in readable_node_list]
        )
        # 建立节点 ID - Agent 状态统计信息映射
        inst_id__agent_statistics_map: typing.Dict[int, typing.Dict[str, int]] = {
            agent_statistics_info["node"]["bk_inst_id"]: agent_statistics_info["agent_statistics"]
            for agent_statistics_info in agent_statistic_infos
        }

        # 格式化返回
        formatted_agent_statistics_infos: typing.List[typing.Dict] = []
        for readable_node in readable_node_list:
            agent_statistics: typing.Dict[str, int] = (
                inst_id__agent_statistics_map.get(readable_node["instance_id"]) or {}
            )
            total_count: int = agent_statistics.get("total", 0)
            alive_count: int = agent_statistics.get(node_man_constants.ProcStateType.RUNNING, 0)
            # 非 alive 统一归到 not alive
            not_alive_count: int = total_count - alive_count
            formatted_agent_statistics_infos.append(
                {
                    "agent_statistics": {
                        "total_count": agent_statistics["total"],
                        "alive_count": alive_count,
                        "not_alive_count": not_alive_count,
                        # 废弃
                        "no_alive_count": not_alive_count,
                    },
                    "node": readable_node,
                }
            )

        return formatted_agent_statistics_infos
