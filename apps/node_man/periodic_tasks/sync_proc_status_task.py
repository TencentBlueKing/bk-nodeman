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

from blueapps.conf import settings
from celery.task import periodic_task, task
from django.db.models import QuerySet
from django.db.transaction import atomic

from apps.adapters.api.gse import get_gse_api_helper
from apps.core.gray.tools import GrayTools
from apps.node_man import constants, tools
from apps.node_man.models import Host, ProcessStatus
from apps.node_man.periodic_tasks.utils import query_bk_biz_ids
from apps.utils.periodic_task import calculate_countdown
from common.log import logger


@task(queue="default", ignore_result=True)
def update_or_create_proc_status(
    task_id: int,
    host_queryset: QuerySet,
    proc_names: typing.Optional[typing.List[str]] = None,
):

    hosts: typing.List[typing.Dict[str, typing.Any]] = list(
        host_queryset.values("bk_host_id", "bk_agent_id", "bk_cloud_id", "inner_ip", "inner_ipv6", "ap_id", "bk_biz_id")
    )
    if not hosts:
        logger.info(f"{task_id} | sync_proc_status_task: Empty host_info_list, skip")
        return

    logger.info(
        f"{task_id} | sync_proc_status_task: Start updating agent status, "
        f"start Host ID -> {hosts[0]['bk_host_id']}, count -> {len(hosts)}"
    )

    if proc_names is None:
        proc_names = tools.PluginV2Tools.fetch_head_plugins()

    gray_tools_instance: GrayTools = GrayTools()
    agent_id__host_id_map: typing.Dict[str, int] = {}
    # 需要区分 GSE 版本，(区分方式：灰度业务 or 灰度接入点) -> 使用 V2 API，其他情况 -> 使用 V1 API
    gse_version__query_hosts_map: typing.Dict[str, typing.List[typing.Dict]] = defaultdict(list)
    for host in hosts:
        gse_version = gray_tools_instance.get_host_ap_gse_version(host["bk_biz_id"], host["ap_id"])
        agent_id = get_gse_api_helper(gse_version).get_agent_id(host)
        agent_id__host_id_map[agent_id] = host["bk_host_id"]
        gse_version__query_hosts_map[gse_version].append(
            {
                "ip": host["inner_ip"] or host["inner_ipv6"],
                "bk_cloud_id": host["bk_cloud_id"],
                "bk_agent_id": host["bk_agent_id"],
            }
        )

    for proc_name in proc_names:

        logger.info(f"{task_id} | sync_proc_status_task: Start updating {proc_name} status")

        agent_id__readable_proc_status_map: typing.Dict[str, typing.Dict[str, typing.Any]] = {}
        for gse_version, query_hosts in gse_version__query_hosts_map.items():
            gse_api_helper = get_gse_api_helper(gse_version)
            agent_id__readable_proc_status_map.update(
                gse_api_helper.list_proc_state(
                    namespace=constants.GSE_NAMESPACE,
                    proc_name=proc_name,
                    labels={"proc_name": proc_name},
                    host_info_list=query_hosts,
                    extra_meta_data={},
                )
            )

        process_status_infos = ProcessStatus.objects.filter(
            name=proc_name,
            bk_host_id__in=agent_id__host_id_map.values(),
            source_type=ProcessStatus.SourceType.DEFAULT,
            proc_type=constants.ProcType.PLUGIN,
            is_latest=True,
        ).values("bk_host_id", "id", "name", "status", "is_auto", "version")

        recorded_host_proc_key: typing.Set[str] = set()
        to_be_delete_process_status_ids: typing.List[int] = []
        host_proc_key__proc_status_info_map: typing.Dict[str, typing.Dict[str, typing.Any]] = {}
        for process_status_info in process_status_infos:
            host_proc_key: str = f"{process_status_info['name']}:{process_status_info['bk_host_id']}"
            if host_proc_key in recorded_host_proc_key:
                # 重复进程状态信息，暂存 id 后续删除
                to_be_delete_process_status_ids.append(process_status_info["id"])
                continue
            recorded_host_proc_key.add(host_proc_key)
            host_proc_key__proc_status_info_map[host_proc_key] = process_status_info

        not_need_to_be_updated_process_status_count: int = 0
        to_be_updated_process_status_objs: typing.List[ProcessStatus] = []
        to_be_created_process_status_objs: typing.List[ProcessStatus] = []

        for agent_id, readable_proc_status in agent_id__readable_proc_status_map.items():
            if agent_id not in agent_id__host_id_map:
                continue

            # TODO 记录 Agent 非存活的主机 ID，将仍为存活状态的插件状态更新为异常
            db_proc_status_info: typing.Optional[
                typing.Dict[str, typing.Any]
            ] = host_proc_key__proc_status_info_map.get(
                f'{readable_proc_status["name"]}:{agent_id__host_id_map[agent_id]}'
            )

            # 如果DB中进程状态为手动停止，并且同步回来的进程状态为终止，此时保持手动停止的标记，用于订阅的豁免操作
            if (
                db_proc_status_info
                and db_proc_status_info["status"] == constants.ProcStateType.MANUAL_STOP
                and readable_proc_status["status"] == constants.ProcStateType.TERMINATED
            ):
                readable_proc_status["status"] = db_proc_status_info["status"]

            if db_proc_status_info:
                if all(
                    [
                        readable_proc_status["status"] == db_proc_status_info["status"],
                        readable_proc_status["version"] == db_proc_status_info["version"],
                        readable_proc_status["is_auto"] == db_proc_status_info["is_auto"],
                    ]
                ):
                    # 状态信息一致，无需更新
                    not_need_to_be_updated_process_status_count += 1
                    continue

                # need update
                obj = ProcessStatus(
                    pk=db_proc_status_info["id"],
                    status=readable_proc_status["status"],
                    version=readable_proc_status["version"],
                    is_auto=readable_proc_status["is_auto"],
                )
                to_be_updated_process_status_objs.append(obj)
            else:
                # need create
                obj = ProcessStatus(
                    status=readable_proc_status["status"],
                    version=readable_proc_status["version"],
                    is_auto=readable_proc_status["is_auto"],
                    name=readable_proc_status["name"],
                    source_type=ProcessStatus.SourceType.DEFAULT,
                    proc_type=constants.ProcType.PLUGIN,
                    bk_host_id=agent_id__host_id_map[agent_id],
                    is_latest=True,
                )
                # 忽略无用的进程信息
                if obj.status != constants.ProcStateType.UNREGISTER:
                    to_be_created_process_status_objs.append(obj)

        logger.info(
            f"{task_id} | sync_proc_status_task: Not need to update record "
            f"count -> {not_need_to_be_updated_process_status_count}"
        )

        with atomic():
            if to_be_updated_process_status_objs:
                ProcessStatus.objects.bulk_update(
                    to_be_updated_process_status_objs, fields=["status", "version", "is_auto"], batch_size=1000
                )
                logger.info(
                    f"{task_id} | sync_proc_status_task: Updated {len(to_be_updated_process_status_objs)} records"
                )
            if to_be_created_process_status_objs:
                ProcessStatus.objects.bulk_create(to_be_created_process_status_objs, batch_size=1000)
                logger.info(
                    f"{task_id} | sync_proc_status_task: Created {len(to_be_created_process_status_objs)} records"
                )
            if to_be_delete_process_status_ids:
                __, delete_row_count = ProcessStatus.objects.filter(id__in=to_be_delete_process_status_ids).delete()
                logger.info(f"{task_id} | sync_proc_status_task: Deleted {delete_row_count} duplicate records")

        logger.info(f"{task_id} | sync_proc_status_task: Complete [{proc_name}] status update")

    logger.info(
        f"{task_id} | sync_proc_status_task: Complete proc status update, "
        f"start Host ID -> {hosts[0]['bk_host_id']}, count -> {len(hosts)}"
    )


@periodic_task(
    queue="default",
    options={"queue": "default"},
    run_every=constants.SYNC_PROC_STATUS_TASK_INTERVAL,
)
def sync_proc_status_periodic_task():

    task_id = sync_proc_status_periodic_task.request.id
    sync_proc_list = tools.PluginV2Tools.fetch_head_plugins()

    # 查询所有需要同步的业务id
    bk_biz_ids = query_bk_biz_ids(task_id)
    # 若没有指定业务时，也同步资源池主机
    bk_biz_ids.append(settings.BK_CMDB_RESOURCE_POOL_BIZ_ID)

    for bk_biz_id in bk_biz_ids:

        host_queryset = Host.objects.filter(bk_biz_id=bk_biz_id)
        count = host_queryset.count()

        if count == 0:
            logger.info(f"{task_id} | sync_proc_status_task: bk_biz_id -> {bk_biz_id}, host_count -> {count}, skip")
            continue

        logger.info(f"{task_id} | sync_proc_status_task: start to sync bk_biz_id -> {bk_biz_id}, host_count -> {count}")

        for start in range(0, count, constants.QUERY_PROC_STATUS_HOST_LENS):
            countdown = calculate_countdown(
                count=count / constants.QUERY_PROC_STATUS_HOST_LENS,
                index=start / constants.QUERY_PROC_STATUS_HOST_LENS,
                duration=constants.SYNC_PROC_STATUS_TASK_INTERVAL,
            )
            logger.info(f"{task_id} | sync_proc_status_task: bk_biz_id -> {bk_biz_id}, sync after {countdown} seconds")

            # (task_id, hosts[start: start + constants.QUERY_PROC_STATUS_HOST_LENS], sync_proc_list, start)
            update_or_create_proc_status.apply_async(
                (
                    task_id,
                    host_queryset[start : start + constants.QUERY_PROC_STATUS_HOST_LENS],
                    sync_proc_list,
                ),
                countdown=countdown,
            )

        logger.info(f"{task_id} | sync_proc_status_task: sync host proc status complete")
