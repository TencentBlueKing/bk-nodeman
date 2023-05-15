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
import typing
from collections import defaultdict

from celery.task import periodic_task, task
from django.db.models import QuerySet
from django.db.transaction import atomic

from apps.adapters.api.gse import get_gse_api_helper
from apps.core.gray.tools import GrayTools
from apps.node_man import constants
from apps.node_man.models import Host, ProcessStatus
from apps.utils.periodic_task import calculate_countdown
from common.log import logger


@task(queue="default", ignore_result=True)
def update_or_create_host_agent_status(task_id: int, host_queryset: QuerySet):
    """
    更新 Agent 状态
    :param task_id: 任务 ID
    :param host_queryset: 主机查询条件
    :return:
    """
    hosts: typing.List[typing.Dict[str, typing.Any]] = list(
        host_queryset.values(
            "bk_host_id", "bk_agent_id", "bk_cloud_id", "inner_ip", "inner_ipv6", "node_from", "ap_id", "bk_biz_id"
        )
    )
    if not hosts:
        # 结束递归
        return

    logger.info(
        f"{task_id} | sync_agent_status_task: Start updating agent status, "
        f"start Host ID -> {hosts[0]['bk_host_id']}, count -> {len(hosts)}"
    )

    # 通过管控区域：内网形式对应bk_host_id&node_from
    agent_id__host_id_map: typing.Dict[str, int] = {}
    agent_id__node_from_map: typing.Dict[str, str] = {}

    # 生成查询参数host弄表
    # 需要区分 GSE 版本，(区分方式：灰度业务 or 灰度接入点) -> 使用 V2 API，其他情况 -> 使用 V1 API
    gray_tools_instance: GrayTools = GrayTools()
    gse_version__query_hosts_map: typing.Dict[str, typing.List[typing.Dict]] = defaultdict(list)
    for host in hosts:
        gse_version = gray_tools_instance.get_host_ap_gse_version(host["bk_biz_id"], host["ap_id"])
        agent_id = get_gse_api_helper(gse_version).get_agent_id(host)
        agent_id__host_id_map[agent_id] = host["bk_host_id"]
        agent_id__node_from_map[agent_id] = host["node_from"]
        gse_version__query_hosts_map[gse_version].append(
            {
                "ip": host["inner_ip"] or host["inner_ipv6"],
                "bk_cloud_id": host["bk_cloud_id"],
                "bk_agent_id": host["bk_agent_id"],
            }
        )

    agent_id__agent_state_info_map: typing.Dict[str, typing.Dict] = {}
    for gse_version, query_hosts in gse_version__query_hosts_map.items():
        gse_api_helper = get_gse_api_helper(gse_version)
        agent_id__agent_state_info_map.update(gse_api_helper.list_agent_state(query_hosts))

    # 查询需要更新主机的ProcessStatus对象
    process_status_infos: typing.List[typing.Dict[str, typing.Any]] = ProcessStatus.objects.filter(
        name=ProcessStatus.GSE_AGENT_PROCESS_NAME,
        bk_host_id__in=agent_id__host_id_map.values(),
        source_type=ProcessStatus.SourceType.DEFAULT,
    ).values("bk_host_id", "id", "status", "version")

    recorded_host_ids: typing.Set[int] = set()
    to_be_delete_process_status_ids: typing.List[int] = []
    host_id__process_status_info_map: typing.Dict[int, typing.Dict[str, typing.Any]] = {}
    for process_status_info in process_status_infos:
        bk_host_id: int = process_status_info["bk_host_id"]
        if bk_host_id in recorded_host_ids:
            # 重复进程状态信息，暂存 id 后续删除
            to_be_delete_process_status_ids.append(process_status_info["id"])
            continue
        recorded_host_ids.add(bk_host_id)
        host_id__process_status_info_map[process_status_info["bk_host_id"]] = {
            "id": process_status_info["id"],
            "status": process_status_info["status"],
            "version": process_status_info["version"],
        }

    # 对查询回来的数据进行分类
    not_need_to_be_updated_process_status_count: int = 0
    to_be_updated_node_from_host_objs: typing.List[Host] = []
    to_be_updated_process_status_objs: typing.List[ProcessStatus] = []
    to_be_created_process_status_objs: typing.List[ProcessStatus] = []
    # TODO 实时更新 Agent 状态 - 建立主机 ID - Agent 状态信息映射关系，并返回给上层使用方，用于填充 Agent 状态
    # host_id__agent_state_info = {}
    for agent_id, agent_state_info in agent_id__agent_state_info_map.items():
        process_status_info: typing.Optional[typing.Dict[str, typing.Any]] = host_id__process_status_info_map.get(
            agent_id__host_id_map[agent_id]
        )
        is_running: bool = agent_state_info["bk_agent_alive"] == constants.BkAgentStatus.ALIVE.value
        version: str = agent_state_info["version"]

        if is_running:
            status = constants.ProcStateType.RUNNING
            if agent_id__node_from_map[agent_id] == constants.NodeFrom.CMDB:
                # Agent 状态正常的情况下，节点管控权划至节点管理
                to_be_updated_node_from_host_objs.append(
                    Host(bk_host_id=agent_id__host_id_map[agent_id], node_from=constants.NodeFrom.NODE_MAN)
                )
        else:
            # Agent 未存活时，细分异常状态
            if agent_id__node_from_map[agent_id] == constants.NodeFrom.CMDB:
                # 主机来源于 CMDB，标记为未安装
                status = constants.ProcStateType.NOT_INSTALLED
            else:
                # 主机来源于自身，标记为终止
                status = constants.ProcStateType.TERMINATED

        if not process_status_info:
            # 如果不存在 ProcessStatus 对象需要创建
            to_be_created_process_status_objs.append(
                ProcessStatus(bk_host_id=agent_id__host_id_map[agent_id], status=status, version=version)
            )
        else:
            if status == process_status_info["status"] and version == process_status_info["version"]:
                # 状态信息一致，无需更新
                # 如果后面需要添加更多的 Agent 状态属性，此处需要进行变更
                not_need_to_be_updated_process_status_count += 1
                continue
            to_be_updated_process_status_objs.append(
                ProcessStatus(id=process_status_info["id"], status=status, version=version)
            )

    logger.info(
        f"{task_id} | sync_agent_status_task: Not need to update record "
        f"count -> {not_need_to_be_updated_process_status_count}"
    )
    with atomic():
        ProcessStatus.objects.bulk_update(
            to_be_updated_process_status_objs, fields=["version", "status"], batch_size=1000
        )
        logger.info(f"{task_id} | sync_agent_status_task: Updated {len(to_be_updated_process_status_objs)} records")
        if to_be_updated_node_from_host_objs:
            Host.objects.bulk_update(to_be_updated_node_from_host_objs, fields=["node_from"], batch_size=1000)
            logger.info(f"{task_id} | sync_agent_status_task: Updated {len(to_be_updated_node_from_host_objs)} hosts")
        if to_be_created_process_status_objs:
            ProcessStatus.objects.bulk_create(to_be_created_process_status_objs, batch_size=1000)
            logger.info(f"{task_id} | sync_agent_status_task: Created {len(to_be_created_process_status_objs)} records")
        if to_be_delete_process_status_ids:
            __, delete_row_count = ProcessStatus.objects.filter(id__in=to_be_delete_process_status_ids).delete()
            logger.info(f"{task_id} | sync_agent_status_task: Deleted {delete_row_count} duplicate records")
    logger.info(
        f"{task_id} | sync_agent_status_task: Complete agent status update, "
        f"start Host ID -> {hosts[0]['bk_host_id']}, count -> {len(hosts)}"
    )


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
            (task_id, Host.objects.all()[start : start + constants.QUERY_AGENT_STATUS_HOST_LENS]), countdown=countdown
        )
