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
from telnetlib import Telnet
from typing import Dict, List, Optional, Tuple

from celery.task import periodic_task
from django.conf import settings
from kazoo.client import KazooClient
from kazoo.exceptions import NoAuthError, NoNodeError

from apps.node_man import constants, models
from common.log import logger


def check_ip_ports_reachable(host: str, ports: List[int]) -> bool:
    for port in ports:
        try:
            with Telnet(host=host, port=port, timeout=2):
                pass
        except (ConnectionRefusedError, TimeoutError):
            logger.error(f"host -> {host}, port -> {port} not reachable.")
            return False
    return True


class ZkSafeClient:
    zk_client: Optional[KazooClient]

    def __init__(self, hosts: str, auth_data: List[Tuple[str, str]], **kwargs):
        self.zk_client = KazooClient(hosts=hosts, auth_data=auth_data, **kwargs)

    def __enter__(self) -> KazooClient:
        self.zk_client.start()
        return self.zk_client

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.zk_client.stop()


@periodic_task(
    queue="default",
    options={"queue": "default"},
    run_every=constants.GSE_SVR_DISCOVERY_INTERVAL,
)
def gse_svr_discovery_periodic_task():
    if not settings.GSE_ENABLE_SVR_DISCOVERY:
        logger.info(f"GSE_ENABLE_SVR_DISCOVERY == {settings.GSE_ENABLE_SVR_DISCOVERY}, skip")
        return
    ap = models.AccessPoint.objects.all().first()
    if not ap:
        logger.error("not access point, skip")
        return

    logger.info(f"gse_svr_discovery: access_point -> {ap.name}")

    gse_zk_root: str = "/gse/config/server"
    # 优先通过区域和城市进行服务发现，如果配置缺失则使用 all 获取全部
    if ap.region_id and ap.city_id:
        gse_zk_suffix: str = f"{ap.region_id}/{ap.city_id}"
    else:
        gse_zk_suffix: str = "all"

    zk_node_path__ap_field_map: Dict[str, str] = {
        f"{gse_zk_root}/dataserver/{gse_zk_suffix}": "dataserver",
        f"{gse_zk_root}/task/{gse_zk_suffix}": "taskserver",
        f"{gse_zk_root}/btfiles/{gse_zk_suffix}": "btfileserver",
    }
    zk_node_path__check_ports_map: Dict[str, List[int]] = {
        f"{gse_zk_root}/dataserver/{gse_zk_suffix}": [ap.port_config["data_port"]],
        f"{gse_zk_root}/task/{gse_zk_suffix}": [ap.port_config["io_port"]],
        f"{gse_zk_root}/btfiles/{gse_zk_suffix}": [ap.port_config["file_svr_port"]],
    }

    is_change = False
    auth_data = None
    zk_hosts_str = ",".join(f"{zk_host['zk_ip']}:{zk_host['zk_port']}" for zk_host in ap.zk_hosts)
    if ap.zk_account and ap.zk_password:
        auth_data = [("digest", f"{ap.zk_account}:{ap.zk_password}")]

    with ZkSafeClient(hosts=zk_hosts_str, auth_data=auth_data) as zk_client:
        for zk_node_path, ap_field in zk_node_path__ap_field_map.items():
            try:
                svr_ips = zk_client.get_children(path=zk_node_path)
                # 过滤不可达的ip
                svr_ips = [
                    svr_ip
                    for svr_ip in svr_ips
                    if check_ip_ports_reachable(svr_ip, zk_node_path__check_ports_map[zk_node_path])
                ]

            except NoNodeError:
                logger.error(f"zk_node_path -> {zk_node_path} not exist")
            except NoAuthError:
                logger.error(f"zk_node_path -> {zk_node_path} no auth, please check zk account.")
            except Exception as e:
                logger.exception(f"failed to get zk_node_path -> {zk_node_path}, err: {e}")
            else:
                if not svr_ips:
                    logger.info(f"zk_node_path -> {zk_node_path} get empty ip list, skip.")
                    continue
                logger.info(f"zk_node_path -> {zk_node_path}, svr_ips -> {svr_ips}")

                outer_ips = getattr(ap, ap_field, {}).get("outer_ip_infos") or {}
                inner_ip_infos: List[Dict[str, str]] = [{"ip": inner_ip} for inner_ip in svr_ips]

                svr_infos: Dict[str, List[Dict[str, str]]] = {
                    "inner_ip_infos": inner_ip_infos,
                    "outer_ip_infos": outer_ips if outer_ips else inner_ip_infos,
                }
                setattr(ap, ap_field, svr_infos)
                logger.info(f"update ap -> {ap}, {ap_field} -> {svr_infos}")
                is_change = True
    if is_change:
        ap.save()
