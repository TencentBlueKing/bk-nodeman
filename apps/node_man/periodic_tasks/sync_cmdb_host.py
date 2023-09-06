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
import math
import typing

from celery.schedules import crontab
from celery.task import periodic_task
from django.conf import settings
from django.db import transaction

from apps.backend.celery import app
from apps.component.esbclient import client_v2
from apps.core.gray.tools import GrayTools
from apps.exceptions import ComponentCallError
from apps.node_man import constants, models, tools
from apps.node_man.periodic_tasks.utils import (
    SyncHostApMapConfig,
    get_host_ap_id,
    get_sync_host_ap_map_config,
    query_bk_biz_ids,
)
from apps.utils.batch_request import batch_request
from apps.utils.concurrent import batch_call
from common.log import logger


def query_biz_hosts(bk_biz_id: int, bk_host_ids: typing.List[int]) -> typing.List[typing.Dict]:
    """
    获取业务下主机
    :param bk_biz_id: 业务ID
    :param bk_host_ids: 主机ID 列表
    :return: 主机列表
    """
    query_params = {
        "fields": constants.CC_HOST_FIELDS,
        "host_property_filter": {
            "condition": "AND",
            "rules": [{"field": "bk_host_id", "operator": "in", "value": bk_host_ids}],
        },
    }
    if bk_biz_id == settings.BK_CMDB_RESOURCE_POOL_BIZ_ID:
        query_hosts_api = client_v2.cc.list_resource_pool_hosts
    else:
        query_params["bk_biz_id"] = bk_biz_id
        query_hosts_api = client_v2.cc.list_biz_hosts

    hosts = batch_request(query_hosts_api, query_params)

    return hosts


def _list_biz_hosts(biz_id: int, start: int) -> dict:
    biz_hosts = client_v2.cc.list_biz_hosts(
        {
            "bk_biz_id": biz_id,
            "fields": constants.CC_HOST_FIELDS,
            "page": {"start": start, "limit": constants.QUERY_CMDB_LIMIT, "sort": "bk_host_id"},
        }
    )
    # 去除内网IP为空的主机
    biz_hosts["info"] = [
        host for host in biz_hosts["info"] if host.get("bk_host_innerip") or host.get("bk_host_innerip_v6")
    ]
    return biz_hosts


def _list_resource_pool_hosts(start):
    try:
        result = client_v2.cc.list_resource_pool_hosts(
            {
                "page": {"start": start, "limit": constants.QUERY_CMDB_LIMIT, "sort": "bk_host_id"},
                "fields": constants.CC_HOST_FIELDS,
            }
        )
        return result
    except ComponentCallError:
        return {"info": []}


def _bulk_update_host(hosts, extra_fields):
    update_fields = [
        "node_type",
        "bk_biz_id",
        "bk_cloud_id",
        "bk_host_name",
        "bk_addressing",
        "inner_ip",
        "outer_ip",
        "inner_ipv6",
        "outer_ipv6",
        "bk_agent_id",
        "os_type",
    ] + extra_fields
    if hosts:
        models.Host.objects.bulk_update(hosts, fields=update_fields)


def _generate_host(biz_id, host, ap_id, is_os_type_priority=False, is_sync_cmdb_host_apply_cpu_arch=False):
    os_type = tools.HostV2Tools.get_os_type(host, is_os_type_priority)
    cpu_arch = tools.HostV2Tools.get_cpu_arch(host, is_sync_cmdb_host_apply_cpu_arch, os_type=os_type)

    host_data = models.Host(
        bk_host_id=host["bk_host_id"],
        bk_agent_id=host.get("bk_agent_id"),
        bk_biz_id=biz_id,
        bk_cloud_id=host["bk_cloud_id"],
        bk_host_name=host.get("bk_host_name"),
        bk_addressing=host.get("bk_addressing") or constants.CmdbAddressingType.STATIC.value,
        inner_ip=(host.get("bk_host_innerip") or "").split(",")[0],
        outer_ip=(host.get("bk_host_outerip") or "").split(",")[0],
        inner_ipv6=(host.get("bk_host_innerip_v6") or "").split(",")[0],
        outer_ipv6=(host.get("bk_host_outerip_v6") or "").split(",")[0],
        node_from=constants.NodeFrom.CMDB,
        os_type=os_type,
        cpu_arch=cpu_arch,
        node_type=constants.NodeType.AGENT
        if host["bk_cloud_id"] == constants.DEFAULT_CLOUD
        else constants.NodeType.PAGENT,
        ap_id=ap_id,
    )

    identify_data = models.IdentityData(
        bk_host_id=host["bk_host_id"],
        auth_type=constants.AuthType.PASSWORD,
        account=constants.WINDOWS_ACCOUNT if os_type == constants.OsType.WINDOWS else constants.LINUX_ACCOUNT,
        port=constants.WINDOWS_PORT if os_type == constants.OsType.WINDOWS else settings.BKAPP_DEFAULT_SSH_PORT,
    )

    process_status_data = models.ProcessStatus(
        bk_host_id=host["bk_host_id"],
        source_type=models.ProcessStatus.SourceType.DEFAULT,
        name=models.ProcessStatus.GSE_AGENT_PROCESS_NAME,
    )

    return host_data, identify_data, process_status_data


def find_host_biz_relations(find_host_biz_ids):
    host_biz_relation = {}
    for count in range(math.ceil(len(find_host_biz_ids) / constants.QUERY_CMDB_LIMIT)):
        cc_host_biz_relations = client_v2.cc.find_host_biz_relations(
            {
                "bk_host_id": find_host_biz_ids[
                    count * constants.QUERY_CMDB_LIMIT : (count + 1) * constants.QUERY_CMDB_LIMIT
                ]
            }
        )
        for _host_biz in cc_host_biz_relations:
            host_biz_relation[_host_biz["bk_host_id"]] = _host_biz["bk_biz_id"]

    return host_biz_relation


def update_or_create_host_base(biz_id, ap_map_config, is_gse2_gray, task_id, cmdb_host_data):
    bk_host_ids = [_host["bk_host_id"] for _host in cmdb_host_data]

    # 查询节点管理已存在的主机
    exist_proxy_host_ids: typing.Set[int] = set(
        models.Host.objects.filter(bk_host_id__in=bk_host_ids, node_type=constants.NodeType.PROXY).values_list(
            "bk_host_id", flat=True
        )
    )
    exist_agent_host_ids: typing.Set[int] = set(
        models.Host.objects.filter(bk_host_id__in=bk_host_ids)
        .exclude(node_type=constants.NodeType.PROXY)
        .values_list("bk_host_id", flat=True)
    )
    host_ids_in_exist_identity_data: typing.Set[int] = set(
        models.IdentityData.objects.filter(bk_host_id__in=bk_host_ids).values_list("bk_host_id", flat=True)
    )
    host_ids_in_exist_proc_statuses: typing.Set[int] = set(
        models.ProcessStatus.objects.filter(
            bk_host_id__in=bk_host_ids,
            name=models.ProcessStatus.GSE_AGENT_PROCESS_NAME,
            source_type=models.ProcessStatus.SourceType.DEFAULT,
        ).values_list("bk_host_id", flat=True)
    )

    is_sync_cmdb_host_apply_cpu_arch = tools.HostV2Tools.is_sync_cmdb_host_apply_cpu_arch()
    is_os_type_priority = tools.HostV2Tools.is_os_type_priority()

    need_update_hosts: typing.List[models.Host] = []
    need_update_hosts_with_arch: typing.List[models.Host] = []

    need_create_hosts: typing.List[models.Host] = []
    need_create_host_identity_objs: typing.List[models.IdentityData] = []
    need_create_process_status_objs: typing.List[models.ProcessStatus] = []
    need_update_host_identity_objs: typing.List[models.IdentityData] = []

    default_ap_id = (
        constants.DEFAULT_AP_ID if models.AccessPoint.objects.count() > 1 else models.AccessPoint.objects.first().id
    )

    # 已存在的主机批量更新,不存在的主机批量创建
    for host in cmdb_host_data:
        # 兼容内网IP为空的情况
        if not (host.get("bk_host_innerip") or host.get("bk_host_innerip_v6")):
            logger.info(
                f"[sync_cmdb_host] update_or_create_host: task_id -> {task_id}, bk_biz_id -> {biz_id}, "
                f"bk_host_id -> {host['bk_host_id']} bk_host_innerip and bk_host_innerip_v6 is empty"
            )
            continue

        host_params = {
            "bk_host_id": host["bk_host_id"],
            "bk_agent_id": host.get("bk_agent_id"),
            "bk_biz_id": biz_id,
            "bk_cloud_id": host["bk_cloud_id"],
            "bk_host_name": host.get("bk_host_name"),
            "bk_addressing": host.get("bk_addressing") or constants.CmdbAddressingType.STATIC.value,
            "inner_ip": (host.get("bk_host_innerip") or "").split(",")[0],
            "outer_ip": (host.get("bk_host_outerip") or "").split(",")[0],
            "inner_ipv6": (host.get("bk_host_innerip_v6") or "").split(",")[0],
            "outer_ipv6": (host.get("bk_host_outerip_v6") or "").split(",")[0],
        }

        if host["bk_host_id"] in exist_agent_host_ids:
            host_params["os_type"] = tools.HostV2Tools.get_os_type(host, is_os_type_priority)
            host_params["node_type"] = (constants.NodeType.PAGENT, constants.NodeType.AGENT)[
                host["bk_cloud_id"] == constants.DEFAULT_CLOUD
            ]
        elif host["bk_host_id"] in exist_proxy_host_ids:
            host_params["os_type"] = constants.OsType.LINUX
            host_params["node_type"] = constants.NodeType.PROXY
        else:
            host_data, identify_data, process_status_data = _generate_host(
                biz_id,
                host,
                get_host_ap_id(
                    default_ap_id=default_ap_id,
                    bk_cloud_id=host["bk_cloud_id"],
                    ap_map_config=ap_map_config,
                    is_gse2_gray=is_gse2_gray,
                ),
                is_os_type_priority,
                is_sync_cmdb_host_apply_cpu_arch,
            )
            need_create_hosts.append(host_data)
            if identify_data.bk_host_id not in host_ids_in_exist_identity_data:
                need_create_host_identity_objs.append(identify_data)
            else:
                need_update_host_identity_objs.append(identify_data)
            if process_status_data.bk_host_id not in host_ids_in_exist_proc_statuses:
                need_create_process_status_objs.append(process_status_data)
            continue

        cpu_arch = tools.HostV2Tools.get_cpu_arch(
            host,
            is_sync_cmdb_host_apply_cpu_arch,
            get_default=False,
        )
        if is_sync_cmdb_host_apply_cpu_arch and cpu_arch:
            host_params["cpu_arch"] = cpu_arch
            need_update_hosts_with_arch.append(models.Host(**host_params))
            continue

        need_update_hosts.append(models.Host(**host_params))

    with transaction.atomic():
        _bulk_update_host(need_update_hosts, [])
        _bulk_update_host(need_update_hosts_with_arch, ["cpu_arch"])

        if need_create_hosts:
            models.Host.objects.bulk_create(need_create_hosts, batch_size=500)
        if need_create_host_identity_objs:
            models.IdentityData.objects.bulk_create(need_create_host_identity_objs, batch_size=500)
        if need_update_host_identity_objs:
            models.IdentityData.objects.bulk_update(
                need_update_host_identity_objs, fields=["auth_type", "account", "port"], batch_size=500
            )
        if need_create_process_status_objs:
            models.ProcessStatus.objects.bulk_create(need_create_process_status_objs, batch_size=500)

    return bk_host_ids


def sync_biz_incremental_hosts(
    bk_biz_id: int, ap_map_config: SyncHostApMapConfig, expected_bk_host_ids: typing.Iterable[int], is_gse2_gray: bool
):
    """
    同步业务增量主机
    :param bk_biz_id: 业务ID
    :param expected_bk_host_ids: 期望得到的主机ID列表
    :return:
    """
    logger.info(
        f"[sync_cmdb_host] sync_biz_incremental_hosts: "
        f"bk_biz_id -> {bk_biz_id}, expected_bk_host_ids -> {expected_bk_host_ids}"
    )
    expected_bk_host_ids: typing.Set[int] = set(expected_bk_host_ids)
    exists_host_ids: typing.Set[int] = set(
        models.Host.objects.filter(bk_biz_id=bk_biz_id, bk_host_id__in=expected_bk_host_ids).values_list(
            "bk_host_id", flat=True
        )
    )
    # 计算出对比本地主机缓存，增量的主机 ID
    incremental_host_ids: typing.List[int] = list(expected_bk_host_ids - exists_host_ids)
    # 尝试获取增量主机信息
    hosts: typing.List[typing.Dict] = query_biz_hosts(bk_biz_id=bk_biz_id, bk_host_ids=incremental_host_ids)
    # 更新本地缓存
    update_or_create_host_base(
        biz_id=bk_biz_id,
        ap_map_config=ap_map_config,
        is_gse2_gray=is_gse2_gray,
        task_id=f"differential_sync_biz_hosts_{bk_biz_id}",
        cmdb_host_data=hosts,
    )


def bulk_differential_sync_biz_hosts(expected_bk_host_ids_gby_bk_biz_id: typing.Dict[int, typing.Iterable[int]]):
    """
    并发同步增量主机
    :param expected_bk_host_ids_gby_bk_biz_id: 按业务ID聚合主机ID列表
    :return:
    """
    params_list: typing.List[typing.Dict] = []
    ap_map_config: SyncHostApMapConfig = get_sync_host_ap_map_config()
    for bk_biz_id, bk_host_ids in expected_bk_host_ids_gby_bk_biz_id.items():
        params_list.append(
            {
                "bk_biz_id": bk_biz_id,
                "ap_map_config": ap_map_config,
                "expected_bk_host_ids": bk_host_ids,
                "is_gse2_gray": GrayTools().is_gse2_gray(bk_biz_id=bk_biz_id),
            }
        )
    batch_call(func=sync_biz_incremental_hosts, params_list=params_list)


def _update_or_create_host(biz_id, ap_map_config: SyncHostApMapConfig, is_gse2_gray=False, start=0, task_id=None):
    if biz_id == settings.BK_CMDB_RESOURCE_POOL_BIZ_ID:
        cc_result = _list_resource_pool_hosts(start)
    else:
        cc_result = _list_biz_hosts(biz_id, start)

    host_data = cc_result.get("info") or []
    host_count = cc_result.get("count", 0)

    logger.info(
        f"[sync_cmdb_host] update_or_create_host: task_id -> {task_id}, bk_biz_id -> {biz_id}, "
        f"host_count -> {host_count}, range -> {start}-{start + constants.QUERY_CMDB_LIMIT}"
    )

    bk_host_ids = update_or_create_host_base(biz_id, ap_map_config, is_gse2_gray, task_id, host_data)

    # 递归
    if host_count > start + constants.QUERY_CMDB_LIMIT:
        bk_host_ids += _update_or_create_host(
            biz_id, ap_map_config, is_gse2_gray, start + constants.QUERY_CMDB_LIMIT, task_id=task_id
        )

    return bk_host_ids


def sync_cmdb_host(bk_biz_id=None, task_id=None):
    """
    同步cmdb主机
    """
    logger.info(f"[sync_cmdb_host] start: task_id -> {task_id}, bk_biz_id -> {bk_biz_id}")

    ap_map_config: SyncHostApMapConfig = get_sync_host_ap_map_config()

    # 记录CC所有host id
    cc_bk_host_ids = []

    if bk_biz_id:
        bk_biz_ids = [bk_biz_id]
    else:
        # 查询所有需要同步的业务id
        bk_biz_ids = query_bk_biz_ids(task_id)
        # 若没有指定业务时，也同步资源池主机
        bk_biz_ids.append(settings.BK_CMDB_RESOURCE_POOL_BIZ_ID)

    for bk_biz_id in bk_biz_ids:
        cc_bk_host_ids += _update_or_create_host(
            bk_biz_id,
            ap_map_config=ap_map_config,
            is_gse2_gray=GrayTools().is_gse2_gray(bk_biz_id=bk_biz_id),
            task_id=task_id,
        )

    # 查询节点管理所有主机
    node_man_host_ids = models.Host.objects.filter(bk_biz_id__in=bk_biz_ids).values_list("bk_host_id", flat=True)

    # 节点管理需要删除的host_id
    need_delete_host_ids = set(node_man_host_ids) - set(cc_bk_host_ids)
    if need_delete_host_ids:
        models.Host.objects.filter(bk_host_id__in=need_delete_host_ids).delete()
        models.IdentityData.objects.filter(bk_host_id__in=need_delete_host_ids).delete()
        models.ProcessStatus.objects.filter(bk_host_id__in=need_delete_host_ids).delete()
        logger.info(f"[sync_cmdb_host] task_id -> {task_id}, need_delete_host_ids -> {need_delete_host_ids}")

    logger.info(f"[sync_cmdb_host] complete: task_id -> {task_id}, bk_biz_ids -> {bk_biz_ids}")


@periodic_task(
    queue="default",
    options={"queue": "default"},
    run_every=crontab(hour="0", minute="0", day_of_week="*", day_of_month="*", month_of_year="*"),
)
def sync_cmdb_host_periodic_task(bk_biz_id=None):
    """
    被动周期同步cmdb主机
    """
    task_id = sync_cmdb_host_periodic_task.request.id
    sync_cmdb_host(bk_biz_id, task_id)


@app.task(queue="default")
def sync_cmdb_host_task(bk_biz_id=None):
    """
    主动同步cmdb主机
    """
    task_id = sync_cmdb_host_task.request.id
    sync_cmdb_host(bk_biz_id, task_id)
