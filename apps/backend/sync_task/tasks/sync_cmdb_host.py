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

from django.conf import settings
from django.db import transaction

from apps.backend.celery import app
from apps.component.esbclient import client_v2
from apps.exceptions import ComponentCallError
from apps.node_man import constants, models, tools
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


def query_bk_biz_ids(task_id):
    biz_data = client_v2.cc.search_business({"fields": ["bk_biz_id"]})
    bk_biz_ids = [biz["bk_biz_id"] for biz in biz_data.get("info") or [] if biz["default"] == 0]

    # 排除掉黑名单业务的主机同步，比如 SA 业务，包含大量主机但无需同步
    bk_biz_ids = list(
        set(bk_biz_ids)
        - set(
            models.GlobalSettings.get_config(
                key=models.GlobalSettings.KeyEnum.SYNC_CMDB_HOST_BIZ_BLACKLIST.value, default=[]
            )
        )
    )

    logger.info(f"[sync_cmdb_host] synchronize full business: task_id -> {task_id}, count -> {len(bk_biz_ids)}")

    return bk_biz_ids


def _list_biz_hosts(biz_id: int, start: int) -> dict:
    biz_hosts = client_v2.cc.list_biz_hosts(
        {
            "bk_biz_id": biz_id,
            "fields": constants.CC_HOST_FIELDS,
            "page": {"start": start, "limit": constants.QUERY_CMDB_LIMIT, "sort": "bk_host_id"},
        }
    )
    # 去除内网IP为空的主机
    biz_hosts["info"] = [host for host in biz_hosts["info"] if host.get("bk_host_innerip")]
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
        "bk_cloud_id",
        "bk_host_name",
        "bk_addressing",
        "inner_ip",
        "outer_ip",
        "inner_ipv6",
        "outer_ipv6",
        "bk_agent_id",
    ] + extra_fields
    if hosts:
        models.Host.objects.bulk_update(hosts, fields=update_fields)


def _generate_host(biz_id, host, ap_id):
    os_type = tools.HostV2Tools.get_os_type(host)
    cpu_arch = tools.HostV2Tools.get_cpu_arch(host)
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


def update_or_create_host_base(biz_id, task_id, cmdb_host_data):
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

    need_delete_host_ids: typing.Set[int] = set()
    need_create_host_without_biz: typing.List[typing.Dict] = []
    need_update_hosts: typing.List[models.Host] = []
    need_update_hosts_without_biz: typing.List[models.Host] = []
    need_update_hosts_without_os: typing.List[models.Host] = []
    need_update_hosts_without_biz_os: typing.List[models.Host] = []
    need_create_hosts: typing.List[models.Host] = []
    need_update_host_identity_objs: typing.List[models.IdentityData] = []
    need_create_host_identity_objs: typing.List[models.IdentityData] = []
    need_create_process_status_objs: typing.List[models.ProcessStatus] = []

    ap_id = constants.DEFAULT_AP_ID if models.AccessPoint.objects.count() > 1 else models.AccessPoint.objects.first().id

    # 已存在的主机批量更新,不存在的主机批量创建
    for host in cmdb_host_data:
        # 兼容内网IP为空的情况
        # TODO 是否和上面 _list_biz_hosts 逻辑重复
        if not host["bk_host_innerip"]:
            logger.info(
                f"[sync_cmdb_host] update_or_create_host: task_id -> {task_id}, bk_biz_id -> {biz_id}, "
                f"bk_host_id -> {host['bk_host_id']} bk_host_innerip is empty"
            )
            continue

        host_params = {
            "bk_host_id": host["bk_host_id"],
            "bk_agent_id": host.get("bk_agent_id"),
            "bk_cloud_id": host["bk_cloud_id"],
            "bk_host_name": host.get("bk_host_name"),
            "bk_addressing": host.get("bk_addressing") or constants.CmdbAddressingType.STATIC.value,
            "inner_ip": (host.get("bk_host_innerip") or "").split(",")[0],
            "outer_ip": (host.get("bk_host_outerip") or "").split(",")[0],
            "inner_ipv6": (host.get("bk_host_innerip_v6") or "").split(",")[0],
            "outer_ipv6": (host.get("bk_host_outerip_v6") or "").split(",")[0],
        }
        if host["bk_host_id"] in exist_agent_host_ids:

            os_type = tools.HostV2Tools.get_os_type(host)

            if os_type and biz_id:
                host_params["bk_biz_id"] = biz_id
                host_params["os_type"] = os_type
                need_update_hosts.append(models.Host(**host_params))
            elif biz_id:
                host_params["bk_biz_id"] = biz_id
                need_update_hosts_without_os.append(models.Host(**host_params))
            elif os_type:
                host_params["os_type"] = os_type
                need_update_hosts_without_biz.append(models.Host(**host_params))
            else:
                need_update_hosts_without_biz_os.append(models.Host(**host_params))
        elif host["bk_host_id"] in exist_proxy_host_ids:
            host_params["os_type"] = constants.OsType.LINUX
            if biz_id:
                host_params["bk_biz_id"] = biz_id
                need_update_hosts.append(models.Host(**host_params))
            else:
                need_update_hosts_without_biz.append(models.Host(**host_params))
        else:
            # 不是agent不是proxy的主机需要创建
            if not biz_id:
                need_create_host_without_biz.append(host)
            else:
                host_data, identify_data, process_status_data = _generate_host(biz_id, host, ap_id)
                need_create_hosts.append(host_data)
                if identify_data.bk_host_id not in host_ids_in_exist_identity_data:
                    need_create_host_identity_objs.append(identify_data)
                else:
                    need_update_host_identity_objs.append(identify_data)
                if process_status_data.bk_host_id not in host_ids_in_exist_proc_statuses:
                    need_create_process_status_objs.append(process_status_data)

    if need_create_host_without_biz:
        # 查询业务主机数据进行创建
        find_host_biz_ids = [_host["bk_host_id"] for _host in need_create_host_without_biz]
        host_biz_relation = find_host_biz_relations(find_host_biz_ids)
        # 查询不到业务需要删除
        need_delete_host_ids = set(find_host_biz_ids) - set(host_biz_relation.keys())

        for need_create_host in need_create_host_without_biz:
            if need_create_host["bk_host_id"] not in need_delete_host_ids:
                host_data, identify_data, process_status_data = _generate_host(
                    host_biz_relation[need_create_host["bk_host_id"]],
                    need_create_host,
                    ap_id,
                )
                need_create_hosts.append(host_data)
                if identify_data.bk_host_id not in host_ids_in_exist_identity_data:
                    need_create_host_identity_objs.append(identify_data)
                else:
                    need_update_host_identity_objs.append(identify_data)
                if process_status_data.bk_host_id not in host_ids_in_exist_proc_statuses:
                    need_create_process_status_objs.append(process_status_data)

    with transaction.atomic():
        _bulk_update_host(need_update_hosts, ["bk_biz_id", "os_type"])
        _bulk_update_host(need_update_hosts_without_biz, ["os_type"])
        _bulk_update_host(need_update_hosts_without_os, ["bk_biz_id"])
        _bulk_update_host(need_update_hosts_without_biz_os, [])

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

    return bk_host_ids, list(need_delete_host_ids)


def sync_biz_incremental_hosts(bk_biz_id: int, expected_bk_host_ids: typing.Iterable[int]):
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
        biz_id=bk_biz_id, task_id=f"differential_sync_biz_hosts_{bk_biz_id}", cmdb_host_data=hosts
    )


def bulk_differential_sync_biz_hosts(expected_bk_host_ids_gby_bk_biz_id: typing.Dict[int, typing.Iterable[int]]):
    """
    并发同步增量主机
    :param expected_bk_host_ids_gby_bk_biz_id: 按业务ID聚合主机ID列表
    :return:
    """
    params_list: typing.List[typing.Dict] = []
    for bk_biz_id, bk_host_ids in expected_bk_host_ids_gby_bk_biz_id.items():
        params_list.append({"bk_biz_id": bk_biz_id, "expected_bk_host_ids": bk_host_ids})
    batch_call(func=sync_biz_incremental_hosts, params_list=params_list)


def _update_or_create_host(biz_id, start=0, task_id=None):
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

    bk_host_ids, _ = update_or_create_host_base(biz_id, task_id, host_data)

    # 递归
    if host_count > start + constants.QUERY_CMDB_LIMIT:
        bk_host_ids += _update_or_create_host(biz_id, start + constants.QUERY_CMDB_LIMIT, task_id=task_id)

    return bk_host_ids


@app.task(queue="default")
def sync_cmdb_host_task(bk_biz_id=None):
    """
    同步cmdb主机
    """
    task_id = sync_cmdb_host_task.request.id
    logger.info(f"[sync_cmdb_host] start: task_id -> {task_id}, bk_biz_id -> {bk_biz_id}")

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
        cc_bk_host_ids += _update_or_create_host(bk_biz_id, task_id=task_id)

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
