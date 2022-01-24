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
from collections import defaultdict
from datetime import datetime

from django.db.models import F, Q
from django.utils import timezone

from apps.backend.subscription.constants import TASK_TIMEOUT
from apps.utils.time_handler import strftime_local
from apps.utils.time_tools import utc2biz_str, utc_dt_str2utc_dt
from pipeline.engine.models import Data as PipelineData
from pipeline.engine.models import LogEntry as PipelineLog
from pipeline.engine.models import NodeRelationship
from pipeline.engine.models import Status as PipelineNodeStatus
from pipeline.engine.models import calculate_elapsed_time
from pipeline.service.pipeline_engine_adapter.adapter_api import (
    _better_time_or_none,
    _get_node_state,
)

"""
导入parse_pipeline函数进行pipeline数据解析
"""
logger = logging.getLogger("app")

PIPELINE_RUNNING_STATES = frozenset(["CREATED", "READY", "RUNNING", "SUSPENDED"])

# pipeline 状态与节点管理任务状态的映射
PIPELINE_STATES_MAPPING = {
    "CREATED": "PENDING",
    "READY": "PENDING",
    "RUNNING": "RUNNING",
    "SUSPENDED": "RUNNING",
    "BLOCKED": "FAILED",
    "FINISHED": "SUCCESS",
    "FAILED": "FAILED",
    "REVOKED": "FAILED",
}


class ActType(object):
    SUB_PROCESS = "SubProcess"
    START = "EmptyStartEvent"
    END = "EmptyEndEvent"
    PARALLEL = "ParallelGateway"
    CONVERGE = "ConvergeGateway"
    SERVICE = "ServiceActivity"


def get_next(pipeline, outgoing):
    if not outgoing:
        return None
    for flow in pipeline["flows"]:
        if flow == outgoing:
            target = pipeline["flows"][flow]["target"]
            break

    for act in pipeline["activities"]:
        if act == target:
            return pipeline["activities"][act]

    for gt in pipeline["gateways"]:
        if gt == target:
            return pipeline["gateways"][gt]


def parse_act(pipeline, act):
    if act["type"] == ActType.SERVICE:
        res = dict(id=act["id"], type=ActType.SERVICE, name=act["name"])
        return res, get_next(pipeline, act["outgoing"])

    elif act["type"] == ActType.SUB_PROCESS:
        res = dict(id=act["id"], type=ActType.SUB_PROCESS, name=act["name"])
        res["children"] = parse_pipeline(act["pipeline"])
        return res, get_next(pipeline, act["outgoing"])


def parse_parallel(pipeline, con):
    acts = {}
    for out in con["outgoing"]:
        nt = get_next(pipeline, out)
        acts[nt["id"]], pg = parse_act(pipeline, nt)
    return acts, get_next(pipeline, pg["outgoing"])


def parse_pipeline(pipeline):
    """
    解析pipeline数据字典
    :param pipeline: dict(activities=...,start_event=...,...)
    :return: example: {
        "c2bdb95bc72239eeade47419840923d7": {
            "index": 0,
            ...
        }
    }
    """
    children = {}
    nt = get_next(pipeline, pipeline["start_event"]["outgoing"])
    index = 0
    while nt is not None:
        if nt["type"] == ActType.PARALLEL:
            acts, a_nt = parse_parallel(pipeline, nt)
            children[nt["id"]] = dict(children=acts, type=ActType.PARALLEL)
        else:
            children[nt["id"]], a_nt = parse_act(pipeline, nt)
        children[nt["id"]]["index"] = index
        nt = a_nt
        index += 1
    return children


def check_running_records(records_queryset):
    """
    检查是否存在正在执行的记录
    :param records_queryset: SubscriptionInstanceRecord 的查询集
    :return: bool 是否存在
    """
    records = records_queryset.values_list("pipeline_id", "update_time")

    pipeline_parser = PipelineParser([record[0] for record in records])
    for pipeline_id, update_time in records:
        state = pipeline_parser.get_node_state(pipeline_id)
        if state["status"] in ["PENDING", "RUNNING"]:
            if timezone.now() - update_time >= timezone.timedelta(seconds=TASK_TIMEOUT):
                # 任务超时则不算是运行中
                continue
            return True
    return False


class PipelineParser(object):
    """
    pipeline 数据解析器
    """

    def __init__(self, pipeline_ids):
        """
        :param list pipeline_ids: pipeline树ID
        """
        self.pipeline_ids = pipeline_ids

    @property
    def pipeline_trees(self):
        if hasattr(self, "_pipeline_trees"):
            return self._pipeline_trees
        from apps.node_man.models import PipelineTree

        self._pipeline_trees = list(PipelineTree.objects.filter(id__in=self.pipeline_ids))
        return self._pipeline_trees

    @property
    def sorted_pipeline_tree(self):
        if hasattr(self, "_sorted_pipeline_tree"):
            return self._sorted_pipeline_tree
        sorted_pipeline_tree = {}
        for pipeline_tree in self.pipeline_trees:
            pipeline = pipeline_tree.tree
            if not pipeline:
                continue
            single_sorted_pipeline_tree = parse_pipeline(pipeline)

            sorted_pipeline_tree.update({pipeline["id"]: {"children": single_sorted_pipeline_tree}})
        self._sorted_pipeline_tree = sorted_pipeline_tree
        return sorted_pipeline_tree

    @staticmethod
    def _collect_descendants(tree, descendants):
        # iterate children for tree
        for identifier_code, child_tree in tree["children"].items():
            child_status = PipelineParser._map(child_tree)
            descendants[identifier_code] = child_status

            # collect children
            if child_tree["children"]:
                PipelineParser._collect_descendants(child_tree, descendants)

    @staticmethod
    def _map(tree):
        tree.setdefault("children", {})
        return {
            "id": tree["id"],
            "state": _get_node_state(tree),
            "start_time": _better_time_or_none(tree["started_time"]),
            "finish_time": _better_time_or_none(tree["archived_time"]),
            "create_time": _better_time_or_none(tree["created_time"]),
            "loop": tree["loop"],
            "retry": tree["retry"],
            "skip": tree["skip"],
        }

    @classmethod
    def get_state(cls, node_ids):
        trees = cls.get_status_tree(node_ids, max_depth=100)
        states = []
        for node_id, tree in trees.items():
            res = PipelineParser._map(tree)
            # collect all atom
            descendants = {}
            PipelineParser._collect_descendants(tree, descendants)
            res["children"] = descendants
            states.append(res)
        return states

    @classmethod
    def get_status_tree(cls, node_ids, max_depth=1):
        """
        get state and children states for a node
        :param node_ids:
        :param max_depth:
        :return:
        """
        rel_qs_not_root = NodeRelationship.objects.filter(
            Q(ancestor_id__in=node_ids, distance__lte=max_depth) & ~Q(ancestor_id=F("descendant_id"))
        ).values("ancestor_id", "descendant_id")

        descendants_mapping = {rel["descendant_id"]: rel["ancestor_id"] for rel in rel_qs_not_root}

        all_rel_qs = NodeRelationship.objects.filter(
            descendant_id__in=list(descendants_mapping.keys()), distance=1
        ).values("descendant_id", "ancestor_id")

        root_status_nodes = []
        all_status_nodes_without_root = []
        for status_node in PipelineNodeStatus.objects.filter(
            id__in=set(node_ids + [rel["descendant_id"] for rel in all_rel_qs])
        ).values():
            if status_node["id"] in node_ids:
                root_status_nodes.append(status_node)
            else:
                all_status_nodes_without_root.append(status_node)

        rel_gby_descendant_id = defaultdict(list)
        for rel in all_rel_qs:
            rel_gby_descendant_id[descendants_mapping[rel["descendant_id"]]].append(rel)

        status_node_gby_id = defaultdict(list)
        for status in all_status_nodes_without_root:
            status_node_gby_id[descendants_mapping[status["id"]]].append(status)

        all_status_tree = {}
        for root_status in root_status_nodes:
            all_status_tree[root_status["id"]] = cls.get_single_status_tree(
                rel_gby_descendant_id[root_status["id"]],
                root_status,
                status_node_gby_id[root_status["id"]],
            )

        return all_status_tree

    @classmethod
    def get_single_status_tree(cls, rel_qs, root_status, status_qs):
        node_id = root_status["id"]
        root_status["elapsed_time"] = calculate_elapsed_time(root_status["started_time"], root_status["archived_time"])
        status_map = {node_id: root_status}
        for status in status_qs:
            status["elapsed_time"] = calculate_elapsed_time(status["started_time"], status["archived_time"])
            status_map[status["id"]] = status

        relationships = [(s["ancestor_id"], s["descendant_id"]) for s in rel_qs]
        for (parent_id, child_id) in relationships:
            if parent_id not in status_map:
                return

            parent_status = status_map[parent_id]
            child_status = status_map[child_id]
            child_status.setdefault("children", {})

            parent_status.setdefault("children", {}).setdefault(child_id, child_status)

        return status_map[node_id]

    def get_all_nodes_state(self, refresh=False):
        """
        获取所有节点的执行状态
        :return: {
            "c2bdb95bc72239eeade47419840923d7": {
                "finish_time": None,
                "start_time": None,
                "status": "PENDING",
            }
        }
        """
        if hasattr(self, "_all_nodes_state") and not refresh:
            return self._all_nodes_state

        states = self.get_state(self.pipeline_ids)
        nodes_state = {}
        for state in states:
            children = state.pop("children", {})

            nodes_state.update(
                {
                    state["id"]: {
                        "finish_time": state["finish_time"],
                        "start_time": state["start_time"],
                        "create_time": state["create_time"],
                        "status": PIPELINE_STATES_MAPPING.get(state["state"], "UNKNOWN"),
                    }
                }
            )
            for key, value in children.items():
                nodes_state[key] = {
                    "finish_time": value["finish_time"],
                    "start_time": value["start_time"],
                    "create_time": state["create_time"],
                    "status": PIPELINE_STATES_MAPPING.get(value["state"], "UNKNOWN"),
                }

        self._all_nodes_state = nodes_state
        return self._all_nodes_state

    def get_node_state(self, node_id):
        """
        获取单个pipeline节点的执行详情
        :param node_id: 节点ID
        :return:
        """
        all_nodes_state = self.get_all_nodes_state()
        node_state = all_nodes_state.get(
            node_id,
            {"finish_time": None, "start_time": None, "create_time": None, "status": "PENDING"},
        )
        return node_state

    def get_node_state_with_local_dt_str(self, node_id):
        node_state = self.get_node_state(node_id)
        for time_field in ["finish_time", "start_time", "create_time"]:
            if not node_state.get(time_field):
                continue
            try:
                if isinstance(node_state[time_field], datetime):
                    node_state[time_field] = strftime_local(node_state[time_field])
                elif isinstance(node_state[time_field], str):
                    node_state[time_field] = strftime_local(utc_dt_str2utc_dt(dt_str=node_state[time_field]))
            except Exception:
                continue
        return node_state

    def get_all_nodes_log(self, refresh=False):
        """
        根据节点ID获取节点日志
        :return: {
            "c2bdb95bc72239eeade47419840923d7": "xxxx"
        }
        """
        if hasattr(self, "_all_nodes_log") and not refresh:
            return self._all_nodes_log

        node_ids = list(self.get_all_nodes_state().keys())
        logs = PipelineLog.objects.filter(node_id__in=node_ids, history_id=-1).values(
            "node_id", "logged_at", "message", "exception", "level_name"
        )
        log_gby_node_id = defaultdict(list)
        for log in logs:
            log_gby_node_id[log["node_id"]].append(log)

        log_text_by_nodes = {}
        for node_id, node_logs in log_gby_node_id.items():
            plain_entries = []
            for log in node_logs:
                log_content = "[{} {}] {}".format(utc2biz_str(log["logged_at"]), log["level_name"], log["message"])
                if log["exception"]:
                    log_content += ", exception: %s" % log["exception"]
                plain_entries.append(log_content)
            log_text_by_nodes[node_id] = "\n".join(plain_entries)
        self._all_nodes_log = log_text_by_nodes
        return self._all_nodes_log

    def get_node_log(self, node_id):
        """
        获取单个节点的日志
        :param node_id:
        :return:
        """
        log_content = self.get_all_nodes_log().get(node_id, "")
        return log_content

    def get_all_nodes_data(self, refresh=False):
        """
        根据节点ID获取节点输入输出
        :return: {
            "c2bdb95bc72239eeade47419840923d7": {
                "inputs": {},
                "outputs": {},
                "ex_data": "",
            }
        }
        """
        if hasattr(self, "_all_nodes_data") and not refresh:
            return self._all_nodes_data

        node_ids = list(self.get_all_nodes_state().keys())

        records = PipelineData.objects.filter(id__in=node_ids)

        nodes_data = {}

        for record in records:
            nodes_data[record.id] = {
                "inputs": record.inputs,
                "outputs": record.outputs,
                "ex_data": record.ex_data,
            }

        self._all_nodes_data = nodes_data
        return self._all_nodes_data

    def get_node_data(self, node_id):
        """
        获取单个节点的数据
        :param node_id:
        :return:
        """
        all_node_data = self.get_all_nodes_data()
        node_data = all_node_data.get(node_id, {"inputs": None, "outputs": None, "ex_data": None})
        return node_data
