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
from apps.backend.api.job import JobClient
from apps.component.esbclient import client_v2
from apps.node_man import constants as const
from apps.node_man.models import Host
from apps.utils.files import md5sum
from common.log import logger


@periodic_task(
    queue="default",
    options={"queue": "default"},
    run_every=crontab(hour="1", minute="0", day_of_week="*", day_of_month="*", month_of_year="*"),
)
def update_proxy_file():
    proxy_hosts = [
        {
            "ip": host.inner_ip,
            "bk_cloud_id": host.bk_cloud_id,
        }
        for host in Host.objects.filter(node_type=const.NodeType.PROXY)
    ]
    if not proxy_hosts:
        return

    # 实时查询PROXY状态
    agent_status_data = client_v2.gse.get_agent_status({"hosts": proxy_hosts})
    for key, host_info in agent_status_data.items():
        if host_info["bk_agent_alive"] != const.BkAgentStatus.ALIVE:
            proxy_hosts.remove({"ip": host_info["ip"], "bk_cloud_id": host_info["bk_cloud_id"]})
    if not proxy_hosts:
        return
    file_name = [file for key in const.FILES_TO_PUSH_TO_PROXY for file in key["files"]]
    local_file_md5 = {}
    for download_file in file_name:
        file_path = os.path.join(settings.NGINX_DOWNLOAD_PATH, download_file)
        if os.path.exists(file_path):
            local_file_md5.update({download_file: md5sum(file_path)})
        else:
            logger.warning(
                f"File ->[{download_file}] not found in download path ->[{settings.NGINX_DOWNLOAD_PATH}], "
                f"please check in order not to affect proxy installation."
            )
    if not local_file_md5:
        return

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
        files=files, path=settings.NGINX_DOWNLOAD_PATH
    )

    kwargs = {
        "bk_biz_id": settings.BLUEKING_BIZ_ID,
        "script_content": base64.b64encode(script.encode()).decode(),
        "script_timeout": 300,
        "account": const.LINUX_ACCOUNT,
        "is_param_sensitive": 1,
        "script_type": 4,
        "target_server": {"ip_list": proxy_hosts},
    }

    data = client_v2.job.fast_execute_script(kwargs, bk_username=settings.SYSTEM_USE_API_ACCOUNT)
    job_instance_id = data["job_instance_id"]
    time.sleep(5)
    client = JobClient(
        bk_biz_id=settings.BLUEKING_BIZ_ID, username=settings.SYSTEM_USE_API_ACCOUNT, os_type=const.OsType.LINUX
    )
    is_finished, task_result = client.poll_task_result(job_instance_id)
    if not is_finished or not task_result["success"]:
        logger.error(f"get proxy files md5 by job failed, msg: {task_result}")
        raise Exception(f"get proxy files md5 by job failed, msg: {task_result}")
    ip_list = []
    for result in task_result["success"]:
        proxy_md5 = json.loads(result["log_content"])
        for name, file_md5 in local_file_md5.items():
            if name not in proxy_md5 or proxy_md5[name] != file_md5:
                ip_list.append({"ip": result["ip"], "bk_cloud_id": result["bk_cloud_id"]})
    if not ip_list:
        return
    client = JobClient(
        bk_biz_id=settings.BLUEKING_BIZ_ID, username=settings.SYSTEM_USE_API_ACCOUNT, os_type=const.OsType.LINUX
    )
    file_source = [
        {
            "files": [os.path.join(settings.NGINX_DOWNLOAD_PATH, file) for file in files],
            "account": const.LINUX_ACCOUNT,
            "ip_list": [{"ip": settings.BKAPP_LAN_IP, "bk_cloud_id": 0}],
        }
    ]
    job_instance_id = client.fast_push_file(
        ip_list=ip_list, file_target_path=settings.NGINX_DOWNLOAD_PATH, file_source=file_source
    )

    time.sleep(5)
    try:
        is_finished, result = client.poll_task_result(job_instance_id)
    except JobPollTimeout:
        logger.error(f"proxy update file failed. job_instance_id:{job_instance_id}")
    if is_finished:
        logger.info(f"proxy update file success. job_instance_id:{job_instance_id}")
