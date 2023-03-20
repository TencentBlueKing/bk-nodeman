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
import time
import typing

from celery.task import periodic_task, task

from apps.adapters.api.gse import GseApiHelper
from apps.node_man import constants, tools
from apps.node_man.models import Host, ProcessStatus
from apps.utils.periodic_task import calculate_countdown
from common.log import logger


@task(queue="default", ignore_result=True)
def update_or_create_proc_status(task_id, host_objs, sync_proc_list, start):
    host_info_list = []
    agent_id__host_id_map = {}
    for host_obj in host_objs:
        host_info = {
            "ip": host_obj.inner_ip or host_obj.inner_ipv6,
            "bk_cloud_id": host_obj.bk_cloud_id,
            "bk_agent_id": host_obj.bk_agent_id,
        }
        host_info_list.append(host_info)
        agent_id__host_id_map[GseApiHelper.get_agent_id(host_info)] = host_obj.bk_host_id

    for proc_name in sync_proc_list:
        past = time.time()

        agent_id__readable_proc_status_map: typing.Dict[
            str, typing.Dict[str, typing.Any]
        ] = GseApiHelper.list_proc_state(
            namespace=constants.GSE_NAMESPACE,
            proc_name=proc_name,
            labels={"proc_name": proc_name},
            host_info_list=host_info_list,
            extra_meta_data={},
        )

        logger.info(f"this get_proc_status cost {time.time() - past}s")

        process_status_objs = ProcessStatus.objects.filter(
            name=proc_name,
            bk_host_id__in=agent_id__host_id_map.values(),
            source_type=ProcessStatus.SourceType.DEFAULT,
            proc_type=constants.ProcType.PLUGIN,
            is_latest=True,
        ).values("bk_host_id", "id", "name", "status")

        host_proc_key__proc_status_map = {}
        for process_status_obj in process_status_objs:
            host_proc_key__proc_status_map[
                f"{process_status_obj['name']}:{process_status_obj['bk_host_id']}"
            ] = process_status_obj

        need_update_status = []
        need_create_status = []

        for agent_id, readable_proc_status in agent_id__readable_proc_status_map.items():
            if agent_id not in agent_id__host_id_map:
                continue
            db_proc_status = host_proc_key__proc_status_map.get(
                f'{readable_proc_status["name"]}:{agent_id__host_id_map[agent_id]}'
            )

            # 如果DB中进程状态为手动停止，并且同步回来的进程状态为终止，此时保持手动停止的标记，用于订阅的豁免操作
            if (
                db_proc_status
                and db_proc_status["status"] == constants.ProcStateType.MANUAL_STOP
                and readable_proc_status["status"] == constants.ProcStateType.TERMINATED
            ):
                readable_proc_status["status"] = db_proc_status["status"]

            if db_proc_status:
                # need update
                obj = ProcessStatus(
                    pk=db_proc_status["id"],
                    status=readable_proc_status["status"],
                    version=readable_proc_status["version"],
                    is_auto=readable_proc_status["is_auto"],
                )
                need_update_status.append(obj)
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
                    need_create_status.append(obj)

        ProcessStatus.objects.bulk_update(need_update_status, fields=["status", "version", "is_auto"])
        ProcessStatus.objects.bulk_create(need_create_status)
        logger.info(f"{task_id} | Sync process status start flag: {start} complete")


@periodic_task(
    queue="default",
    options={"queue": "default"},
    run_every=constants.SYNC_PROC_STATUS_TASK_INTERVAL,
)
def sync_proc_status_periodic_task():
    sync_proc_list = tools.PluginV2Tools.fetch_head_plugins()
    task_id = sync_proc_status_periodic_task.request.id
    host_queryset = Host.objects.all()
    count = host_queryset.count()
    logger.info(f"{task_id} | sync host proc status... host_count={count}.")

    for start in range(0, count, constants.QUERY_PROC_STATUS_HOST_LENS):
        countdown = calculate_countdown(
            count=count / constants.QUERY_PROC_STATUS_HOST_LENS,
            index=start / constants.QUERY_PROC_STATUS_HOST_LENS,
            duration=constants.SYNC_PROC_STATUS_TASK_INTERVAL,
        )
        logger.info(f"{task_id} | sync host proc status after {countdown} seconds")

        # (task_id, hosts[start: start + constants.QUERY_PROC_STATUS_HOST_LENS], sync_proc_list, start)
        # TODO 这里需要区分 GSE 版本，(区分方式：灰度业务 or 灰度接入点) -> 使用 V2 API，其他情况 -> 使用 V1 API
        update_or_create_proc_status.apply_async(
            (task_id, host_queryset[start : start + constants.QUERY_PROC_STATUS_HOST_LENS], sync_proc_list, start),
            countdown=countdown,
        )

    logger.info(f"{task_id} | sync host proc status complete.")
