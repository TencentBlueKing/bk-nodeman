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
import base64
import json
import os
import time
from collections import defaultdict
from json import JSONDecodeError
from typing import Any, Dict, List

from celery.schedules import crontab
from celery.task import periodic_task
from django.conf import settings
from django.db.models import Q

from apps.backend.api.errors import JobPollTimeout
from apps.component.esbclient import client_v2
from apps.core.files.storage import get_storage
from apps.node_man import constants
from apps.node_man.models import AccessPoint, Host, InstallChannel
from apps.node_man.periodic_tasks.utils import JobDemand
from common.api import JobApi
from common.log import logger


@periodic_task(
    queue="default",
    options={"queue": "default"},
    run_every=crontab(hour="1", minute="0", day_of_week="*", day_of_month="*", month_of_year="*"),
)
def update_proxy_files():
    alive_hosts: List[Dict[str, str]] = []
    channel_hosts: List[Dict[str, Any]] = []
    ap_nginx_path_map: Dict[Dict[str, int]] = defaultdict(list)
    host_gby_ap_id: Dict[int, List[Dict[str, str]]] = defaultdict(list)

    proxy_hosts = [
        {"ip": host_info["inner_ip"], "bk_cloud_id": host_info["bk_cloud_id"]}
        for host_info in Host.objects.filter(node_type=constants.NodeType.PROXY).values("inner_ip", "bk_cloud_id")
    ]

    channel_host_queryset = InstallChannel.objects.all().values("bk_cloud_id", "jump_servers")
    for channel_info in channel_host_queryset:
        for jump_server in channel_info["jump_servers"]:
            channel_hosts.append({"bk_cloud_id": channel_info["bk_cloud_id"], "ip": jump_server})

    total_update_hosts = proxy_hosts + channel_hosts

    if not total_update_hosts:
        return

    # 实时查询主机状态
    agent_statuses = client_v2.gse.get_agent_status({"hosts": total_update_hosts})
    for __, host_info in agent_statuses.items():
        if host_info["bk_agent_alive"] == constants.BkAgentStatus.ALIVE:
            alive_hosts.append({"ip": host_info["ip"], "bk_cloud_id": host_info["bk_cloud_id"]})
    if not alive_hosts:
        return

    storage = get_storage()
    ap_id_obj_map = {ap.id: ap for ap in AccessPoint.objects.all()}
    for ap_id, obj in ap_id_obj_map.items():
        if not obj.nginx_path:
            ap_nginx_path_map[settings.DOWNLOAD_PATH].append(ap_id)
        else:
            ap_nginx_path_map[obj.nginx_path].append(ap_id)
    if len(ap_nginx_path_map) == 1:
        # 路径相同时，同时下发所有主机
        correct_file_action(settings.DOWNLOAD_PATH, alive_hosts, storage)
    else:
        host_query_conditions = Q()
        host_query_conditions.connector = "OR"
        for host in alive_hosts:
            host_query_conditions.children.append((Q(bk_cloud_id=host["bk_cloud_id"], inner_ip=host["ip"])))
        host_queryset = Host.objects.filter(host_query_conditions)
        for host_obj in host_queryset:
            host_gby_ap_id[host_obj.ap_id].append({"bk_cloud_id": host_obj.bk_cloud_id, "ip": host_obj.inner_ip})
        # 以nginx_path为维度，分批处理
        for nginx_path, ap_ids in ap_nginx_path_map.items():
            same_path_hosts = [host_info for ap_id in ap_ids for host_info in host_gby_ap_id[ap_id]]
            if same_path_hosts:
                correct_file_action(nginx_path, same_path_hosts, storage)


def correct_file_action(download_path: str, hosts: List[Dict[str, str]], storage):
    local_file__md5_map: Dict[str, str] = {}
    lookup_update_host_list: List[Dict[str, str]] = []
    file_names = [file_name for file_set in constants.FILES_TO_PUSH_TO_PROXY for file_name in file_set["files"]]
    for file_name in file_names:
        file_path = os.path.join(download_path, file_name)
        try:
            local_file__md5_map.update({file_name: storage.get_file_md5(file_path)})
        except FileExistsError as e:
            logger.warning(
                f"file -> {file_path} not found, please check in order not to affect proxy installation, "
                f"error_msg -> {e}"
            )

    if not local_file__md5_map:
        logger.error(
            "There is no file to be pushed to the proxy or channel locally, "
            "please check in order not to affect proxy installation."
        )
        return True

    files = [file for file in local_file__md5_map.keys()]
    script = """#!/opt/py36/bin/python
# -*- encoding:utf-8 -*-
import os
import json
import hashlib
from collections import defaultdict
def md5(file_name):
    if not os.path.exists(file_name):
        return
    hash = hashlib.md5()
    try:
        with open(file_name, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                if not chunk:
                    break
                hash.update(chunk)
    except IOError:
        return "-1"

    return hash.hexdigest()

proxy_md5 = defaultdict(dict)
for file in {files}:
    file_path = os.path.join('{path}', file)
    if os.path.exists(file_path):
        proxy_md5.update({{file: md5(file_path)}})
print(json.dumps(proxy_md5))
""".format(
        files=files, path=download_path
    )

    kwargs = {
        "task_name": "NODE_MAN_PROXY_FILES_CHECK_MD5",
        "bk_biz_id": settings.BLUEKING_BIZ_ID,
        "script_content": base64.b64encode(script.encode()).decode(),
        "script_timeout": 300,
        "account_alias": constants.LINUX_ACCOUNT,
        "is_param_sensitive": 1,
        "script_language": 4,
        "target_server": {"ip_list": hosts},
    }

    job_instance_id = JobApi.fast_execute_script(kwargs)["job_instance_id"]
    time.sleep(5)
    result = JobDemand.poll_task_result(job_instance_id)
    task_result = result["task_result"]
    if not result["is_finished"] or not task_result["success"]:
        logger.error(f"get proxy files md5 by job failed, msg: {task_result}")
        raise Exception(f"get proxy files md5 by job failed, msg: {task_result}")

    for proxy_task_result in task_result["success"]:
        logs = proxy_task_result["log_content"].split("\n")
        proxy_file_md5_map = {}
        for log in logs:
            try:
                proxy_file_md5_map = json.loads(log)
            except JSONDecodeError:
                # 期望得到的结果是一行json，解析失败则认为该行不符合预期，抛弃即可
                continue
        if not proxy_file_md5_map:
            logger.error(f"load proxy files md5 failed, result: {result}")
            continue
        for name, file_md5 in local_file__md5_map.items():
            if name not in proxy_file_md5_map or proxy_file_md5_map[name] != file_md5:
                lookup_update_host_list.append(
                    {"ip": proxy_task_result["ip"], "bk_cloud_id": proxy_task_result["bk_cloud_id"]}
                )

    if not lookup_update_host_list:
        logger.info("There are no files with local differences on proxy or channel servers that need to be updated")
        return

    job_transfer_id = storage.fast_transfer_file(
        bk_biz_id=settings.BLUEKING_BIZ_ID,
        task_name=f"NODEMAN_PUSH_FILE_TO_PROXY_{len(lookup_update_host_list)}",
        timeout=300,
        account_alias=constants.LINUX_ACCOUNT,
        file_target_path=download_path,
        file_source_list=[{"file_list": [os.path.join(download_path, file) for file in files]}],
        target_server={"ip_list": lookup_update_host_list},
    )
    time.sleep(5)
    transfer_result = {"task_result": {"pending": lookup_update_host_list, "failed": []}}
    try:
        transfer_result = JobDemand.poll_task_result(job_transfer_id)
        if transfer_result["is_finished"]:
            logger.info(
                f"proxy or channel host update file success, hosts: "
                f"{transfer_result['task_result']['success']}, job_instance_id:{job_transfer_id}"
            )
    except JobPollTimeout:
        logger.error(
            f"proxy or channel host update file failed, pending hosts: "
            f"{transfer_result['task_result']['pending']}, failed hosts: {transfer_result['task_result']['failed']}"
            f"job_instance_id:{job_transfer_id}"
        )
