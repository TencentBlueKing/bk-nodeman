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
from copy import deepcopy

from django.db.models import Count, QuerySet

from apps.node_man import models as node_man_models
from apps.utils import concurrent

from .. import constants, types
from ..query import resource
from . import base

logger = logging.getLogger("app")


class TopoTool:
    @staticmethod
    def find_topo_node_paths(bk_biz_id: int, node_list: typing.List[types.TreeNode]):
        def _find_topo_node_paths(
            _cur_node: types.TreeNode, _cur_path: typing.List[types.TreeNode], _hit_inst_ids: typing.Set
        ):
            if _cur_node["bk_inst_id"] in inst_id__node_map:
                inst_id__node_map[_cur_node["bk_inst_id"]]["bk_path"] = deepcopy(_cur_path)
                _hit_inst_ids.add(_cur_node["bk_inst_id"])
                # 全部命中后提前返回
                if len(_hit_inst_ids) == len(inst_id__node_map.keys()):
                    return

            for _child_node in _cur_node.get("child") or []:
                _cur_path.append(_child_node)
                _find_topo_node_paths(_child_node, _cur_path, _hit_inst_ids)
                # 以 del 代替 [:-1]，防止后者产生 list 对象导致路径重复压栈
                del _cur_path[-1]

        topo_tree: types.TreeNode = resource.ResourceQueryHelper.get_topo_tree(bk_biz_id)
        inst_id__node_map: typing.Dict[int, types.TreeNode] = {bk_node["bk_inst_id"]: bk_node for bk_node in node_list}
        _find_topo_node_paths(topo_tree, [topo_tree], set())
        return node_list

    @staticmethod
    def get_biz_id__host_count_map() -> typing.Dict[int, int]:
        biz_host_count_infos: typing.List[typing.Dict] = (
            node_man_models.Host.objects.all()
            .values_list("bk_biz_id")
            .order_by("bk_biz_id")
            .annotate(host_count=Count("bk_host_id"))
            .values("host_count", "bk_biz_id")
        )
        biz_id__host_count_map: typing.Dict[int, int] = {
            biz_host_count_info["bk_biz_id"]: biz_host_count_info["host_count"]
            for biz_host_count_info in biz_host_count_infos
        }
        return biz_id__host_count_map

    @classmethod
    def fill_host_count_to_tree(
        cls, nodes: typing.List[types.TreeNode], host_ids_gby_module_id: typing.Dict[int, typing.List[int]]
    ) -> typing.Set[int]:
        total_host_ids: typing.Set[int] = set()
        for node in nodes:
            bk_host_ids: typing.Set[int] = set()
            if node.get("bk_obj_id") == constants.ObjectType.MODULE.value:
                bk_host_ids = bk_host_ids | set(host_ids_gby_module_id.get(node["bk_inst_id"], set()))
            else:
                bk_host_ids = cls.fill_host_count_to_tree(node.get("child", []), host_ids_gby_module_id)
            node["count"] = len(bk_host_ids)
            total_host_ids = bk_host_ids | total_host_ids
        return total_host_ids

    @classmethod
    def get_topo_tree_with_count(cls, bk_biz_id: int) -> types.TreeNode:
        topo_tree: types.TreeNode = resource.ResourceQueryHelper.get_topo_tree(bk_biz_id)
        host_topo_relations: typing.List[typing.Dict] = resource.ResourceQueryHelper.fetch_host_topo_relations(
            bk_biz_id
        )
        cache_host_ids: typing.Set[int] = set(
            node_man_models.Host.objects.filter(bk_biz_id=bk_biz_id).values_list("bk_host_id", flat=True)
        )
        host_ids_gby_module_id: typing.Dict[int, typing.List[int]] = defaultdict(list)
        for host_topo_relation in host_topo_relations:
            bk_host_id: int = host_topo_relation["bk_host_id"]
            # 暂不统计非缓存数据，遇到不一致的情况需要触发缓存更新
            if bk_host_id not in cache_host_ids:
                continue
            host_ids_gby_module_id[host_topo_relation["bk_module_id"]].append(bk_host_id)
        cls.fill_host_count_to_tree([topo_tree], host_ids_gby_module_id)
        return topo_tree

    @classmethod
    def fetch_agent_statistics_infos(cls, node_list: typing.List[types.TreeNode]) -> typing.List[typing.Dict]:
        """
        获取各节点 Agent 状态统计信息
        :param node_list:
        :return:
        """

        def _get_node_agent_statistics_info_base(_node: types.TreeNode) -> typing.Dict:
            """为了并发封装的一个原子函数，用于获取单节点 Agent 状态信息"""
            _host_queryset: QuerySet = base.HostQueryHelper.query_hosts_base(node_list=[_node], conditions=[])
            return {"node": _node, "agent_statistics": base.HostQueryHelper.get_agent_statistics(_host_queryset)}

        # 多线程请求，提高处理效率
        params_list: typing.List[typing.Dict] = [{"_node": node} for node in node_list]
        node_agent_statistics_infos = concurrent.batch_call(
            func=_get_node_agent_statistics_info_base, params_list=params_list
        )
        return node_agent_statistics_infos
