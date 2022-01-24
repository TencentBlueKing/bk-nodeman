# coding: utf-8
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""


from subprocess import check_output

from django.conf import settings
from django.utils.translation import ugettext as _
from six.moves import zip

from common.log import logger

from .checker import CheckerRegister
from .utils import get_process_info, get_supervisor_client

register = CheckerRegister.supervisor


@register.status()
def status(manager, result):
    """Supervisor 自身状态"""
    try:
        client = get_supervisor_client()
        return result.ok(client.supervisor.getPID())
    except Exception as err:
        logger.exception(err)
        return result.fail(str(err))


@register.process.status()
def process_status(manager, result):
    """Supervisor 进程状态"""
    client = get_supervisor_client()
    info = client.supervisor.getAllProcessInfo()
    process_name = ""
    process_state = ""
    all_running = True
    for i in info:
        state = i.get("statename")
        desc = i.get("description")
        if state != "RUNNING" and desc != "Not started":
            # 'Not started' means autostart=false in config file
            all_running = False
            process_name = i.get("name")
            process_state = state
    if all_running:
        result.ok(all_running)
    else:
        result.fail("{} {}".format(process_name, process_state))


@register.process.info()
def process_info(manager, result, process_name):
    """Supervisor 进程详情"""
    ok = False
    processes = []
    # 遍历所选组内所有任务
    for info in get_process_info():
        # 如果任务名含有process_name，证明是该类型任务
        if info.get("name").startswith(process_name):
            processes.append(
                {
                    "name": info.get("name"),
                    "pid": info.get("pid"),
                    "start": info.get("start"),
                    "exitstatus": info.get("exitstatus"),
                    "spawnerr": info.get("spawnerr"),
                    "statename": info.get("statename"),
                    "description": info.get("description"),
                }
            )

            uptime = info.get("now", 0) - info.get("start", 0)
            is_running = info.get("statename") == "RUNNING" and uptime >= settings.SUPERVISOR_PROCESS_UPTIME
            not_started = info.get("description") == "Not started"

            if not is_running and info.get("statename") == "RUNNING":
                processes[-1]["description"] += _(", 进程启动时间小于10秒，请关注")

            if info and (is_running or not_started):
                ok = True
    if ok:
        return result.ok(processes)
    return result.fail(processes)


@register.escaped()
def escaped_processes(manager, result, python_bin):
    client = get_supervisor_client()
    pid = str(client.supervisor.getPID())
    ps_infos = check_output(["ps", "-elf"]).splitlines()
    title = [i.lower().decode("utf-8") for i in ps_infos[0].split()]
    process_pids = []
    for line in ps_infos[1:]:
        cols = [col.decode("utf-8") for col in line.split()]
        info = {k: v for k, v in zip(title, cols)}
        cmd = [info["cmd"]]
        cmd.extend(cols)
        info["cmd"] = " ".join(cmd)
        if info.get("ppid") == "1" and info.get("pid") != pid and info.get("cmd", "").startswith(python_bin):
            pid = info.get("pid")
            process_pids.append(str(info.get("pid")))
    if process_pids:
        return result.fail("逃逸进程pid：" + ",".join(process_pids))
    return result.ok(value="ok")
