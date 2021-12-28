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
from celery.task import periodic_task, task

from apps.component.esbclient import client_v2
from apps.node_man import constants
from apps.node_man.models import Host, ProcessStatus
from apps.utils.periodic_task import calculate_countdown
from common.log import logger


@task(queue="default", ignore_result=True)
def update_or_create_host_agent_status(task_id, start, end):
    hosts = Host.objects.values("bk_host_id", "bk_cloud_id", "inner_ip", "node_from")[start:end]
    if not hosts:
        # 结束递归
        return

    logger.info(f"{task_id} | sync_agent_status_task: Start updating agent status. [{start}-{end}]")

    # 通过云区域：内网形式对应bk_host_id&node_from
    bk_host_id_map = {}
    node_from_map = {}

    # 生成查询参数host弄表
    query_host = []
    for host in hosts:
        # IP 为空，直接跳过
        if not host["inner_ip"]:
            continue
        bk_host_id_map[f"{host['bk_cloud_id']}:{host['inner_ip']}"] = host["bk_host_id"]
        node_from_map[f"{host['bk_cloud_id']}:{host['inner_ip']}"] = host["node_from"]
        query_host.append({"ip": host["inner_ip"], "bk_cloud_id": host["bk_cloud_id"]})

    # 查询agent状态和版本信息
    agent_status_data = client_v2.gse.get_agent_status({"hosts": query_host})
    agent_info_data = client_v2.gse.get_agent_info({"hosts": query_host})

    # 查询需要更新主机的ProcessStatus对象
    process_status_objs = ProcessStatus.objects.filter(
        name="gseagent", bk_host_id__in=bk_host_id_map.values(), source_type=ProcessStatus.SourceType.DEFAULT
    ).values("bk_host_id", "id", "status")

    # 生成bk_host_id与ProcessStatus对象的映射
    process_status_id_map = {}
    for item in process_status_objs:
        process_status_id_map[item["bk_host_id"]] = {"id": item["id"], "status": item["status"]}

    # 对查询回来的数据进行分类
    process_objs = []
    need_update_node_from_host = []
    to_be_created_status = []
    for key, host_info in agent_status_data.items():
        process_status_id = process_status_id_map.get(bk_host_id_map[key], {}).get("id")
        is_running = host_info["bk_agent_alive"] == constants.BkAgentStatus.ALIVE
        version = constants.VERSION_PATTERN.search(agent_info_data[key]["version"])

        if not process_status_id:
            # 如果不存在ProcessStatus对象需要创建
            to_be_created_status.append(
                ProcessStatus(
                    bk_host_id=bk_host_id_map[key],
                    status=constants.PROC_STATUS_DICT[host_info["bk_agent_alive"]],
                    version=version.group() if version else "",
                )
            )
        else:
            if is_running:
                status = constants.PROC_STATUS_DICT[host_info["bk_agent_alive"]]
                if node_from_map[key] == constants.NodeFrom.CMDB:
                    need_update_node_from_host.append(
                        Host(bk_host_id=bk_host_id_map[key], node_from=constants.NodeFrom.NODE_MAN)
                    )
            else:
                # 状态为0时如果节点管理为CMDB标记为未安装否则为异常
                if node_from_map[key] == constants.NodeFrom.CMDB:
                    # NOT_INSTALLED
                    status = constants.PROC_STATUS_DICT[3]
                else:
                    # TERMINATED
                    status = constants.PROC_STATUS_DICT[2]

            process_objs.append(
                ProcessStatus(
                    id=process_status_id, status=status, version=version.group() if (version and is_running) else ""
                )
            )

    # 批量更新状态&版本
    ProcessStatus.objects.bulk_update(process_objs, fields=["status", "version"])
    if need_update_node_from_host:
        Host.objects.bulk_update(need_update_node_from_host, fields=["node_from"])
    if to_be_created_status:
        ProcessStatus.objects.bulk_create(to_be_created_status)


@periodic_task(
    queue="default",
    options={"queue": "default"},
    run_every=constants.SYNC_AGENT_STATUS_TASK_INTERVAL,
)
def sync_agent_status_periodic_task():
    """
    同步agent状态
    """
    task_id = sync_agent_status_periodic_task.request.id
    logger.info(f"{task_id} | sync_agent_status_task: Start syncing host status.")
    count = Host.objects.count()
    for start in range(0, count, constants.QUERY_AGENT_STATUS_HOST_LENS):
        countdown = calculate_countdown(
            count=count / constants.QUERY_AGENT_STATUS_HOST_LENS,
            index=start / constants.QUERY_AGENT_STATUS_HOST_LENS,
            duration=constants.SYNC_AGENT_STATUS_TASK_INTERVAL,
        )
        logger.info(f"{task_id} | sync_agent_status_task after {countdown} seconds")
        update_or_create_host_agent_status.apply_async(
            (task_id, start, start + constants.QUERY_AGENT_STATUS_HOST_LENS), countdown=countdown
        )
