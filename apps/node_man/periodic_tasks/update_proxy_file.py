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
from typing import Dict, List

from celery.schedules import crontab
from celery.task import periodic_task
from django.conf import settings

from apps.backend.api.errors import JobPollTimeout
from apps.component.esbclient import client_v2
from apps.core.files.storage import get_storage
from apps.node_man import constants
from apps.node_man.models import Host
from apps.node_man.periodic_tasks.utils import JobDemand
from common.api import JobApi
from common.log import logger


@periodic_task(
    queue="default",
    options={"queue": "default"},
    run_every=crontab(hour="1", minute="0", day_of_week="*", day_of_month="*", month_of_year="*"),
)
def update_proxy_files():
    local_file__md5_map: Dict[str, str] = {}
    update_proxy_host_list: List[Dict[str, str]] = []
    alive_proxy_hosts: List[Dict[str, str]] = []

    total_proxy_hosts = [
        {"ip": host_info["inner_ip"], "bk_cloud_id": host_info["bk_cloud_id"]}
        for host_info in Host.objects.filter(node_type=constants.NodeType.PROXY).values("inner_ip", "bk_cloud_id")
    ]
    if not total_proxy_hosts:
        return

    # 实时查询PROXY状态
    proxy_agent_status = client_v2.gse.get_agent_status({"hosts": total_proxy_hosts})
    for __, host_info in proxy_agent_status.items():
        if host_info["bk_agent_alive"] == constants.BkAgentStatus.ALIVE:
            alive_proxy_hosts.append({"ip": host_info["ip"], "bk_cloud_id": host_info["bk_cloud_id"]})
    if not alive_proxy_hosts:
        return

    storage = get_storage()
    file_names = [file_name for file_set in constants.FILES_TO_PUSH_TO_PROXY for file_name in file_set["files"]]
    for file_name in file_names:
        file_path = os.path.join(settings.DOWNLOAD_PATH, file_name)
        try:
            local_file__md5_map.update({file_name: storage.get_file_md5(file_path)})
        except FileExistsError as e:
            logger.warning(
                f"file -> {file_path} not found, please check in order not to affect proxy installation, "
                f"error_msg -> {e}"
            )

    if not local_file__md5_map:
        logger.error(
            "There is no file to be pushed to the proxy locally, "
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
        files=files, path=settings.DOWNLOAD_PATH
    )

    kwargs = {
        "bk_biz_id": settings.BLUEKING_BIZ_ID,
        "script_content": base64.b64encode(script.encode()).decode(),
        "script_timeout": 300,
        "account_alias": constants.LINUX_ACCOUNT,
        "is_param_sensitive": 1,
        "script_language": 4,
        "target_server": {"ip_list": alive_proxy_hosts},
    }

    job_instance_id = JobApi.fast_execute_script(kwargs)["job_instance_id"]
    time.sleep(5)
    result = JobDemand.poll_task_result(job_instance_id)
    task_result = result["task_result"]
    if not result["is_finished"] or not task_result["success"]:
        logger.error(f"get proxy files md5 by job failed, msg: {task_result}")
        raise Exception(f"get proxy files md5 by job failed, msg: {task_result}")
    for proxy_task_result in task_result["success"]:
        proxy_file_md5_map = json.loads(proxy_task_result["log_content"])
        for file_name, file_md5 in local_file__md5_map.items():
            if file_name not in proxy_file_md5_map or proxy_file_md5_map[file_name] != file_md5:
                update_proxy_host_list.append(
                    {"ip": proxy_task_result["ip"], "bk_cloud_id": proxy_task_result["bk_cloud_id"]}
                )
                break
    if not update_proxy_host_list:
        logger.info("There are no files with local differences on all proxy servers")
        return

    job_transfer_id = storage.fast_transfer_file(
        bk_biz_id=settings.BLUEKING_BIZ_ID,
        task_name=f"NODEMAN_PUSH_FILE_TO_PROXY_{len(update_proxy_host_list)}",
        timeout=300,
        account_alias=constants.LINUX_ACCOUNT,
        file_target_path=settings.DOWNLOAD_PATH,
        file_source_list=[{"file_list": [os.path.join(settings.DOWNLOAD_PATH, file) for file in files]}],
        target_server={"ip_list": update_proxy_host_list},
    )
    time.sleep(5)
    try:
        transfer_result = JobDemand.poll_task_result(job_transfer_id)
        if transfer_result["is_finished"]:
            logger.info(
                f"proxy update file success, hosts: "
                f"{transfer_result['task_result']['success']}, job_instance_id:{job_transfer_id}"
            )
    except JobPollTimeout:
        logger.error(
            f"proxy update file failed, pending hosts: "
            f"{transfer_result['task_result']['pending']}, failed hosts: {transfer_result['task_result']['failed']}"
            f"job_instance_id:{job_transfer_id}"
        )
