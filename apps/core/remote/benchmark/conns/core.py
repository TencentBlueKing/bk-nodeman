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
import asyncio
import logging
import random
import time
import traceback
import typing

import wrapt

from apps.backend.utils.ssh import SshMan
from apps.core.concurrent import controller
from apps.mock_data import common_unit
from apps.node_man import models
from apps.utils import concurrent
from apps.utils.exc import ExceptionHandler

from ... import conns, exceptions

logging.basicConfig(
    format="%(levelname)s [%(asctime)s] %(name)s | %(funcName)s | %(lineno)d %(message)s", level=logging.ERROR
)

CONCURRENT_CONTROL_CONFIG = {
    "limit": 50,
    "execute_all": False,
    "is_concurrent_between_batches": True,
    "interval": 0,
}

CMDS = [
    "uname -sr",
    "echo 'sleep 5 && ls -al' > /tmp/sleep.sh && chmod +x /tmp/sleep.sh",
    "nohup bash /tmp/sleep.sh &> /tmp/nm.nohup.out &",
]


class LoginInfo:
    login_id: int = None
    ip: str = None
    port: int = None
    username: str = None
    password: str = None

    def __init__(self, login_id: int, ip: str, port: int, username: str, password: str):
        self.login_id = login_id
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password

    def __str__(self):
        return f"[{self.login_id}] {self.ip}:{self.port}"


def gen_login_infos_txt():
    """
    生成登录信息文本
    :return:
    """
    with open(file="local/ips/tmp.txt", mode="r", encoding="utf-8") as fs:
        ips = fs.read().split("\n")
    ips = {ip for ip in ips if ip}
    host_infos = models.Host.objects.filter(inner_ip__in=ips).values("bk_host_id", "inner_ip")
    bk_host_ids = [host_info["bk_host_id"] for host_info in host_infos]
    identity_datas = models.IdentityData.objects.filter(bk_host_id__in=bk_host_ids)

    bk_host_id__identity_data_map: typing.Dict[int, models.IdentityData] = {
        identity_data.bk_host_id: identity_data for identity_data in identity_datas
    }
    bk_host_id__inner_ip_map = {host_info["bk_host_id"]: host_info["inner_ip"] for host_info in host_infos}

    with open(file="local/login_infos.txt", mode="w+", encoding="utf-8") as fs:
        for bk_host_id, identity_data in bk_host_id__identity_data_map.items():
            fs.write(
                ",".join(
                    [
                        str(bk_host_id),
                        bk_host_id__inner_ip_map[bk_host_id],
                        str(identity_data.port),
                        identity_data.account,
                        identity_data.password,
                    ]
                )
                + "\n"
            )


def shuffle_ips(num: int):
    with open(file="local/ips/tmp.txt", mode="r", encoding="utf-8") as fs:
        ips = fs.read().split("\n")

    with open(file="local/ips/tmp_shuffle.txt", mode="w+", encoding="utf-8") as fs:
        fs.write("\n".join(list(random.sample(ips, num))))


def avg(cost_time_str: str):
    cost_times = [int(cost_time) for cost_time in cost_time_str.split("/")]
    return round(sum(cost_times) / len(cost_times), 3)


def format_outputs(login_info: LoginInfo, outputs: typing.List[str]) -> str:
    output_str = f"{login_info}\n" + "\n".join(outputs) + f"\n{20 * '-'}"
    logging.info(output_str)
    return output_str


def exc_handler(
    wrapped: typing.Callable,
    instance: typing.Any,
    args: typing.Tuple[typing.Any],
    kwargs: typing.Dict[str, typing.Any],
    exc: Exception,
):
    logging.error(exc)
    logging.error(traceback.format_exc())
    logging.error(args, kwargs.get("login_info"))


@wrapt.decorator
def time_cost(
    wrapped: typing.Callable,
    instance: typing.Optional[object],
    args: typing.Tuple[typing.Any],
    kwargs: typing.Dict[str, typing.Any],
):
    begin = time.time()
    results = wrapped(*args, **kwargs)
    cost = time.time() - begin
    logging.error(f"cost: {round(cost, 3)}")
    return {"list": results, "cost": cost}


def load_login_infos() -> typing.List[LoginInfo]:
    login_infos: typing.List[LoginInfo] = []

    with open(file="local/login_infos.txt", mode="r", encoding="utf-8") as fs:
        login_info_str = fs.readline()
        while login_info_str:
            login_id_str, ip, port_str, username, password = login_info_str[:-1].split(",", 5)
            login_infos.append(
                LoginInfo(login_id=int(login_id_str), ip=ip, port=int(port_str), username=username, password=password)
            )
            login_info_str = fs.readline()
    return login_infos


@ExceptionHandler(exc_handler=exc_handler)
async def execute_cmds_with_asyncssh(login_info: LoginInfo, cmds: typing.List[str]) -> typing.List[str]:
    async with conns.AsyncsshConn(
        host=login_info.ip, username=login_info.username, port=login_info.port, password=login_info.password
    ) as conn:
        outputs: typing.List[str] = []
        for cmd in cmds:
            try:
                run_result: conns.RunOutput = await conn.run(cmd, check=True)
            except (exceptions.RemoteTimeoutError, exceptions.ProcessError, exceptions.SessionError):
                logging.info(f"{login_info} \n " f"stdout -> {run_result.stdout}, stderr -> {run_result.stderr}")
                break
            outputs.append(f"cmd -> {cmd}, stdout -> {run_result.stdout}, stderr -> {run_result.stderr}")
    format_outputs(login_info, outputs)
    return outputs


def execute_cmds_with_asyncssh_in_sync(login_info: LoginInfo, cmds: typing.List[str]) -> typing.List[str]:
    loop = asyncio.new_event_loop()
    return loop.run_until_complete(execute_cmds_with_asyncssh(login_info, cmds))


@ExceptionHandler(exc_handler=exc_handler)
def execute_cmds_with_ssh_man(login_info: LoginInfo, cmds: typing.List[str]) -> typing.List[str]:

    host_obj = models.Host(**common_unit.host.HOST_MODEL_DATA)
    host_obj.bk_host_id = login_info.login_id
    host_obj.login_ip = host_obj.inner_ip = host_obj.outer_ip = login_info.ip

    identity_data_obj = models.IdentityData(**common_unit.host.IDENTITY_MODEL_DATA)
    identity_data_obj.bk_host_id = login_info.login_id
    identity_data_obj.port = login_info.port
    identity_data_obj.password = login_info.password

    ssh_man = SshMan(host=host_obj, log=logging, identity_data=identity_data_obj)
    ssh_man.get_and_set_prompt()

    is_break = False
    outputs: typing.List[str] = []
    for cmd in cmds:
        try:
            log = ssh_man.send_cmd(cmd)
            outputs.append(log)
        except Exception as e:
            logging.info(e)
            ssh_man.safe_close(ssh_man.ssh)
            is_break = True
            break

    if not is_break:
        ssh_man.safe_close(ssh_man.ssh)
    format_outputs(login_info, outputs)
    return outputs


@ExceptionHandler(exc_handler=exc_handler)
def execute_cmds_with_paramiko(login_info: LoginInfo, cmds: typing.List[str]) -> typing.List[str]:

    with conns.ParamikoConn(
        host=login_info.ip, username=login_info.username, port=login_info.port, password=login_info.password
    ) as conn:
        outputs: typing.List[str] = []
        for cmd in cmds:
            try:
                run_result: conns.RunOutput = conn.run(cmd, check=True)
            except (exceptions.RemoteTimeoutError, exceptions.ProcessError, exceptions.SessionError):
                logging.info(f"{login_info} \n " f"stdout -> {run_result.stdout}, stderr -> {run_result.stderr}")
                break
            outputs.append(f"cmd -> {cmd}, stdout -> {run_result.stdout}, stderr -> {run_result.stderr}")
    format_outputs(login_info, outputs)
    return outputs


@time_cost
@controller.ConcurrentController(
    data_list_name="login_infos",
    batch_call_func=concurrent.batch_call,
    get_config_dict_func=lambda: CONCURRENT_CONTROL_CONFIG,
)
def batch_execute_cmds(
    login_infos: typing.List[LoginInfo],
    cmds: typing.List[str],
    func: typing.Callable[[LoginInfo, typing.List[str]], typing.Union[typing.List[str], typing.Coroutine]],
    batch_call_func: typing.Callable,
):
    params_list = [{"login_info": login_info, "cmds": cmds} for login_info in login_infos]
    return batch_call_func(func=func, params_list=params_list)


def fetch_exceptions(results):
    return [result for result in results if isinstance(result, Exception)]


def check(result):
    info_list = result["list"]
    excs = fetch_exceptions(info_list)
    none_num = len([info for info in info_list if info is None])
    logging.error(f"total -> {len(info_list)}, exceptions -> {len(excs)}, none_num -> {none_num}")
    return {"info_list": info_list, "exceptions": excs, "none_num": none_num, "cost": result["cost"]}


def do_performance(nums: typing.List[int], repeat: int, call_func: typing.Callable, batch_call_func: typing.Callable):
    login_infos = load_login_infos()
    for num in nums:
        total_cost = 0
        for __ in range(repeat):
            random_login_infos = random.sample(login_infos, k=num)
            result = batch_execute_cmds(
                login_infos=random_login_infos, cmds=CMDS, func=call_func, batch_call_func=batch_call_func
            )
            check(result)
            total_cost += result["cost"]
            logging.error(f"call_func -> {call_func.__name__}, cost -> {result['cost']}")
        logging.error(
            f"\n{'-' * 150} \n"
            f"call_func -> {call_func.__name__}, num -> {num}, cost -> {round(total_cost / repeat, 3)} \n"
            f"{'-' * 150} \n\n"
        )
