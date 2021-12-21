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
import time

from celery.task import periodic_task, task
from django.conf import settings

from apps.component.esbclient import client_v2
from apps.node_man import constants
from apps.node_man.models import Host, ProcessStatus
from apps.utils.periodic_task import calculate_countdown
from common.log import logger


def get_version(version_str):
    version = constants.VERSION_PATTERN.search(version_str)
    return version.group() if version else ""


def query_proc_status(proc_name, host_list):
    """
    上云接口测试
    200: 0.3s-0.4s (0.41s 0.29s 0.33s)
    500: 0.35s-0.5s (0.34s 0.42s 0.51s)
    1000: 0.5s-0.6s (0.53s 0.56s 0.61s)
    2000: 0.9s (0.91s, 0.93s)
    5000: 2s-4s (2.3s 2.2s 4.1s 4.3s)
    """
    kwargs = {
        "meta": {"namespace": "nodeman", "name": proc_name, "labels": {"proc_name": proc_name}},
        "hosts": host_list,
    }
    data = client_v2.gse.get_proc_status(kwargs)

    return data.get("proc_infos") or []


@task(queue="default", ignore_result=True)
def update_or_create_proc_status(task_id, hosts, sync_proc_list, start):
    host_ip_cloud_list = []
    bk_host_id_map = {}
    for host in hosts:
        host_ip_cloud_list.append({"ip": host.inner_ip, "bk_cloud_id": host.bk_cloud_id})
        bk_host_id_map[f"{host.inner_ip}:{host.bk_cloud_id}"] = host.bk_host_id

    for proc_name in sync_proc_list:
        past = time.time()
        proc_infos = query_proc_status(proc_name, host_ip_cloud_list)
        logger.info(f"this get_proc_status cost {time.time() - past}s")

        host_proc_status_map = {}
        for info in proc_infos:
            host_proc_status_map[f'{info["host"]["ip"]}:{info["host"]["bk_cloud_id"]}'] = {
                "version": get_version(info["version"]),
                "status": constants.PLUGIN_STATUS_DICT[info["status"]],
                "is_auto": constants.AutoStateType.AUTO if info["isauto"] else constants.AutoStateType.UNAUTO,
                "name": info["meta"]["name"],
            }

        process_status_objs = ProcessStatus.objects.filter(
            name=proc_name,
            bk_host_id__in=bk_host_id_map.values(),
            source_type=ProcessStatus.SourceType.DEFAULT,
            proc_type=constants.ProcType.PLUGIN,
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
                and db_proc_info["status"] == constants.ProcStateType.MANUAL_STOP
                and host_proc_info["status"] == constants.ProcStateType.TERMINATED
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
                    proc_type=constants.ProcType.PLUGIN,
                    bk_host_id=bk_host_id_map[host_cloud_key],
                    is_latest=True,
                )
                # 忽略无用的进程信息
                if obj.status != "UNREGISTER":
                    need_create_status.append(obj)

        ProcessStatus.objects.bulk_update(need_update_status, fields=["status", "version", "is_auto"])
        ProcessStatus.objects.bulk_create(need_create_status)
        logger.info(f"{task_id} | Sync process status start flag: {start} complate")


@periodic_task(
    queue="default",
    options={"queue": "default"},
    run_every=constants.SYNC_PROC_STATUS_TASK_INTERVAL,
)
def sync_proc_status_periodic_task():
    sync_proc_list = settings.HEAD_PLUGINS
    task_id = sync_proc_status_periodic_task.request.id
    hosts = Host.objects.all()
    count = hosts.count()
    logger.info(f"{task_id} | sync host proc status... host_count={count}.")

    for start in range(0, count, constants.QUERY_PROC_STATUS_HOST_LENS):
        countdown = calculate_countdown(
            count=count / constants.QUERY_PROC_STATUS_HOST_LENS,
            index=start / constants.QUERY_PROC_STATUS_HOST_LENS,
            duration=constants.SYNC_PROC_STATUS_TASK_INTERVAL,
        )
        logger.info(f"{task_id} | sync host proc status after {countdown} seconds")

        # (task_id, hosts[start: start + constants.QUERY_PROC_STATUS_HOST_LENS], sync_proc_list, start)
        update_or_create_proc_status.apply_async(
            (task_id, hosts[start : start + constants.QUERY_PROC_STATUS_HOST_LENS], sync_proc_list, start),
            countdown=countdown,
        )

    logger.info(f"{task_id} | sync host proc status complate.")
