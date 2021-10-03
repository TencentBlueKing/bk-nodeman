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

from celery.schedules import crontab
from celery.task import periodic_task
from django.conf import settings

from apps.backend.api.errors import JobPollTimeout
from apps.component.esbclient import client_v2
from apps.core.files.exceptions import FilesNotFoundError
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
    proxy_hosts = [
        {"ip": host["inner_ip"], "bk_cloud_id": host["bk_cloud_id"]}
        for host in Host.objects.filter(node_type=constants.NodeType.PROXY).values("inner_ip", "bk_cloud_id")
    ]
    if not proxy_hosts:
        return

    # 实时查询PROXY状态
    agent_status_data = client_v2.gse.get_agent_status({"hosts": proxy_hosts})
    for key, host_info in agent_status_data.items():
        if host_info["bk_agent_alive"] != constants.BkAgentStatus.ALIVE:
            proxy_hosts.remove({"ip": host_info["ip"], "bk_cloud_id": host_info["bk_cloud_id"]})
    if not proxy_hosts:
        return
    file_paths = [file for key in constants.FILES_TO_PUSH_TO_PROXY for file in key["files"]]
    local_file_md5 = {}
    storage = get_storage()
    for download_file in file_paths:
        file_path = os.path.join(settings.DOWNLOAD_PATH, download_file)
        try:
            local_file_md5.update({download_file: storage.get_file_md5(file_path)})
        except FileExistsError:
            logger.warning(
                f"File ->[{download_file}] not found in download path ->[{settings.DOWNLOAD_PATH}], "
                f"please check in order not to affect proxy installation."
            )
        except FilesNotFoundError:
            logger.warning(
                f"File ->[{download_file}] not found in path ->"
                f"[PROJECT:{settings.BKREPO_PROJECT}, BUCKET: {settings.BKREPO_BUCKET}, PATH: {settings.DOWNLOAD_PATH}]"
                f"please check in order not to affect proxy installation."
            )

    if not local_file_md5:
        return True

    files = [file for file in local_file_md5.keys()]
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
        "target_server": {"ip_list": proxy_hosts},
    }

    job_instance_id = JobApi.fast_execute_script(kwargs)["job_instance_id"]
    time.sleep(5)
    result = JobDemand.poll_task_result(job_instance_id)
    task_result = result["task_result"]
    if not result["is_finished"] or not task_result["success"]:
        logger.error(f"get proxy files md5 by job failed, msg: {task_result}")
        raise Exception(f"get proxy files md5 by job failed, msg: {task_result}")
    ip_list = []
    for host_result in task_result["success"]:
        proxy_md5 = json.loads(host_result["log_content"])
        for name, file_md5 in local_file_md5.items():
            if name not in proxy_md5 or proxy_md5[name] != file_md5:
                ip_list.append({"ip": host_result["ip"], "bk_cloud_id": host_result["bk_cloud_id"]})
    if not ip_list:
        logger.info("There are no files with local differences on all proxy servers")
        return

    job_transfer_id = storage.fast_transfer_file(
        bk_biz_id=settings.BLUEKING_BIZ_ID,
        task_name=f"NODEMAN_PUSH_FILE_TO_PROXY_{len(ip_list)}",
        timeout=300,
        account_alias=constants.LINUX_ACCOUNT,
        file_target_path=settings.DOWNLOAD_PATH,
        file_source_list=[{"file_list": [os.path.join(settings.DOWNLOAD_PATH, file) for file in files]}],
        target_server={"ip_list": ip_list},
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
