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

from celery.schedules import crontab
from celery.task import periodic_task, task

from apps.component.esbclient import client_v2
from apps.node_man import constants as const
from apps.node_man.models import GsePluginDesc, Host, ProcessStatus
from apps.utils.periodic_task import calculate_countdown
from common.log import logger


def get_version(version_str):
    version = const.VERSION_PATTERN.search(version_str)
    return version.group() if version else ""


def query_proc_status(start=0, limit=const.QUERY_PROC_STATUS_HOST_LENS):
    kwargs = {"meta": {"namespace": "nodeman"}, "page": {"start": start, "limit": limit}}

    data = client_v2.gse.sync_proc_status(kwargs)
    return data.get("count") or 0, data.get("proc_infos") or []


@task(queue="default", ignore_result=True)
def update_or_create_proc_status(task_id, sync_proc_list, start):
    logger.info(f"{task_id} | Sync process status start flag: {start}")
    _, proc_infos = query_proc_status(start)

    bk_host_ips = []
    bk_cloud_ids = []
    proc_name_list = []
    host_proc_status_map = {}

    for info in proc_infos:
        if info["meta"]["name"] not in sync_proc_list:
            continue
        if info["meta"]["name"] not in proc_name_list:
            proc_name_list.append(info["meta"]["name"])
        bk_host_ips.append(info["host"]["ip"])
        bk_cloud_ids.append(info["host"]["bk_cloud_id"])
        host_proc_status_map[f'{info["host"]["ip"]}:{info["host"]["bk_cloud_id"]}'] = {
            "version": get_version(info["version"]),
            "status": const.PLUGIN_STATUS_DICT[info["status"]],
            "is_auto": const.AutoStateType.AUTO if info["isauto"] else const.AutoStateType.UNAUTO,
            "name": info["meta"]["name"],
        }

    # 查询已存在的主机
    hosts = Host.objects.filter(inner_ip__in=bk_host_ips, bk_cloud_id__in=bk_cloud_ids).values(
        "bk_host_id", "inner_ip", "bk_cloud_id"
    )
    bk_host_id_map = {}
    for host in hosts:
        bk_host_id_map[f"{host['inner_ip']}:{host['bk_cloud_id']}"] = host["bk_host_id"]

    process_status_objs = ProcessStatus.objects.filter(
        name__in=proc_name_list,
        bk_host_id__in=bk_host_id_map.values(),
        source_type=ProcessStatus.SourceType.DEFAULT,
        proc_type=const.ProcType.PLUGIN,
        is_latest=True,
    ).values("bk_host_id", "id", "name", "status")

    host_proc_key__proc_map = {}
    for item in process_status_objs:
        host_proc_key__proc_map[f"{item['name']}:{item['bk_host_id']}"] = item

    need_update_status = []
    need_create_status = []

    for host_cloud_key, host_proc_info in host_proc_status_map.items():
        if host_cloud_key not in bk_host_id_map:
            continue
        db_proc_info = host_proc_key__proc_map.get(f'{host_proc_info["name"]}:{bk_host_id_map[host_cloud_key]}')

        # 如果DB中进程状态为手动停止，并且同步回来的进程状态为终止，此时保持手动停止的标记，用于订阅的豁免操作
        if (
            db_proc_info
            and db_proc_info["status"] == const.ProcStateType.MANUAL_STOP
            and host_proc_info["status"] == const.ProcStateType.TERMINATED
        ):
            host_proc_info["status"] = db_proc_info["status"]

        if db_proc_info:
            # need update
            obj = ProcessStatus(
                pk=db_proc_info["id"],
                status=host_proc_info["status"],
                version=host_proc_info["version"],
                is_auto=host_proc_info["is_auto"],
            )
            need_update_status.append(obj)
        else:
            # need create
            obj = ProcessStatus(
                status=host_proc_info["status"],
                version=host_proc_info["version"],
                is_auto=host_proc_info["is_auto"],
                name=host_proc_info["name"],
                source_type=ProcessStatus.SourceType.DEFAULT,
                proc_type=const.ProcType.PLUGIN,
                bk_host_id=bk_host_id_map[host_cloud_key],
                is_latest=True,
            )
            need_create_status.append(obj)

    ProcessStatus.objects.bulk_update(need_update_status, fields=["status", "version", "is_auto"])
    ProcessStatus.objects.bulk_create(need_create_status)
    logger.info(f"{task_id} | Sync process status start flag: {start} complate")


@periodic_task(
    queue="default",
    options={"queue": "default"},
    run_every=crontab(hour="*", minute="*/15", day_of_week="*", day_of_month="*", month_of_year="*"),
)
def sync_proc_status_task():
    sync_proc_list = GsePluginDesc.objects.filter(category=const.CategoryType.official).values_list("name", flat=True)
    task_id = sync_proc_status_task.request.id
    count, _ = query_proc_status(limit=1)
    logger.info(f"{task_id} | sync host proc status count={count}.")
    for start in range(0, count, const.QUERY_PROC_STATUS_HOST_LENS):
        countdown = calculate_countdown(
            count / const.QUERY_PROC_STATUS_HOST_LENS, start / const.QUERY_PROC_STATUS_HOST_LENS
        )
        logger.info(f"{task_id} | sync host proc status after {countdown} seconds")
        update_or_create_proc_status.apply_async((task_id, sync_proc_list, start), countdown=countdown)
    logger.info(f"{task_id} | sync host proc status complate.")
