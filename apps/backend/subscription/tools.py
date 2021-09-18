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
import copy
import hashlib
import logging
import math
import os
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
from itertools import groupby
from typing import Any, Dict, List, Union

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.backend.subscription import task_tools
from apps.backend.subscription.commons import get_host_by_inst, list_biz_hosts
from apps.backend.subscription.errors import (
    ConfigRenderFailed,
    MultipleObjectError,
    PipelineTreeParseError,
)
from apps.backend.utils.data_renderer import nested_render_data
from apps.component.esbclient import client_v2
from apps.exceptions import ComponentCallError
from apps.node_man import constants, models
from apps.node_man import tools as node_man_tools
from apps.utils.basic import chunk_lists, distinct_dict_list, order_dict
from apps.utils.batch_request import batch_request, request_multi_thread
from apps.utils.time_handler import strftime_local

logger = logging.getLogger("app")

client_v2.backend = True


def create_group_id(subscription: models.Subscription, instance: Dict) -> str:
    """
    创建插件组ID
    :param subscription: 订阅对象
    :param instance: CMDB实例（可能是主机实例或者服务实例）
                    {
                        "service": {
                            "id": 1
                        },
                        "host": {
                            "bk_host_id": 1
                        }
                    }
    :return: sub_1234_host_1
    """
    if subscription.object_type == subscription.ObjectType.SERVICE:
        # 服务实例
        instance_id = instance["service"]["id"]
    else:
        # 主机实例
        instance_id = instance["host"]["bk_host_id"]
    group_id = "sub_{subscription_id}_{object_type}_{instance_id}".format(
        subscription_id=subscription.id,
        object_type=subscription.object_type.lower(),
        instance_id=instance_id,
    )
    return group_id


def parse_group_id(group_id: str) -> Dict:
    """
    解析插件组ID
    :param group_id: sub_1234_host_1
    :return: {
        "subscription_id": 1234,
        "object_type": host,
        "id": 1,
    }
    """
    source_type, subscription_id, object_type, _id = group_id.split("_")
    return {
        "subscription_id": subscription_id,
        "object_type": object_type,
        "id": _id,
    }


def create_topo_node_id(topo_node: Dict) -> str:
    """
    创建拓扑节点ID
    :param topo_node: CMDB拓扑节点，如{"bk_obj_id": "biz", "bk_inst_id": 2}
    :return: "biz|2"
    """
    return "{}|{}".format(topo_node["bk_obj_id"], topo_node["bk_inst_id"])


def get_module_to_topo_dict(bk_biz_id: int) -> Dict:
    """
    获取业务的模块拓扑映射
    :param bk_biz_id: 业务ID
    :return: {
        "module|1": ["biz|2", "set|3", "module|1"]
    }
    """
    topo_tree = client_v2.cc.search_biz_inst_topo({"bk_username": "admin", "bk_biz_id": bk_biz_id})
    internal_module = client_v2.cc.get_biz_internal_module({"bk_biz_id": bk_biz_id})

    node_relations = {}

    for _internal_module in internal_module.get("module") or []:
        module_node_id = "module|{}".format(_internal_module["bk_module_id"])
        node_relations[module_node_id] = [f"biz|{bk_biz_id}", f"set|{internal_module['bk_set_id']}", module_node_id]

    queue = topo_tree
    while queue:
        topo_node = queue.pop()
        topo_node_id = create_topo_node_id(topo_node)

        if topo_node_id not in node_relations:
            node_relations[topo_node_id] = [topo_node_id]

        queue.extend(topo_node["child"])
        for child in topo_node["child"]:
            child_node_id = create_topo_node_id(child)
            node_relations[child_node_id] = node_relations[topo_node_id] + [child_node_id]

    return {
        topo_node_id: node_relations[topo_node_id]
        for topo_node_id in node_relations
        if topo_node_id.startswith("module")
    }


def create_node_id(data: Dict) -> str:
    """
    转换成字符串格式的node_id
    :param data: dict
    {
        "object_type": "HOST",
        "node_type": "TOPO",
        "bk_obj_id": "set",
        "bk_inst_id": 123
    }
    {
        "object_type": "SERVICE",
        "node_type": "INSTANCE",
        "service_instance_id": 123
    }
    {
        "object_type": "HOST",
        "node_type": "INSTANCE",
        "bk_host_id": 1213
    }
    :return: str  "host|instance|host|123"
    """
    if data["node_type"] == models.Subscription.NodeType.INSTANCE:
        _type = data["object_type"].lower()
        if _type == "host":
            _id = create_host_key(data)
        else:
            _id = data["id"]
    else:
        _type = data["bk_obj_id"]
        _id = data["bk_inst_id"]

    return "{object_type}|{node_type}|{type}|{id}".format(
        object_type=data["object_type"].lower(),
        node_type=data["node_type"].lower(),
        type=_type,
        id=_id,
    )


def parse_node_id(node_id: str) -> Dict:
    """
    解析节点ID
    :param node_id: 节点ID "host|instance|host|123"
    :return: {
        "object_type": "HOST",
        "node_type": "INSTANCE",
        "type": "host",
        "id": 123,
    }
    """
    object_type, node_type, _type, _id = node_id.split("|")
    return {
        "object_type": object_type.upper(),
        "node_type": node_type.upper(),
        "type": _type,
        "id": _id,
    }


def parse_host_key(host_key: str) -> Dict:
    """
    解析主机唯一标识
    :param host_key:  三段式：127.0.0.1-0-tencent  或者 1024
    :return: {"ip": "127.0.0.1", "bk_cloud_id": 0, "bk_supplier_id": "tencent"}
    """
    try:
        ip, bk_could_id, bk_supplier_id = host_key.split("-")
    except ValueError:
        return {"bk_host_id": int(host_key)}
    else:
        return {"ip": ip, "bk_cloud_id": bk_could_id, "bk_supplier_id": bk_supplier_id}


def create_host_key(data: Dict) -> str:
    """
    根据ip，bk_cloud_id，bk_supplier_id生成key
    :param data: {"ip": "127.0.0.1", "bk_cloud_id": 0, "bk_supplier_id": "tencent"}
    :return: str "127.0.0.1-0-tencent"
    """

    if "bk_host_id" in data:
        return data["bk_host_id"]

    if isinstance(data["bk_cloud_id"], list):
        if data["bk_cloud_id"]:
            bk_cloud_id = data["bk_cloud_id"][0]["bk_inst_id"]
        else:
            bk_cloud_id = constants.DEFAULT_CLOUD
    else:
        bk_cloud_id = data["bk_cloud_id"]

    return "{}-{}-{}".format(data.get("bk_host_innerip") or data.get("ip"), bk_cloud_id, constants.DEFAULT_SUPPLIER_ID)


def find_host_biz_relations(bk_host_ids: List[int]) -> Dict:
    """
    查询主机所属拓扑关系
    :param bk_host_ids: 主机ID列表 [1, 2, 3]
    :return: 主机所属拓扑关系
    [
        {
          "bk_biz_id": 3,
          "bk_host_id": 3,
          "bk_module_id": 59,
          "bk_set_id": 11,
          "bk_supplier_account": "0"
        }
    ]
    """
    # CMDB 限制了单次查询数量，这里需分批并发请求查询
    param_list = [
        {"bk_host_id": bk_host_ids[count * constants.QUERY_CMDB_LIMIT : (count + 1) * constants.QUERY_CMDB_LIMIT]}
        for count in range(math.ceil(len(bk_host_ids) / constants.QUERY_CMDB_LIMIT))
    ]
    host_biz_relations = request_multi_thread(client_v2.cc.find_host_biz_relations, param_list, get_data=lambda x: x)
    return host_biz_relations


def get_process_by_biz_id(bk_biz_id: int) -> Dict:
    """
    查询业务主机进程
    :param bk_biz_id: 业务ID
    :return: 主机进程
    {
        "123": {
            "java": {...}
        }
    }
    """
    try:
        params = {"bk_biz_id": int(bk_biz_id), "with_name": True}
        result = batch_request(client_v2.cc.list_service_instance_detail, params)
    except (TypeError, ComponentCallError):
        logger.warning(f"Failed to list_service_instance_detail with biz_id={bk_biz_id}")
        service_instances = []
    else:
        service_instances = result

    host_processes = defaultdict(dict)

    for service_instance in service_instances:
        for process in service_instance.get("process_instances") or []:
            process["process"].update(process["relation"])
            bk_host_id = process["relation"]["bk_host_id"]
            bk_func_name = process["process"]["bk_func_name"]
            host_processes[bk_host_id][bk_func_name] = process["process"]

    return host_processes


def get_modules_by_inst_list(inst_list, module_to_topo):
    module_ids = set()
    no_module_inst_list = set()
    # 先查询出模块
    for inst in inst_list:
        if inst["bk_obj_id"] == "module":
            module_ids.add(int(inst["bk_inst_id"]))
        else:
            no_module_inst_list.add(create_topo_node_id(inst))

    for module_node_id in module_to_topo:
        if set(module_to_topo[module_node_id]).intersection(no_module_inst_list):
            module_ids.add(int(module_node_id.split("|")[1]))
    return module_ids, no_module_inst_list


def get_service_instance_by_inst(bk_biz_id, inst_list, module_to_topo):
    module_ids, no_module_inst_list = get_modules_by_inst_list(inst_list, module_to_topo)
    params = {"bk_biz_id": int(bk_biz_id), "with_name": True}

    service_instances = batch_request(client_v2.cc.list_service_instance_detail, params, sort="id")

    service_instances = [
        service_instance for service_instance in service_instances if service_instance["bk_module_id"] in module_ids
    ]

    return service_instances


def get_service_instance_by_ids(bk_biz_id, ids):
    """
    根据服务实例id获取服务实例详情
    :param bk_biz_id: int 业务id
    :param ids: list 服务实例id
    :return:
    """
    params = {
        "bk_biz_id": int(bk_biz_id),
        "with_name": True,
        "service_instance_ids": ids,
    }

    result = batch_request(client_v2.cc.list_service_instance_detail, params)
    return result


def search_business(condition, start=0):
    kwargs = {"fields": ["bk_biz_id", "bk_biz_name"], "page": {"start": start, "limit": constants.QUERY_BIZ_LENS}}
    kwargs.update(condition)
    biz_data = client_v2.cc.search_business(kwargs)
    biz_count = biz_data.get("count", 0)
    bizs = biz_data.get("info") or []

    if biz_count > constants.QUERY_BIZ_LENS + start:
        bizs += search_business(condition, start + constants.QUERY_BIZ_LENS)

    bizs.append({"bk_biz_id": settings.BK_CMDB_RESOURCE_POOL_BIZ_ID, "bk_biz_name": "资源池"})
    return bizs


def fetch_biz_info(condition):
    all_biz = search_business(condition)
    biz_map = {}
    for biz in all_biz:
        biz_map[biz["bk_biz_id"]] = biz

    return biz_map


def get_host_detail_by_template(bk_obj_id, template_info_list: list, bk_biz_id: int = None):
    """
    根据集群模板ID/服务模板ID获得主机的详细信息
    :param bk_obj_id: 模板类型
    :param template_info_list: 模板信息列表
    :param bk_biz_id: 业务ID
    :return: 主机列表信息
    """
    if not template_info_list:
        return []

    fields = constants.FIND_HOST_BY_TEMPLATE_FIELD

    if bk_obj_id == models.Subscription.NodeType.SERVICE_TEMPLATE:
        # 服务模板
        call_func = client_v2.cc.find_host_by_service_template
        template_ids = [info["bk_inst_id"] for info in template_info_list]
        host_info_result = batch_request(
            call_func, dict(bk_service_template_ids=template_ids, bk_biz_id=bk_biz_id, fields=fields)
        )
    else:
        # 集群模板
        call_func = client_v2.cc.find_host_by_set_template
        template_ids = [info["bk_inst_id"] for info in template_info_list]
        host_info_result = batch_request(
            call_func, dict(bk_set_template_ids=template_ids, bk_biz_id=bk_biz_id, fields=fields)
        )

    return host_info_result


def get_service_instances_by_template(bk_obj_id, template_info_list: list, bk_biz_id: int = None):
    """
    根据集群模板ID/服务模板ID获得服务实例列表
    :param bk_obj_id: 模板类型
    :param template_info_list: 模板信息列表
    :param bk_biz_id: 业务ID
    :return: 服务实例列表
    """
    if not template_info_list:
        return []

    template_ids = [info["bk_inst_id"] for info in template_info_list]

    if bk_obj_id == models.Subscription.NodeType.SERVICE_TEMPLATE:
        # 服务模板下的服务实例
        call_func = client_v2.cc.find_host_by_service_template
        params = dict(
            bk_service_template_ids=template_ids, bk_biz_id=int(bk_biz_id), fields=("bk_host_id", "bk_cloud_id")
        )
    else:
        # 集群模板下的服务实例
        call_func = client_v2.cc.find_host_by_set_template
        params = dict(bk_set_template_ids=template_ids, bk_biz_id=int(bk_biz_id), fields=("bk_host_id", "bk_cloud_id"))
    host_info_result = batch_request(call_func, params)
    bk_host_ids = [inst["bk_host_id"] for inst in host_info_result]
    all_service_instances = batch_request(client_v2.cc.list_service_instance_detail, params)
    service_instances = [instance for instance in all_service_instances if instance["bk_host_id"] in bk_host_ids]

    return service_instances


def get_host_detail(host_info_list: list, bk_biz_id: int = None):
    """
    获取主机详情
    :param bk_biz_id: 业务ID
    :param host_info_list: list 主机部分信息
    # 两种主机格式只能取其中一种
    [{
        "ip": "127.0.0.1",
        "bk_cloud_id": "0",
        "bk_supplier_id": "0"
    },
    # 或者
    {
        "bk_host_id": 1
    }]
    :return: list 主机详细信息
    """
    if not host_info_list:
        return []

    host_details = []

    # 仅支持一种主机格式
    first_host_info = host_info_list[0]
    if "instance_info" in first_host_info:
        # 当已存在instance_info时，不到 CMDB 查询，用于新安装AGENT的场景
        return [host.get("instance_info", {}) for host in host_info_list]

    if "bk_host_id" in first_host_info:
        cond = {
            "host_property_filter": {
                "condition": "AND",
                "rules": [
                    {"field": "bk_host_id", "operator": "in", "value": [host["bk_host_id"] for host in host_info_list]}
                ],
            }
        }
    elif "ip" in first_host_info and "bk_cloud_id" in first_host_info:
        cond = {
            "host_property_filter": {
                "condition": "OR",
                "rules": [
                    {
                        "condition": "AND",
                        "rules": [
                            {"field": "bk_host_innerip", "operator": "equal", "value": host["ip"]},
                            {"field": "bk_cloud_id", "operator": "equal", "value": host["bk_cloud_id"]},
                        ],
                    }
                    for host in host_info_list
                ],
            }
        }
    else:
        # 如果不满足 bk_host_id / ip & bk_cloud_id 的传入格式，此时直接返回空列表，表示查询不到任何主机
        # 说明：
        #   1. list_hosts_without_biz 无需业务进行全量查询，无效传参格式会匹配单业务或全业务（不传bk_biz_id）主机
        #   2. 无有效 ip 在后续执行 create_host_key 获取 bk_cloud_id 也会 KeyError
        #   3. 综上所述，提前返回可以减少无效执行逻辑及网络IO
        return []

    hosts = list_biz_hosts(bk_biz_id, cond, "list_hosts_without_biz")
    bk_host_ids = []
    bk_cloud_ids = []
    for host in hosts:
        bk_host_ids.append(host["bk_host_id"])
        bk_cloud_ids.append(host["bk_cloud_id"])

    host_relations = find_host_biz_relations(list(set(bk_host_ids)))
    host_biz_map = {}
    for host in host_relations:
        host_biz_map[host["bk_host_id"]] = host["bk_biz_id"]

    cloud_id_name_map = models.Cloud.cloud_id_name_map()

    # 需要将资源池移除
    all_biz_id = list(set(host_biz_map.values()) - {settings.BK_CMDB_RESOURCE_POOL_BIZ_ID})
    all_biz_info = fetch_biz_info({"condition": {"bk_biz_id": {"$in": all_biz_id}}})

    host_key_dict = {}
    host_id_dict = {}
    for _host in hosts:
        _host["bk_biz_id"] = host_biz_map[_host["bk_host_id"]]
        _host["bk_biz_name"] = (
            all_biz_info.get(_host["bk_biz_id"], {}).get("bk_biz_name", "")
            if _host["bk_biz_id"] != settings.BK_CMDB_RESOURCE_POOL_BIZ_ID
            else "资源池"
        )
        _host["bk_cloud_name"] = (
            cloud_id_name_map.get(_host["bk_cloud_id"], "")
            if _host["bk_cloud_id"] != constants.DEFAULT_CLOUD
            else "直连区域"
        )
        host_key = f'{_host["bk_host_innerip"]}-{_host["bk_cloud_id"]}-{constants.DEFAULT_SUPPLIER_ID}'
        host_key_dict[host_key] = _host
        host_id_dict[_host["bk_host_id"]] = _host

    for host_info in host_info_list:
        if "bk_host_id" in host_info:
            if host_info["bk_host_id"] in host_id_dict:
                host_details.append(host_id_dict[host_info["bk_host_id"]])
        else:
            host_key = create_host_key(host_info)
            if host_key in host_key_dict:
                host_details.append(host_key_dict[host_key])

    return host_details


def add_host_module_info(host_biz_relations, instances):
    """
    增加主机的模块信息（为降低圈复杂度所写）
    :param host_biz_relations: 主机的业务相关信息
    :param instances: 目标信息，模块信息将保存到这里
    :return: instances
    """

    bk_host_module_map_id = {}
    for relation in host_biz_relations:
        if relation["bk_host_id"] not in bk_host_module_map_id:
            bk_host_module_map_id[relation["bk_host_id"]] = [relation["bk_module_id"]]
        else:
            bk_host_module_map_id[relation["bk_host_id"]].append(relation["bk_module_id"])

    for instance in instances:
        if "module" not in instance["host"]:
            instance["host"]["module"] = bk_host_module_map_id.get(instance["host"]["bk_host_id"])
    return instances


def check_instances_object_type(nodes):
    """
    确认实例的object_type是否都一致
    :param nodes: 实例
    :return: object_type 集合
    """
    bk_obj_id_set = {node["bk_obj_id"] for node in nodes}

    if len(bk_obj_id_set) > 1:
        raise MultipleObjectError
    return bk_obj_id_set


def set_template_scope_nodes(scope):
    """
    将模板scope中的nodes重置为拓扑
    """
    # 现在search_module同时返回集群模板ID和服务模板ID
    params = {"bk_biz_id": int(scope["bk_biz_id"])}
    modules_info = batch_request(client_v2.cc.search_module, params)
    template_ids = [node["bk_inst_id"] for node in scope["nodes"]]
    if scope["node_type"] == models.Subscription.NodeType.SERVICE_TEMPLATE:
        # 转化服务模板为node
        scope["nodes"] = [
            {"bk_inst_id": node["bk_module_id"], "bk_obj_id": "module"}
            for node in modules_info
            if node["service_template_id"] in template_ids
        ]
    else:
        # 转化集群模板为node
        scope["nodes"] = [
            {"bk_inst_id": node["bk_module_id"], "bk_obj_id": "module"}
            for node in modules_info
            if node["set_template_id"] in template_ids
        ]
    return scope["nodes"]


def get_host_relation(bk_biz_id, nodes):
    data = []
    hosts = get_host_by_inst(bk_biz_id, nodes)

    host_biz_relations = find_host_biz_relations([_host["bk_host_id"] for _host in hosts])

    relations = defaultdict(lambda: defaultdict(list))
    for item in host_biz_relations:
        relations[item["bk_host_id"]]["bk_module_ids"].append(item["bk_module_id"])
        relations[item["bk_host_id"]]["bk_set_ids"].append(item["bk_set_id"])

    biz_info = fetch_biz_info({"condition": {"bk_biz_id": bk_biz_id}})

    for host in hosts:
        host["bk_biz_id"] = bk_biz_id
        host["bk_biz_name"] = biz_info[bk_biz_id]["bk_biz_name"]
        host["module"] = relations[host["bk_host_id"]]["bk_module_ids"]
        host["set"] = relations[host["bk_host_id"]]["bk_set_ids"]
        data.append(host)

    return data


def support_multi_biz(get_instances_by_scope_func):
    """支持scope多范围"""

    @wraps(get_instances_by_scope_func)
    def wrapper(scope: Dict[str, Union[Dict, Any]]) -> Dict[str, Dict[str, Union[Dict, Any]]]:
        if scope.get("bk_biz_id") is not None:
            return get_instances_by_scope_func(scope)
        # 兼容只传bk_host_id的情况
        if (
            scope["object_type"] == models.Subscription.ObjectType.HOST
            and scope["node_type"] == models.Subscription.NodeType.INSTANCE
        ):
            if None in [node.get("bk_biz_id") for node in scope["nodes"]]:
                return get_instances_by_scope_func(scope)

        instance_id_info_map = {}
        nodes = sorted(scope["nodes"], key=lambda node: node["bk_biz_id"])
        params_list = [
            {
                "scope": {
                    "bk_biz_id": bk_biz_id,
                    "object_type": scope["object_type"],
                    "node_type": scope["node_type"],
                    "nodes": list(nodes),
                }
            }
            for bk_biz_id, nodes in groupby(nodes, key=lambda x: x["bk_biz_id"])
        ]
        results = request_multi_thread(get_instances_by_scope_func, params_list, get_data=lambda x: [x])
        for result in results:
            instance_id_info_map.update(result)
        return instance_id_info_map

    return wrapper


@support_multi_biz
def get_instances_by_scope(scope: Dict[str, Union[Dict, int, Any]]) -> Dict[str, Dict[str, Union[Dict, Any]]]:
    """
    获取范围内的所有主机
    :param scope: dict {
        "bk_biz_id": 2,
        "object_type": "SERVICE",
        "node_type": "TOPO",
        "need_register": False, // 是否需要注册到CMDB
        "nodes": [
            // SERVICE-INSTANCE 待补充
            // HOST-TOPO
            {
                "bk_inst_id": 33,   // 节点实例ID
                "bk_obj_id": "module",  // 节点对象ID
            },
            // HOST-INSTANCE
            {
                "ip": "127.0.0.1",
                "bk_cloud_id": 0,
                "bk_supplier_id": 0,
                "instance_info": {}  // 注册到CMDB的主机信息
            },
            {
                'bk_host_id': 1,
            }
        ]
    }
    :return: dict {
        "host|instance|host|xxxx": {...},
        "host|instance|host|yyyy": {...},
    }
    """
    instances = []
    bk_biz_id = scope["bk_biz_id"]
    if bk_biz_id:
        module_to_topo = get_module_to_topo_dict(bk_biz_id)
    else:
        module_to_topo = {}

    nodes = scope["nodes"]
    if not nodes:
        # 兼容节点为空的情况
        return {}

    need_register = scope.get("need_register", False)
    # 按照拓扑查询
    if scope["node_type"] == models.Subscription.NodeType.TOPO:
        if scope["object_type"] == models.Subscription.ObjectType.HOST:
            instances.extend([{"host": inst} for inst in get_host_relation(bk_biz_id, nodes)])
        else:
            # 补充服务实例中的信息
            instances.extend(
                [{"service": inst} for inst in get_service_instance_by_inst(bk_biz_id, nodes, module_to_topo)]
            )

    # 按照实例查询
    elif scope["node_type"] == models.Subscription.NodeType.INSTANCE:
        if scope["object_type"] == models.Subscription.ObjectType.HOST:
            instances.extend([{"host": inst} for inst in get_host_detail(nodes, bk_biz_id=bk_biz_id)])
        else:
            service_instance_ids = [int(node["id"]) for node in nodes]
            instances.extend(
                [{"service": inst} for inst in get_service_instance_by_ids(bk_biz_id, service_instance_ids)]
            )

    # 按照模板查询
    elif scope["node_type"] in [
        models.Subscription.NodeType.SERVICE_TEMPLATE,
        models.Subscription.NodeType.SET_TEMPLATE,
    ]:
        # 校验是否都选择了同一种模板
        bk_obj_id_set = check_instances_object_type(nodes)
        if scope["object_type"] == models.Subscription.ObjectType.HOST:
            # 补充实例所属模块ID
            host_biz_relations = []
            instances.extend(
                [
                    {"host": inst}
                    for inst in get_host_detail_by_template(list(bk_obj_id_set)[0], nodes, bk_biz_id=bk_biz_id)
                ]
            )
            bk_host_id_chunks = chunk_lists([instance["host"]["bk_host_id"] for instance in instances], 500)
            with ThreadPoolExecutor(max_workers=settings.CONCURRENT_NUMBER) as ex:
                tasks = [
                    ex.submit(client_v2.cc.find_host_biz_relations, dict(bk_host_id=chunk, bk_biz_id=bk_biz_id))
                    for chunk in bk_host_id_chunks
                ]
                for future in as_completed(tasks):
                    host_biz_relations.extend(future.result())

            # 转化模板为节点
            nodes = set_template_scope_nodes(scope)
            instances = add_host_module_info(host_biz_relations, instances)

        else:
            # 补充服务实例中的信息
            # 转化模板为节点，**注意不可在get_service_instance_by_inst之后才转换**
            nodes = set_template_scope_nodes(scope)
            instances.extend(
                [{"service": inst} for inst in get_service_instance_by_inst(bk_biz_id, nodes, module_to_topo)]
            )

    if not need_register:
        # 补充必要的主机或实例相关信息
        add_host_info_to_instances(bk_biz_id, scope, instances)
        add_scope_info_to_instances(nodes, scope, instances, module_to_topo)
        add_process_info_to_instances(bk_biz_id, scope, instances)

    instances_dict = {}
    data = {
        "object_type": scope["object_type"],
        "node_type": models.Subscription.NodeType.INSTANCE,
    }
    for instance in instances:
        if data["object_type"] == models.Subscription.ObjectType.HOST:
            data.update(instance["host"])
        else:
            data.update(instance["service"])
        instances_dict[create_node_id(data)] = instance

    return instances_dict


def add_host_info_to_instances(bk_biz_id: int, scope: Dict, instances: Dict):
    """
    补全实例的主机信息
    :param bk_biz_id: 业务ID
    :param scope: 目标范围
    :param instances: 实例列表
    """
    if scope["object_type"] != models.Subscription.ObjectType.SERVICE:
        # 非服务实例，不需要补充实例主机信息
        return

    host_dict = {
        host_info["bk_host_id"]: host_info
        for host_info in get_host_detail([instance["service"] for instance in instances], bk_biz_id=bk_biz_id)
    }
    for instance in instances:
        instance["host"] = host_dict[instance["service"]["bk_host_id"]]


def _add_scope_info_to_inst_instances(scope: Dict, instance: Dict):
    """
    给实例类型的实例添加目标范围信息
    :param scope: 目标范围
    :param instance: 实例
    :return:
    """
    if scope["object_type"] == models.Subscription.ObjectType.HOST:
        host = instance["host"]
        instance["scope"] = [
            {
                "ip": host["bk_host_innerip"],
                "bk_cloud_id": host["bk_cloud_id"],
                "bk_supplier_id": constants.DEFAULT_SUPPLIER_ID,
            }
        ]
    else:
        instance["scope"] = [{"service_instance_id": instance["service"]["id"]}]


def _add_scope_info_to_topo_instances(scope: Dict, instance: Dict, nodes: List[Dict], module_to_topo: Dict[str, List]):
    """
    给拓扑类型的实例添加目标范围信息
    :param scope: 目标范围
    :param instance: 实例
    :param nodes: 节点列表
    :param module_to_topo: 模块拓扑 {"module|1": ["biz|2", "set|3", "module|1"]}
    """
    instance_scope = []
    if scope["object_type"] == models.Subscription.ObjectType.HOST:
        module_ids = instance["host"]["module"]
    else:
        module_ids = [instance["service"]["bk_module_id"]]

    for topo_node in nodes:
        topo_node_id = create_topo_node_id(topo_node)
        for module_id in module_ids:
            module_node_id = create_topo_node_id({"bk_obj_id": "module", "bk_inst_id": module_id})
            if topo_node_id in module_to_topo.get(module_node_id, []):
                instance_scope.append(topo_node)
    instance["scope"] = instance_scope


def add_scope_info_to_instances(nodes: List, scope: Dict, instances: List[Dict], module_to_topo: Dict[str, List]):
    """
    给实例添加目标范围信息
    :param nodes: 节点列表
    :param scope: 目标范围
    :param instances: 实例列表
    :param module_to_topo: 模块拓扑 {"module|1": ["biz|2", "set|3", "module|1"]}
    :return:
    """
    for instance in instances:
        if scope["node_type"] == models.Subscription.NodeType.INSTANCE:
            _add_scope_info_to_inst_instances(scope, instance)
        else:
            _add_scope_info_to_topo_instances(scope, instance, nodes, module_to_topo)


def _add_process_info_to_host_instances(bk_biz_id: int, instances: List[Dict]):
    """
    给主机实例添加进程信息
    :param bk_biz_id: 业务ID
    :param instances: 实例列表
    """
    host_processes = get_process_by_biz_id(bk_biz_id)
    for instance in instances:
        bk_host_id = instance["host"]["bk_host_id"]
        instance["process"] = host_processes[bk_host_id]
        # 补全字段
        instance["service"] = None


def _add_process_info_to_service_instances(instances: List[Dict]):
    """
    给服务实例添加进程信息
    :param instances: 实例列表
    """
    for instance in instances:
        processes = {}
        for process in instance["service"].get("process_instances") or []:
            processes[process["process"]["bk_process_name"]] = process["process"]
        instance["process"] = processes
        del instance["service"]["process_instances"]


def add_process_info_to_instances(bk_biz_id: int, scope, instances):
    """
    给实例列表添加进程信息
    :param bk_biz_id: 业务
    :param scope: 目标范围
    :param instances: 实例列表
    """
    if scope["object_type"] == models.Subscription.ObjectType.HOST:
        _add_process_info_to_host_instances(bk_biz_id, instances)
    else:
        _add_process_info_to_service_instances(instances)


def get_plugin_path(plugin_name: str, target_host: models.Host, agent_config: Dict) -> Dict:
    """
    获取插件的路径配置
    :param plugin_name: 插件名称
    :param target_host: 目标主机
    :param agent_config: AGENT配置
    :return: 插件路径
    """
    setup_path = agent_config["setup_path"]
    log_path = agent_config["log_path"]
    run_path = agent_config.get("run_path")
    data_path = agent_config["data_path"]
    if target_host.os_type == constants.OsType.WINDOWS:
        path_sep = constants.WINDOWS_SEP
        dataipc = agent_config.get("dataipc", 47000)
        host_id = agent_config.get("hostid_path", "C:\\gse\\data\\host\\hostid")
        endpoint = "127.0.0.1:{}".format(dataipc)
    else:
        path_sep = constants.LINUX_SEP
        endpoint = agent_config.get("dataipc", "/var/run/ipc.state.report")
        host_id = agent_config.get("hostid_path", "/var/lib/gse/host/hostid")

    plugin_path = {
        "log_path": log_path,
        "data_path": data_path,
        "pid_path": run_path or log_path,
        "setup_path": setup_path,
        "endpoint": endpoint,
        "host_id": host_id,
        "subconfig_path": path_sep.join([setup_path, "plugins", "etc", plugin_name]),
    }
    return plugin_path


def get_all_subscription_steps_context(
    subscription_step: models.SubscriptionStep,
    instance_info: Dict,
    target_host: models.Host,
    plugin_name: str,
    agent_config: Dict,
) -> Dict:
    """
    获取订阅步骤上下文数据
    :param agent_config:
    :param SubscriptionStep subscription_step:
    :param dict instance_info: 实例信息
    :param dict target_host: 主机信息
    :param string plugin_name: 插件名称
    :return:
    """
    from apps.backend.subscription.steps import StepFactory

    context = {}
    all_step_data = {}
    for step in subscription_step.subscription.steps:
        step_context = order_dict(step.params.get("context") or {})
        step_context.update(StepFactory.get_step_manager(step).get_step_data(instance_info, target_host, agent_config))
        all_step_data[step.step_id] = step_context

    plugin_path = get_plugin_path(plugin_name, target_host, agent_config)
    # 当前step_id的数据单独拎出来，作为 shortcut
    context.update(all_step_data[subscription_step.step_id])
    context.update(cmdb_instance=instance_info, step_data=all_step_data, target=instance_info, plugin_path=plugin_path)

    # 深拷贝一份，避免原数据后续被污染
    context = copy.deepcopy(context)
    return context


def render_config_files(
    config_instances: List[models.PluginConfigInstance],
    host_status: models.ProcessStatus,
    context: Dict,
    package_obj: models.Packages,
):
    """
    根据订阅配置及步骤信息渲染配置模板
    :param package_obj: 插件包对象
    :param list[PluginConfigInstance] config_instances: 配置文件模板
    :param HostStatus host_status: 主机进程信息
    :param dict context: 上下文信息
    :return: example: [
        {
            "instance_id": config.id,
            "content": content,
            "file_path": config.template.file_path,
            "md5": md5sum,
            "name": "xxx"
        }
    ]
    """
    rendered_configs = []
    for config in config_instances:
        try:
            content = config.render_config_template(context)
        except Exception as e:
            raise ConfigRenderFailed({"name": config.template.name, "msg": e})
        # 计算配置文件的MD5
        md5 = hashlib.md5()
        md5.update(content.encode())
        md5sum = md5.hexdigest()

        rendered_config = {
            "instance_id": config.id,
            "content": content,
            "file_path": config.template.file_path,
            "md5": md5sum,
        }
        if package_obj and package_obj.plugin_desc.is_official and not config.template.is_main:
            # 官方插件的部署方式为单实例多配置，在配置模板的名称上追加 group id 即可对配置文件做唯一标识
            filename, extension = os.path.splitext(config.template.name)
            rendered_config["name"] = "{filename}_{group_id}{extension}".format(
                filename=filename, group_id=host_status.group_id, extension=extension
            )
        else:
            # 非官方插件、官方插件中的主配置文件，无需追加 group id
            # 适配模板名可渲染的形式
            rendered_config["name"] = config.render_name(config.template.name)
        if rendered_config["name"]:
            rendered_configs.append(rendered_config)
    return rendered_configs


def render_config_files_by_config_templates(
    config_templates: List[models.PluginConfigTemplate],
    process_status: models.ProcessStatus,
    context: Dict,
    package_obj: models.Packages,
):
    """
    根据订阅配置及步骤信息渲染配置模板
    :param package_obj: 插件包对象
    :param list[PluginConfigTemplate] config_templates: 配置文件模板
    :param HostStatus process_status: 主机进程信息
    :param dict context: 上下文信息
    :return: example: [
        {
            "instance_id": config.id,
            "content": content,
            "file_path": config.template.file_path,
            "md5": md5sum,
            "name": "xxx"
        }
    ]
    """
    rendered_configs = []
    for template in config_templates:
        try:
            content = template.render(context)
        except Exception as e:
            raise ConfigRenderFailed({"name": template.name, "msg": e})
        # 计算配置文件的MD5
        md5 = hashlib.md5()
        md5.update(content.encode())
        md5sum = md5.hexdigest()

        rendered_config = {
            "md5": md5sum,
            "content": content,
            "file_path": template.file_path,
        }
        if package_obj and package_obj.plugin_desc.is_official and not template.is_main:
            # 官方插件的部署方式为单实例多配置，在配置模板的名称上追加 group id 即可对配置文件做唯一标识
            filename, extension = os.path.splitext(template.name)
            rendered_config["name"] = "{filename}_{group_id}{extension}".format(
                filename=filename, group_id=process_status.group_id, extension=extension
            )
        else:
            # 非官方插件、官方插件中的主配置文件，无需追加 group id
            # 适配模板名可渲染的形式
            rendered_config["name"] = nested_render_data(template.name, context)
        if rendered_config["name"]:
            rendered_configs.append(rendered_config)
    return rendered_configs


def get_subscription_task_instance_status(instance_record, pipeline_parser, need_detail=False, need_log=False):
    """
    :param need_log:
    :param instance_record:
    :param PipelineParser pipeline_parser:
    :param need_detail: 是否需要详细信息
    :return:
    """
    # 解析 pipeline 任务树
    try:
        instance_tree = pipeline_parser.sorted_pipeline_tree[instance_record.pipeline_id]
        steps_tree = instance_tree["children"]
    except KeyError:
        raise PipelineTreeParseError()

    # 新创建的记录会覆盖前面的实例执行记录
    instance_status = {
        "task_id": instance_record.task_id,
        "record_id": instance_record.id,
        "instance_id": instance_record.instance_id,
        "create_time": strftime_local(instance_record.create_time),
        "pipeline_id": instance_record.pipeline_id,
        "start_time": None,
        "finish_time": None,
    }

    # 是否返回详细信息
    if need_detail:
        instance_status.update({"instance_info": instance_record.instance_info})
    else:
        instance_status.update({"instance_info": instance_record.simple_instance_info()})

    # 更新 Instance Pipeline 状态信息
    instance_status.update(pipeline_parser.get_node_state_with_local_dt_str(instance_record.pipeline_id))

    # 更新 Step Pipeline 状态信息
    all_steps_info = instance_record.get_all_step_data()

    finish_time = None
    # 过滤未执行的步骤
    steps_info = [step for step in all_steps_info if step["pipeline_id"]]
    for step in steps_info:
        step.update(pipeline_parser.get_node_state_with_local_dt_str(step["pipeline_id"]))
        try:
            if not step["pipeline_id"]:
                # 没有代表不执行该节点
                continue
            single_step_tree = steps_tree[step["pipeline_id"]]
            hosts_tree = list(single_step_tree["children"].values())[0]["children"]
        except Exception:
            raise PipelineTreeParseError()
        step["node_name"] = single_step_tree["name"]
        step["step_code"] = single_step_tree.get("step_code")

        # 更新 target_host 信息
        step["target_hosts"] = []
        for host_tree in list(hosts_tree.values()):
            target_host_info = {
                "pipeline_id": host_tree["id"],
                "node_name": host_tree["name"],
                "sub_steps": [],
            }
            target_host_info.update(pipeline_parser.get_node_state_with_local_dt_str(host_tree["id"]))

            # 更新 target_host 每个子步骤信息
            for single_host_step in list(host_tree["children"].values()):
                sub_step = {
                    "pipeline_id": single_host_step["id"],
                    "index": single_host_step["index"],
                    "node_name": single_host_step["name"],
                }
                sub_step.update(pipeline_parser.get_node_state_with_local_dt_str(single_host_step["id"]))

                if need_detail:
                    sub_step.update(pipeline_parser.get_node_data(single_host_step["id"]))

                if need_detail or need_log:
                    log = pipeline_parser.get_node_log(single_host_step["id"])
                    if sub_step.get("ex_data"):
                        log = f"{log}\n{sub_step['ex_data']}"
                    sub_step.update(log=log)

                target_host_info["sub_steps"].append(sub_step)
                target_host_info["sub_steps"].sort(key=lambda i: i["index"])
                target_host_info["status"] = task_tools.TaskResultTools.collect_status(target_host_info["sub_steps"])

                if sub_step.get("finish_time"):
                    finish_time = sub_step["finish_time"]

            step["target_hosts"].append(target_host_info)
            step["status"] = step["target_hosts"][0]["status"]

    instance_status["steps"] = steps_info

    status = task_tools.TaskResultTools.collect_status(instance_status["steps"])
    if status in [constants.JobStatusType.RUNNING, constants.JobStatusType.PENDING]:
        finish_time = None

    instance_status.update(status=task_tools.TaskResultTools.collect_status(instance_status["steps"]))
    if instance_status["steps"]:
        instance_status.update(
            start_time=instance_status["steps"][0]["start_time"],
            finish_time=instance_status["steps"][-1]["finish_time"] or finish_time,
        )

    return instance_status


def get_inst_record_id_host_id_map(instance_records: List[Dict[str, Any]]) -> Dict[int, int]:
    """
    根据订阅实例列表获取`订阅实例ID` 与 `host_id` 的映射关系
    :param instance_records: 订阅实例列表
    :return: `订阅实例ID` 与 `host_id` 的映射关系
    """
    bk_host_ids = []
    ip_infos = []
    host_key_inst_record_id_map: Dict[Union[str, int], int] = {}
    # 从instance_record中提取主机信息并建立`主机信息`与`订阅实例ID`映射
    for instance_record in instance_records:
        host_info = instance_record["instance_info"]["host"]
        bk_host_id = host_info.get("bk_host_id")
        if bk_host_id:
            bk_host_ids.append(bk_host_id)
            host_key_inst_record_id_map[bk_host_id] = instance_record["id"]
        else:
            ip = host_info.get("bk_host_innerip") or host_info.get("ip")
            # 兼容IP为逗号分割的多IP情况，取第一个IP
            ip_info = {"ip": ip.split(",")[0], "bk_cloud_id": host_info["bk_cloud_id"]}
            ip_infos.append(ip_info)
            host_key_inst_record_id_map[f"{ip_info['ip']}-{ip_info['bk_cloud_id']}"] = instance_record["id"]
    ip_infos = distinct_dict_list(ip_infos)

    query_exp = Q(bk_host_id__in=set(bk_host_ids))
    for ip_info in ip_infos:
        query_exp |= Q(inner_ip=ip_info["ip"], bk_cloud_id=ip_info["bk_cloud_id"])

    inst_record_id_host_id_map: Dict[int, int] = {}
    host_keys_in_db = set()
    # host_infos是instance_records包含主机信息的子集
    host_infos = models.Host.objects.filter(query_exp).values("bk_host_id", "inner_ip", "bk_cloud_id")
    for host_info in host_infos:
        inst_record_id = host_key_inst_record_id_map.get(host_info["bk_host_id"])
        if inst_record_id:
            host_keys_in_db.add(host_info["bk_host_id"])
        else:
            host_key = f"{host_info['inner_ip']}-{host_info['bk_cloud_id']}"
            inst_record_id = host_key_inst_record_id_map[host_key]
            host_keys_in_db.add(host_key)

        inst_record_id_host_id_map[inst_record_id] = host_info["bk_host_id"]

    host_key_not_in_db = set(host_key_inst_record_id_map.keys()) - host_keys_in_db
    logger.info(
        f"get_inst_record_id_host_id_map: host_key_not_in_db -> {host_key_not_in_db}, "
        f"instance_record_ids -> {[host_key_inst_record_id_map[host_key] for host_key in host_key_not_in_db]}"
    )

    return inst_record_id_host_id_map


def update_job_status(pipeline_id, result=None):
    logger.info(f"pipeline_id -> {pipeline_id} update_job_status begin.")
    instance_record = models.SubscriptionInstanceRecord.objects.filter(pipeline_id=pipeline_id).first()
    if not instance_record:
        logger.info(f"pipeline_id -> {pipeline_id} update_job_status skipped. (Pipeline 改造优化后无需更新job状态。)")
        return
    subscription_id = instance_record.subscription_id

    # 状态迁移至InstanceRecord
    task_tools.transfer_instance_record_status([subscription_id])

    job = models.Job.objects.filter(subscription_id=subscription_id).first()
    if not job:
        logger.warning(f"pipeline_id -> {pipeline_id}, subscription_id -> {subscription_id} job not exist")

    instance_record_qs = models.SubscriptionInstanceRecord.objects.filter(
        subscription_id=subscription_id, is_latest=True
    )

    job_type = job.job_type.rsplit("_")[-1]
    # agent任务需要维护JobTask
    if job_type in [constants.SubStepType.AGENT, constants.SubStepType.PROXY]:
        instance_records = instance_record_qs.values("id", "status", "instance_info")

        # 聚合相同状态instance_record_id，减少后续更新状态的DB操作
        inst_record_id_gby_status = defaultdict(list)
        for instance_record in instance_records:
            inst_record_id_gby_status[instance_record["status"]].append(instance_record["id"])

        inst_record_id_host_id_map = get_inst_record_id_host_id_map(instance_records)
        for status, inst_record_ids in inst_record_id_gby_status.items():
            models.JobTask.objects.filter(
                bk_host_id__in=[
                    inst_record_id_host_id_map[inst_record_id]
                    for inst_record_id in inst_record_ids
                    if inst_record_id in inst_record_id_host_id_map
                ]
            ).update(status=status, update_time=timezone.now())

        statuses = [instance_record["status"] for instance_record in instance_records]
    else:
        statuses = instance_record_qs.values_list("status", flat=True)

    node_man_tools.JobTools.update_job_statistics(job, dict(Counter(statuses)))

    logger.info(
        f"pipeline_id -> {pipeline_id}, subscription_id -> {subscription_id}, "
        f"job_id -> {job.id} update_job_status success."
    )
