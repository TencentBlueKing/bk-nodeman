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
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy

from celery.task import periodic_task, task
from django.conf import settings
from django.core.cache import cache

from apps.component.esbclient import client_v2
from apps.node_man import constants
from apps.node_man.handlers import cmdb
from apps.utils.periodic_task import calculate_countdown
from common.log import logger


def format_biz_topo(biz_topo: dict) -> dict:
    """
    格式化业务拓扑并获取业务节点列表
    :param biz_topo: 业务拓扑
    :return
    {
        "biz_format_topo": {
            "name": "biz_name",
            "id": 1,
            "type": "biz",
            "child": []
        },
        "biz_nodes": [{"name": "biz_name", "id": 1, "type": "biz", "path": "biz"}]
    }
    """
    bk_biz_id = biz_topo["bk_inst_id"]

    biz_topo_copy = deepcopy(biz_topo)
    biz_topo_copy["path"] = [biz_topo_copy["bk_inst_name"]]

    biz_nodes = []
    stack = [biz_topo_copy]
    while stack:
        cur_node = stack.pop()
        cur_node.update(
            {
                "bk_biz_id": bk_biz_id,
                "name": cur_node.pop("bk_inst_name"),
                "id": cur_node.pop("bk_inst_id"),
                "type": cur_node.pop("bk_obj_id"),
                "children": cur_node.pop("child"),
            }
        )
        # 防止多业务情况下，不同业务下节点id重复，生成一个唯一id
        cur_node["biz_inst_id"] = f"biz:{cur_node['bk_biz_id']}:obj:{cur_node['type']}:id:{cur_node['id']}"

        # 保存topo路径
        node_path_list = cur_node.pop("path")
        cur_node["path"] = " / ".join(node_path_list)

        # 线性化保存业务节点
        biz_nodes.append(
            {
                "bk_biz_id": bk_biz_id,
                "name": cur_node["name"],
                "id": cur_node["id"],
                "type": cur_node["type"],
                "path": " / ".join(node_path_list),
                "biz_inst_id": cur_node["biz_inst_id"],
                "bk_obj_id": cur_node["type"],
                "bk_inst_id": cur_node["id"],
                "bk_inst_name": cur_node["name"],
            }
        )

        for child_node in cur_node.get("children", []):
            child_node["path"] = node_path_list + [child_node["bk_inst_name"]]
            stack.append(child_node)

    biz_nodes.sort(key=lambda node: node["path"])
    return {"biz_format_topo": biz_topo_copy, "biz_nodes": biz_nodes}


@task(queue="default", ignore_result=True)
def get_and_cache_format_biz_topo(bk_biz_id: int) -> dict:
    """
    获取格式化业务拓扑并缓存
    :param bk_biz_id: 业务ID
    :return
    {
        "biz_format_topo": {
            "name": "biz_name",
            "id": 1,
            "type": "biz",
            "child": []
        },
        "biz_nodes": [{"name": "biz_name", "id": 1, "type": "biz", "path": "biz"}]
    }
    """
    cmdb_tools = cmdb.CmdbHandler()
    biz_topo_list = cmdb_tools.cmdb_biz_inst_topo(bk_biz_id)
    if not biz_topo_list:
        return {"biz_format_topo": {}, "biz_nodes": []}
    biz_topo = biz_topo_list[0]

    # 空闲机 & 故障机节点补充到业务拓扑中
    free_topo = cmdb_tools.cmdb_biz_free_inst_topo(bk_biz_id)
    logger.info(f"sync_cmdb_biz_topo_task: {free_topo}")
    free_modules = []
    if free_topo.get("module", []):
        modules = free_topo.get("module", [])
    else:
        modules = []
    for module in modules:
        free_modules.append(
            {
                "bk_obj_id": "module",
                "bk_inst_name": module["bk_module_name"],
                "bk_inst_id": module["bk_module_id"],
                "child": [],
            }
        )
    biz_topo["child"].append(
        {
            "bk_obj_id": "set",
            "bk_inst_name": free_topo.get("bk_set_name"),
            "bk_inst_id": free_topo.get("bk_set_id"),
            "child": [],
        }
    )

    format_result = format_biz_topo(biz_topo)

    cache.set(f"{bk_biz_id}_topo_cache", format_result["biz_format_topo"], 60 * 15)
    cache.set(f"{bk_biz_id}_topo_nodes", format_result["biz_nodes"], 60 * 15)

    logger.info(f"Cached {bk_biz_id} topo and nodes")

    return format_result


def cache_all_biz_topo():
    """
    多线程缓存全业务拓扑及业务拓扑节点列表
    :return:
    """
    biz_data = client_v2.cc.search_business({"fields": ["bk_biz_id"]})
    bk_biz_ids = [biz["bk_biz_id"] for biz in biz_data.get("info", []) if biz["default"] == 0]

    with ThreadPoolExecutor(max_workers=settings.CONCURRENT_NUMBER) as ex:
        tasks = [ex.submit(get_and_cache_format_biz_topo, bk_biz_id) for bk_biz_id in bk_biz_ids]
        as_completed(tasks)


@task(queue="default", ignore_result=True)
def cache_all_biz_topo_delay_task():
    task_id = sync_cmdb_biz_topo_periodic_task.request.id
    logger.warning(f"{task_id} | cache_all_biz_topo_delay_task: Sync cmdb biz topo task' cache expired")
    cache_all_biz_topo()
    logger.warning(f"{task_id} | cache_all_biz_topo_delay_task: Re-cache finished")


@periodic_task(
    queue="default",
    options={"queue": "default"},
    run_every=constants.SYNC_CMDB_BIZ_TOPO_TASK_INTERVAL,
)
def sync_cmdb_biz_topo_periodic_task():
    task_id = sync_cmdb_biz_topo_periodic_task.request.id
    logger.info(f"{task_id} | sync_cmdb_biz_topo_task: Start sync cmdb biz topo task.")

    biz_data = client_v2.cc.search_business({"fields": ["bk_biz_id"]})
    bk_biz_ids = [biz["bk_biz_id"] for biz in biz_data.get("info", []) if biz["default"] == 0]
    for index, bk_biz_id in enumerate(bk_biz_ids):
        countdown = calculate_countdown(
            count=len(bk_biz_ids), index=index, duration=constants.SYNC_CMDB_BIZ_TOPO_TASK_INTERVAL
        )
        logger.info(f"{task_id} | sync_cmdb_biz_topo_task after {countdown} seconds")
        get_and_cache_format_biz_topo.apply_async((bk_biz_id,), countdown=countdown)
    logger.info(f"{task_id} | sync_cmdb_biz_topo_task: Sync cmdb biz topo complete.")
