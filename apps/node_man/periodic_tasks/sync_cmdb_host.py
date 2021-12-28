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
import math

from celery.schedules import crontab
from celery.task import periodic_task
from django.conf import settings

from apps.component.esbclient import client_v2
from apps.exceptions import ComponentCallError
from apps.node_man import constants as const
from apps.node_man import models, tools
from common.log import logger


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

    logger.info(f"{task_id} | sync_cmdb_host biz count {len(bk_biz_ids)}")

    return bk_biz_ids


def _list_biz_hosts(biz_id: int, start: int) -> dict:
    biz_hosts = client_v2.cc.list_biz_hosts(
        {
            "bk_biz_id": biz_id,
            "fields": const.CC_HOST_FIELDS,
            "page": {"start": start, "limit": const.QUERY_CMDB_LIMIT, "sort": "bk_host_id"},
        }
    )
    # 去除内网IP为空的主机
    biz_hosts["info"] = [host for host in biz_hosts["info"] if host.get("bk_host_innerip")]
    return biz_hosts


def _list_resource_pool_hosts(start):
    try:
        result = client_v2.cc.list_resource_pool_hosts(
            {
                "page": {"start": start, "limit": const.QUERY_CMDB_LIMIT, "sort": "bk_host_id"},
                "fields": const.CC_HOST_FIELDS,
            }
        )
        return result
    except ComponentCallError:
        return {"info": []}


def _bulk_update_host(hosts, fields):
    if hosts:
        models.Host.objects.bulk_update(hosts, fields=fields)


def _generate_host(biz_id, host, bk_host_innerip, bk_host_outerip, ap_id):
    os_type = tools.HostV2Tools.get_os_type(host)
    cpu_arch = tools.HostV2Tools.get_cpu_arch(host)
    host_data = models.Host(
        bk_host_id=host["bk_host_id"],
        bk_biz_id=biz_id,
        bk_cloud_id=host["bk_cloud_id"],
        inner_ip=bk_host_innerip,
        outer_ip=bk_host_outerip,
        node_from=const.NodeFrom.CMDB,
        os_type=os_type,
        cpu_arch=cpu_arch,
        node_type=const.NodeType.AGENT if host["bk_cloud_id"] == const.DEFAULT_CLOUD else const.NodeType.PAGENT,
        ap_id=ap_id,
    )

    identify_data = models.IdentityData(
        bk_host_id=host["bk_host_id"],
        auth_type="PASSWORD",
        account=const.WINDOWS_ACCOUNT if os_type == const.OsType.WINDOWS else const.LINUX_ACCOUNT,
        port=const.WINDOWS_PORT if os_type == const.OsType.WINDOWS else settings.BKAPP_DEFAULT_SSH_PORT,
    )

    process_status_data = models.ProcessStatus(bk_host_id=host["bk_host_id"], name="gseagent")

    return host_data, identify_data, process_status_data


def find_host_biz_relations(find_host_biz_ids):
    host_biz_relation = {}
    for count in range(math.ceil(len(find_host_biz_ids) / const.QUERY_CMDB_LIMIT)):
        cc_host_biz_relations = client_v2.cc.find_host_biz_relations(
            {"bk_host_id": find_host_biz_ids[count * const.QUERY_CMDB_LIMIT : (count + 1) * const.QUERY_CMDB_LIMIT]}
        )
        for _host_biz in cc_host_biz_relations:
            host_biz_relation[_host_biz["bk_host_id"]] = _host_biz["bk_biz_id"]

    return host_biz_relation


def update_or_create_host_base(biz_id, task_id, cmdb_host_data):
    bk_host_ids = [_host["bk_host_id"] for _host in cmdb_host_data]

    # 查询节点管理已存在的主机
    exist_proxy_host_ids = models.Host.objects.filter(bk_host_id__in=bk_host_ids, node_type="PROXY").values_list(
        "bk_host_id", flat=True
    )
    exist_agent_host_ids = (
        models.Host.objects.filter(bk_host_id__in=bk_host_ids)
        .exclude(node_type="PROXY")
        .values_list("bk_host_id", flat=True)
    )

    need_update_hosts = []
    need_update_hosts_without_biz = []
    need_update_hosts_without_os = []
    need_update_hosts_without_biz_os = []
    need_create_hosts = []
    host_identity_objs = []
    process_status_objs = []
    need_create_host_without_biz = []
    need_delete_host_ids = []

    ap_id = const.DEFAULT_AP_ID if models.AccessPoint.objects.count() > 1 else models.AccessPoint.objects.first().id

    # 已存在的主机批量更新,不存在的主机批量创建
    for host in cmdb_host_data:
        # 兼容内网IP为空的情况
        if not host["bk_host_innerip"]:
            logger.info(
                f"{task_id} | sync_cmdb_host error: biz[{biz_id}] | bk_host_id[{host['bk_host_id']}]] "
                f"bk_host_innerip is empty"
            )
            continue

        if any(["," in host["bk_host_innerip"], "," in host["bk_host_outerip"]]):
            logger.info(
                f"{task_id} | sync_cmdb_host error: biz[{biz_id}] | bk_host_id[{host['bk_host_id']}]] | "
                f"inner_ip [{host['bk_host_innerip']}]"
            )
            bk_host_innerip = host["bk_host_innerip"].split(",")[0]
            bk_host_outerip = host["bk_host_outerip"].split(",")[0]
        else:
            bk_host_innerip = host["bk_host_innerip"]
            bk_host_outerip = host["bk_host_outerip"]

        if host["bk_host_id"] in exist_agent_host_ids:
            host_params = {
                "bk_host_id": host["bk_host_id"],
                "bk_cloud_id": host["bk_cloud_id"],
                "inner_ip": bk_host_innerip,
                "outer_ip": bk_host_outerip,
            }

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
            host_params = {
                "bk_host_id": host["bk_host_id"],
                "bk_cloud_id": host["bk_cloud_id"],
                "inner_ip": bk_host_innerip,
                "outer_ip": bk_host_outerip,
                "os_type": const.OsType.LINUX,
            }
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
                host_data, identify_data, process_status_data = _generate_host(
                    biz_id, host, bk_host_innerip, bk_host_outerip, ap_id
                )
                need_create_hosts.append(host_data)
                host_identity_objs.append(identify_data)
                process_status_objs.append(process_status_data)

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
                    need_create_host["bk_host_innerip"].split(",")[0],
                    need_create_host["bk_host_outerip"].split(",")[0],
                    ap_id,
                )
                need_create_hosts.append(host_data)
                host_identity_objs.append(identify_data)
                process_status_objs.append(process_status_data)

    _bulk_update_host(need_update_hosts, ["bk_biz_id", "bk_cloud_id", "inner_ip", "outer_ip", "os_type"])
    _bulk_update_host(need_update_hosts_without_biz, ["bk_cloud_id", "inner_ip", "outer_ip", "os_type"])
    _bulk_update_host(need_update_hosts_without_os, ["bk_biz_id", "bk_cloud_id", "inner_ip", "outer_ip"])
    _bulk_update_host(need_update_hosts_without_biz_os, ["bk_cloud_id", "inner_ip", "outer_ip"])

    if need_create_hosts:
        models.Host.objects.bulk_create(need_create_hosts)
        models.IdentityData.objects.bulk_create(host_identity_objs)
        models.ProcessStatus.objects.bulk_create(process_status_objs)

    return bk_host_ids, list(need_delete_host_ids)


def _update_or_create_host(biz_id, start=0, task_id=None):
    if biz_id == settings.BK_CMDB_RESOURCE_POOL_BIZ_ID:
        cc_result = _list_resource_pool_hosts(start)
    else:
        cc_result = _list_biz_hosts(biz_id, start)

    host_data = cc_result.get("info") or []
    host_count = cc_result.get("count", 0)

    logger.info(
        f"{task_id} | sync_cmdb_host biz:[{biz_id}] "
        f"host count: [{host_count}] current sync[{start}-{start + const.QUERY_CMDB_LIMIT}]"
    )

    bk_host_ids, _ = update_or_create_host_base(biz_id, task_id, host_data)

    # 递归
    if host_count > start + const.QUERY_CMDB_LIMIT:
        bk_host_ids += _update_or_create_host(biz_id, start + const.QUERY_CMDB_LIMIT, task_id=task_id)

    return bk_host_ids


@periodic_task(
    queue="default",
    options={"queue": "default"},
    run_every=crontab(hour="0", minute="0", day_of_week="*", day_of_month="*", month_of_year="*"),
)
def sync_cmdb_host_periodic_task(bk_biz_id=None):
    """
    同步cmdb主机
    """
    task_id = sync_cmdb_host_periodic_task.request.id
    logger.info(f"{task_id} | sync cmdb host start.")

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
        logger.info(f"{task_id} | Delete host ids {need_delete_host_ids}")

    logger.info(f"{task_id} | Sync cmdb host complete.")
