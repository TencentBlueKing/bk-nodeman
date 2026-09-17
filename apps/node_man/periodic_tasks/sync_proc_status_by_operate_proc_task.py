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
import json
import time
import typing
from concurrent.futures import ThreadPoolExecutor, as_completed

from blueapps.contrib.celery_tools.periodic import periodic_task
from celery import current_app
from django.db.models import QuerySet
from django.db.transaction import atomic

from apps.adapters.api.gse import get_gse_api_helper
from apps.backend.api.constants import GSE_RUNNING_TASK_CODE, POLLING_INTERVAL
from apps.node_man import constants, tools
from apps.node_man.models import GlobalSettings, GsePluginDesc, Host, Packages, ProcControl, ProcessStatus
from common.log import logger
from env import constants as env_constants

QUERY_PROC_STATUS_OPERATE_PROC_AGENT_ID_LENS = 1000
QUERY_PROC_STATUS_OPERATE_PROC_POLLING_TIMEOUT = 30
SYNC_PROC_STATUS_OPERATE_PROC_MULTI_CONCURRENCY = 20


def _get_int_global_setting(key: str, default: int) -> int:
    try:
        value = int(GlobalSettings.get_config(key=key, default=default))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _get_plugin_desc(proc_name: str) -> typing.Optional[GsePluginDesc]:
    plugin_desc = GsePluginDesc.objects.filter(name=proc_name, category=constants.CategoryType.official).first()
    return plugin_desc or GsePluginDesc.objects.filter(name=proc_name).first()


def _get_proc_control_by_machine_type(
    plugin: GsePluginDesc, os_type: str, cpu_arch: str
) -> typing.Optional[ProcControl]:
    query_params = {"project": plugin.name, "os": os_type, "cpu_arch": cpu_arch}
    if not plugin.is_official:
        query_params["tenant_id"] = plugin.tenant_id
    package = Packages.objects.filter(**query_params).order_by("-id").first()
    if not package:
        return None
    try:
        return package.proc_control
    except ProcControl.DoesNotExist:
        return None


def _get_gse_control(os_type: str, package_control: ProcControl) -> typing.Dict[str, str]:
    gse_control = {
        "start_cmd": package_control.start_cmd,
        "stop_cmd": package_control.stop_cmd,
        "restart_cmd": package_control.restart_cmd,
        "reload_cmd": package_control.reload_cmd or package_control.restart_cmd,
        "kill_cmd": package_control.kill_cmd,
        "version_cmd": package_control.version_cmd,
        "health_cmd": package_control.health_cmd,
    }
    if os_type == constants.OsType.WINDOWS:
        setup_path = package_control.install_path
        gse_control = {
            "start_cmd": f"{setup_path}/{package_control.start_cmd}" if package_control.start_cmd else "",
            "stop_cmd": f"{setup_path}/{package_control.stop_cmd}" if package_control.stop_cmd else "",
            "restart_cmd": f"{setup_path}/{package_control.restart_cmd}" if package_control.restart_cmd else "",
            "reload_cmd": f"{setup_path}/{package_control.reload_cmd or package_control.restart_cmd}",
            "kill_cmd": f"{setup_path}/{package_control.kill_cmd}" if package_control.kill_cmd else "",
            "version_cmd": f"{setup_path}/{package_control.version_cmd}" if package_control.version_cmd else "",
            "health_cmd": f"{setup_path}/{package_control.health_cmd}" if package_control.health_cmd else "",
        }
    return gse_control


def _get_default_resource_policy(plugin_name: str) -> typing.Dict[str, int]:
    return {
        "cpu": (constants.PLUGIN_DEFAULT_CPU_LIMIT, 30)[plugin_name == "bkunifylogbeat"],
        "mem": constants.PLUGIN_DEFAULT_MEM_LIMIT,
    }


def _get_hosts_with_agent_id_queryset():
    return Host.objects.exclude(bk_agent_id__isnull=True).exclude(bk_agent_id="")


def _iter_host_values_by_batch(batch_size: int):
    last_bk_host_id = 0
    while True:
        host_values = list(
            _get_hosts_with_agent_id_queryset()
            .filter(bk_host_id__gt=last_bk_host_id)
            .order_by("bk_host_id")
            .values(
                "bk_host_id",
                "bk_agent_id",
                "bk_cloud_id",
                "inner_ip",
                "inner_ipv6",
                "ap_id",
                "bk_biz_id",
                "os_type",
                "cpu_arch",
            )[:batch_size]
        )
        if not host_values:
            break
        yield host_values
        last_bk_host_id = host_values[-1]["bk_host_id"]


def _build_operate_proc_query_groups(
    gse_api_helper,
    proc_name: str,
    host_values: typing.List[typing.Dict[str, typing.Any]],
) -> typing.List[typing.Dict[str, typing.Any]]:
    plugin = _get_plugin_desc(proc_name)
    if not plugin:
        logger.warning(f"sync_proc_status_by_operate_proc_task: plugin [{proc_name}] not found, skip")
        return []

    start_check_secs = GlobalSettings.get_config(
        GlobalSettings.KeyEnum.PLUGIN_PROC_START_CHECK_SECS.value,
        default=constants.DEFAULT_PLUGIN_PROC_START_CHECK_SECS,
    )
    control_cache: typing.Dict[typing.Tuple[str, str], typing.Optional[ProcControl]] = {}
    query_group_key__query_group_map: typing.Dict[str, typing.Dict[str, typing.Any]] = {}
    skipped_host_count = 0

    for host in host_values:
        os_type = host["os_type"]
        cpu_arch = host["cpu_arch"]
        machine_type = (os_type, cpu_arch)
        if machine_type not in control_cache:
            control_cache[machine_type] = _get_proc_control_by_machine_type(plugin, os_type, cpu_arch)
        package_control = control_cache[machine_type]
        if not package_control or not package_control.need_delegate:
            skipped_host_count += 1
            continue

        meta = {"namespace": constants.GSE_NAMESPACE, "name": plugin.name}
        spec = {
            "identity": {
                "index_key": "",
                "proc_name": package_control.process_name or plugin.name,
                "setup_path": package_control.install_path,
                "pid_path": package_control.pid_path,
                "user": constants.ACCOUNT_MAP.get(os_type, "root"),
            },
            "control": _get_gse_control(os_type, package_control),
            "resource": _get_default_resource_policy(plugin.name),
            "alive_monitor_policy": {
                "auto_type": plugin.auto_type,
                "start_check_secs": start_check_secs,
            },
        }
        query_group_key = json.dumps({"meta": meta, "spec": spec}, sort_keys=True)
        query_group = query_group_key__query_group_map.setdefault(
            query_group_key,
            {"meta": meta, "spec": spec, "agent_id_list": [], "agent_id__host_id_map": {}},
        )
        agent_id = gse_api_helper.get_agent_id(host)
        query_group["agent_id_list"].append(agent_id)
        query_group["agent_id__host_id_map"][agent_id] = host["bk_host_id"]

    if skipped_host_count:
        logger.warning(
            f"sync_proc_status_by_operate_proc_task: skipped {skipped_host_count} hosts for proc [{proc_name}] "
            f"because proc control is missing"
        )
    return list(query_group_key__query_group_map.values())


def _parse_operate_proc_status_content(content: typing.Any) -> typing.Dict[str, typing.Any]:
    if not content:
        return {}
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except ValueError:
            return {}
    if not isinstance(content, dict):
        return {}
    values = content.get("value") or []
    if isinstance(values, dict):
        return values
    if isinstance(values, list) and values:
        return values[0]
    return content


def _get_operate_proc_result_agent_id(result_key: str, result_info: typing.Dict[str, typing.Any], proc_name: str) -> str:
    if result_info.get("bk_agent_id"):
        return result_info["bk_agent_id"]
    content = _parse_operate_proc_status_content(result_info.get("content"))
    if content.get("bk_agent_id"):
        return content["bk_agent_id"]
    gse_proc_key_suffix = f":{constants.GSE_NAMESPACE}:{proc_name}"
    if result_key.endswith(gse_proc_key_suffix):
        return result_key[: -len(gse_proc_key_suffix)]
    return ":".join(result_key.split(":")[:2])


def _get_operate_proc_process_instance(
    content: typing.Dict[str, typing.Any], proc_name: str
) -> typing.Tuple[typing.Dict[str, typing.Any], typing.Dict[str, typing.Any]]:
    processes = content.get("process") or []
    if isinstance(processes, dict):
        processes = [processes]

    for process_info in processes:
        if not isinstance(process_info, dict):
            continue
        process_name = process_info.get("procname") or process_info.get("procName") or process_info.get("processName")
        if process_name and process_name != proc_name:
            continue

        instances = process_info.get("instance") or []
        if isinstance(instances, dict):
            instances = [instances]
        instances = [instance for instance in instances if isinstance(instance, dict)]
        if not instances:
            return process_info, {}

        running_instance = next((instance for instance in instances if instance.get("pid") != -1), None)
        return process_info, running_instance or instances[0]

    return {}, {}


def _is_operate_proc_result_handling(proc_operate_result: typing.Dict[str, typing.Any]) -> bool:
    return proc_operate_result.get("error_code") == 115 and proc_operate_result.get("error_msg") == "handling"


def _is_valid_operate_proc_result(proc_operate_result: typing.Dict[str, typing.Any]) -> bool:
    if _is_operate_proc_result_handling(proc_operate_result):
        return False
    for result_code_field in ["code", "error_code"]:
        result_code = proc_operate_result.get(result_code_field)
        if result_code is not None and result_code != 0:
            return False
    return bool(proc_operate_result.get("content"))


def _has_handling_operate_proc_result(result: typing.Dict[str, typing.Any]) -> bool:
    return any(
        isinstance(proc_operate_result, dict) and _is_operate_proc_result_handling(proc_operate_result)
        for proc_operate_result in (result.get("data") or {}).values()
    )


def _parse_operate_proc_result_to_readable_status(
    gse_api_helper,
    proc_name: str,
    result: typing.Dict[str, typing.Any],
) -> typing.Dict[str, typing.Dict[str, typing.Any]]:
    agent_id__readable_proc_status_map: typing.Dict[str, typing.Dict[str, typing.Any]] = {}
    for gse_proc_key, proc_operate_result in (result.get("data") or {}).items():
        if not isinstance(proc_operate_result, dict) or not _is_valid_operate_proc_result(proc_operate_result):
            continue
        content = _parse_operate_proc_status_content(proc_operate_result.get("content"))
        if not content:
            continue
        process_info, instance_info = _get_operate_proc_process_instance(content, proc_name)
        pid = instance_info.get("pid")
        status = (
            constants.GseProcessStatusCode.RUNNING.value
            if pid is not None and pid != -1
            else constants.GseProcessStatusCode.STOPPED.value
        )
        isauto = instance_info.get("isAuto", instance_info.get("isauto", instance_info.get("is_auto", False)))
        agent_id = _get_operate_proc_result_agent_id(gse_proc_key, proc_operate_result, proc_name)
        agent_id__readable_proc_status_map[agent_id] = {
            "version": gse_api_helper.get_version(instance_info.get("version")),
            "status": constants.PLUGIN_STATUS_DICT.get(status, constants.ProcStateType.TERMINATED),
            "is_auto": constants.AutoStateType.AUTO if isauto else constants.AutoStateType.UNAUTO,
            "name": proc_name,
        }
    return agent_id__readable_proc_status_map


def _query_proc_status_by_operate_proc_multi(
    task_id: str,
    gse_api_helper,
    proc_name: str,
    query_groups: typing.List[typing.Dict[str, typing.Any]],
) -> typing.Dict[str, typing.Dict[str, typing.Any]]:
    proc_operate_req = [
        {
            "meta": query_group["meta"],
            "op_type": constants.GseOpType.STATUS,
            "agent_id_list": query_group["agent_id_list"],
            "spec": query_group["spec"],
        }
        for query_group in query_groups
        if query_group["agent_id_list"]
    ]
    if not proc_operate_req:
        return {}

    gse_task_id = gse_api_helper.operate_proc_multi(proc_operate_req=proc_operate_req)
    polling_time = 0
    polling_timeout = _get_int_global_setting(
        key=GlobalSettings.KeyEnum.QUERY_PROC_STATUS_OPERATE_PROC_POLLING_TIMEOUT.value,
        default=QUERY_PROC_STATUS_OPERATE_PROC_POLLING_TIMEOUT,
    )
    while True:
        result = gse_api_helper.get_proc_operate_result(gse_task_id)
        if result.get("code") != GSE_RUNNING_TASK_CODE and not _has_handling_operate_proc_result(result):
            break
        if polling_time + POLLING_INTERVAL > polling_timeout:
            logger.warning(
                f"{task_id} | sync_proc_status_by_operate_proc_task: GSE operate_proc_multi status query timeout, "
                f"proc_name -> {proc_name}, gse_task_id -> {gse_task_id}"
            )
            break
        polling_time += POLLING_INTERVAL
        time.sleep(POLLING_INTERVAL)
    return _parse_operate_proc_result_to_readable_status(gse_api_helper, proc_name, result)


def _sync_proc_status_by_operate_proc_multi_for_host_batch(
    task_id: str,
    gse_api_helper,
    proc_name: str,
    host_values: typing.List[typing.Dict[str, typing.Any]],
):
    logger.info(
        f"{task_id} | sync_proc_status_by_operate_proc_task: start to sync host batch, "
        f"first_bk_host_id -> {host_values[0]['bk_host_id']}, "
        f"last_bk_host_id -> {host_values[-1]['bk_host_id']}, host_count -> {len(host_values)}"
    )
    query_groups = _build_operate_proc_query_groups(gse_api_helper, proc_name, host_values)
    agent_id__host_id_map = {}
    for query_group in query_groups:
        agent_id__host_id_map.update(query_group["agent_id__host_id_map"])
    agent_id__readable_proc_status_map = _query_proc_status_by_operate_proc_multi(
        task_id=task_id,
        gse_api_helper=gse_api_helper,
        proc_name=proc_name,
        query_groups=query_groups,
    )
    _update_proc_status_records(
        task_id=task_id,
        proc_name=proc_name,
        agent_id__host_id_map=agent_id__host_id_map,
        agent_id__readable_proc_status_map=agent_id__readable_proc_status_map,
    )


def _sync_proc_status_by_operate_proc_multi_for_host_batch_group(
    task_id: str,
    gse_api_helper,
    proc_name: str,
    host_batch_group: typing.List[typing.List[typing.Dict[str, typing.Any]]],
):
    logger.info(
        f"{task_id} | sync_proc_status_by_operate_proc_task: start to sync host batch group, "
        f"proc_name -> {proc_name}, batch_count -> {len(host_batch_group)}"
    )
    multi_concurrency = _get_int_global_setting(
        key=GlobalSettings.KeyEnum.SYNC_PROC_STATUS_OPERATE_PROC_MULTI_CONCURRENCY.value,
        default=SYNC_PROC_STATUS_OPERATE_PROC_MULTI_CONCURRENCY,
    )
    with ThreadPoolExecutor(max_workers=multi_concurrency) as executor:
        future_list = [
            executor.submit(
                _sync_proc_status_by_operate_proc_multi_for_host_batch,
                task_id,
                gse_api_helper,
                proc_name,
                host_values,
            )
            for host_values in host_batch_group
        ]
        for future in as_completed(future_list):
            future.result()


def _update_proc_status_records(
    task_id: str,
    proc_name: str,
    agent_id__host_id_map: typing.Dict[str, int],
    agent_id__readable_proc_status_map: typing.Dict[str, typing.Dict[str, typing.Any]],
):
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

        db_proc_status_info: typing.Optional[typing.Dict[str, typing.Any]] = host_proc_key__proc_status_info_map.get(
            f'{readable_proc_status["name"]}:{agent_id__host_id_map[agent_id]}'
        )

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
                not_need_to_be_updated_process_status_count += 1
                continue

            obj = ProcessStatus(
                pk=db_proc_status_info["id"],
                status=readable_proc_status["status"],
                version=readable_proc_status["version"],
                is_auto=readable_proc_status["is_auto"],
            )
            to_be_updated_process_status_objs.append(obj)
        else:
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
            if obj.status != constants.ProcStateType.UNREGISTER:
                to_be_created_process_status_objs.append(obj)

    logger.info(
        f"{task_id} | sync_proc_status_by_operate_proc_task: Not need to update record "
        f"count -> {not_need_to_be_updated_process_status_count}"
    )

    with atomic():
        if to_be_updated_process_status_objs:
            ProcessStatus.objects.bulk_update(
                to_be_updated_process_status_objs, fields=["status", "version", "is_auto"], batch_size=1000
            )
            logger.info(
                f"{task_id} | sync_proc_status_by_operate_proc_task: "
                f"Updated {len(to_be_updated_process_status_objs)} records"
            )
        if to_be_created_process_status_objs:
            ProcessStatus.objects.bulk_create(to_be_created_process_status_objs, batch_size=1000)
            logger.info(
                f"{task_id} | sync_proc_status_by_operate_proc_task: "
                f"Created {len(to_be_created_process_status_objs)} records"
            )
        if to_be_delete_process_status_ids:
            __, delete_row_count = ProcessStatus.objects.filter(id__in=to_be_delete_process_status_ids).delete()
            logger.info(
                f"{task_id} | sync_proc_status_by_operate_proc_task: Deleted {delete_row_count} duplicate records"
            )



def _sync_proc_status_by_operate_proc(
    task_id: str,
    host_queryset: QuerySet,
    sync_proc_list: typing.Optional[typing.List[str]] = None,
):
    sync_proc_list = sync_proc_list or tools.PluginV2Tools.fetch_head_plugins()
    gse_api_helper = get_gse_api_helper(env_constants.GseVersion.V2.value)

    host_queryset = host_queryset.exclude(bk_agent_id__isnull=True).exclude(bk_agent_id="")
    count = host_queryset.count()
    if count == 0:
        logger.info(f"{task_id} | sync_proc_status_by_operate_proc_task: host_count -> {count}, skip")
        return

    logger.info(
        f"{task_id} | sync_proc_status_by_operate_proc_task: start to sync host proc status, "
        f"host_count -> {count}"
    )

    for proc_name in sync_proc_list:
        logger.info(f"{task_id} | sync_proc_status_by_operate_proc_task: Start updating {proc_name} status")
        host_batch_group = []
        batch_size = _get_int_global_setting(
            key=GlobalSettings.KeyEnum.QUERY_PROC_STATUS_OPERATE_PROC_AGENT_ID_LENS.value,
            default=QUERY_PROC_STATUS_OPERATE_PROC_AGENT_ID_LENS,
        )
        multi_concurrency = _get_int_global_setting(
            key=GlobalSettings.KeyEnum.SYNC_PROC_STATUS_OPERATE_PROC_MULTI_CONCURRENCY.value,
            default=SYNC_PROC_STATUS_OPERATE_PROC_MULTI_CONCURRENCY,
        )
        for start in range(0, count, batch_size):
            host_values = list(
                host_queryset.order_by("bk_host_id")
                .values(
                    "bk_host_id",
                    "bk_agent_id",
                    "bk_cloud_id",
                    "inner_ip",
                    "inner_ipv6",
                    "ap_id",
                    "bk_biz_id",
                    "os_type",
                    "cpu_arch",
                )[start : start + batch_size]
            )
            if not host_values:
                continue
            host_batch_group.append(host_values)
            if len(host_batch_group) < multi_concurrency:
                continue
            _sync_proc_status_by_operate_proc_multi_for_host_batch_group(
                task_id=task_id,
                gse_api_helper=gse_api_helper,
                proc_name=proc_name,
                host_batch_group=host_batch_group,
            )
            host_batch_group = []

        if host_batch_group:
            _sync_proc_status_by_operate_proc_multi_for_host_batch_group(
                task_id=task_id,
                gse_api_helper=gse_api_helper,
                proc_name=proc_name,
                host_batch_group=host_batch_group,
            )
        logger.info(f"{task_id} | sync_proc_status_by_operate_proc_task: Complete [{proc_name}] status update")

    logger.info(f"{task_id} | sync_proc_status_by_operate_proc_task: sync host proc status complete")


@current_app.task(queue="default", ignore_result=True)
def update_or_create_proc_status_by_operate_proc(
    task_id: str,
    host_queryset: QuerySet,
    proc_names: typing.Optional[typing.List[str]] = None,
):
    _sync_proc_status_by_operate_proc(task_id=task_id, host_queryset=host_queryset, sync_proc_list=proc_names)


@periodic_task(
    queue="default",
    options={"queue": "default"},
    run_every=constants.SYNC_PROC_STATUS_TASK_INTERVAL,
)
def sync_proc_status_by_operate_proc_periodic_task():
    task_id = sync_proc_status_by_operate_proc_periodic_task.request.id
    _sync_proc_status_by_operate_proc(task_id=task_id, host_queryset=Host.objects.all())
