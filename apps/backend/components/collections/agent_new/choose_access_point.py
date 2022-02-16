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
import random
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Union

from django.utils.translation import ugettext_lazy as _

from apps.backend import constants as backend_constants
from apps.backend.utils.wmi import execute_cmd
from apps.core.concurrent import controller
from apps.core.remote import conns
from apps.node_man import constants, models
from apps.utils import concurrent, exc

from .. import core
from .base import AgentBaseService, AgentCommonData


class ChooseAccessPointService(AgentBaseService):
    """选择接入点"""

    # windows返回执行结果的正则表示式
    WIN_PING_PATTERN = re.compile(r"(?<=\=\s)\d+(?=ms)")
    # 用于表示ping不通时的ping时间
    MIN_PING_TIME = 9999
    # 用于表示选不到接入点的默认值
    FAILED_AP_ID = -2

    @classmethod
    def construct_return_data(
        cls,
        ap_id_obj_map: Dict[Optional[int], models.AccessPoint],
        bk_host_id: int,
        ap_id: int,
        log: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        构造接入点选择结果
        :param ap_id_obj_map:
        :param bk_host_id: 主机ID
        :param ap_id: 接入点ID
        :param log: 日志，为空会根据ap_id 取值情况打印默认日志
        :return: 接入点选择结果
        """
        if not log:
            if ap_id == cls.FAILED_AP_ID:
                log = _("选择接入点失败")
            else:
                log = _("已选择[{ap_name}]作为本次安装接入点").format(ap_name=ap_id_obj_map[ap_id].name)
        return {"bk_host_id": bk_host_id, "ap_id": ap_id, "log": log}

    def detect_host_to_aps_network(
        self, host: models.Host, ap_objs: List[models.AccessPoint]
    ) -> Dict[str, Union[Dict[int, float], float, int]]:
        """
        探测指定主机到ap所属的gse svr的连通性
        :param host: 主机对象
        :param ap_objs: 接入点对象
        :return: 探测结果
        """
        is_windows = host.os_type in [constants.OsType.WINDOWS]
        ssh_conn = None
        if not is_windows:
            ip = host.login_ip or (host.inner_ip, host.outer_ip)[host.node_type == constants.NodeType.PROXY]
            client_key_strings = []
            if host.identity.auth_type == constants.AuthType.KEY:
                client_key_strings.append(host.identity.key)
            ssh_conn = conns.ParamikoConn(
                host=ip,
                port=host.identity.port,
                username=host.identity.account,
                password=host.identity.password,
                client_key_strings=client_key_strings,
                connect_timeout=backend_constants.SSH_CON_TIMEOUT,
            )
            ssh_conn.connect()

        # 接入点id - ping时间 映射关系
        ap_id__ping_time_map: Dict[int, float] = {}
        # 最少的ping时间
        min_ping_time: float = self.MIN_PING_TIME
        # 最少ping时间的接入点id
        min_ping_ap_id: int = self.FAILED_AP_ID

        for ap in ap_objs:
            task_server_ping_time_list: List[float] = []
            for task_server in ap.taskserver:
                ip = task_server["inner_ip"] if host.bk_cloud_id == constants.DEFAULT_CLOUD else task_server["outer_ip"]
                if is_windows:
                    output = execute_cmd(
                        f"ping {ip} -w 1000",
                        host.login_ip or host.inner_ip,
                        host.identity.account,
                        host.identity.password,
                    )["data"]
                    try:
                        ping_time = self.WIN_PING_PATTERN.findall(output)[-1]
                        task_server_ping_time_list.append(float(ping_time))
                    except IndexError:
                        pass
                else:
                    run_output = ssh_conn.run(
                        command=f"ping {ip} -i 0.1 -c 4 -s 100 -W 1 | tail -1 | awk -F '/' '{{print $5}}'",
                        check=False,
                        timeout=backend_constants.SSH_RUN_TIMEOUT,
                    )
                    ping_time_str = run_output.stdout or str(self.MIN_PING_TIME)
                    if ping_time_str:
                        task_server_ping_time_list.append(float(ping_time_str))
            if task_server_ping_time_list:
                ap_id__ping_time_map[ap.id] = sum(task_server_ping_time_list) / len(task_server_ping_time_list)
            else:
                ap_id__ping_time_map[ap.id] = self.MIN_PING_TIME

            if ap_id__ping_time_map[ap.id] < min_ping_time:
                min_ping_time = ap_id__ping_time_map[ap.id]
                min_ping_ap_id = ap.id

        if not is_windows:
            ssh_conn.close()

        return {
            "ap_id__ping_time_map": ap_id__ping_time_map,
            "min_ping_time": min_ping_time,
            "min_ping_ap_id": min_ping_ap_id,
        }

    @exc.ExceptionHandler(exc_handler=core.default_sub_inst_task_exc_handler)
    def detect_and_choose_ap(
        self,
        sub_inst_id: int,
        host: models.Host,
        ap_objs: List[models.AccessPoint],
        ap_id_obj_map: Dict[Optional[int], models.AccessPoint],
    ) -> Dict[str, Any]:
        """
        探测并选择连通性最好的接入点
        :param sub_inst_id: 订阅实例ID
        :param host: 主机对象
        :param ap_objs: 接入点列表
        :param ap_id_obj_map: 接入点ID - 接入点对象映射
        :return: 接入点选择结果
        """
        detect_result = self.detect_host_to_aps_network(host=host, ap_objs=ap_objs)
        ping_logs = []
        for ap_id, ping_time in detect_result["ap_id__ping_time_map"].items():
            ping_logs.append(
                _("连接至接入点[{ap_name}]的平均延迟为 {ping_time}ms").format(
                    ap_name=ap_id_obj_map[ap_id].name, ping_time=ping_time
                )
            )
        if ping_logs:
            self.log_info(sub_inst_id, log_content="\n".join(ping_logs))

        if detect_result["min_ping_ap_id"] == self.FAILED_AP_ID:
            return self.construct_return_data(
                ap_id_obj_map=ap_id_obj_map,
                bk_host_id=host.bk_host_id,
                ap_id=self.FAILED_AP_ID,
                log=_("自动选择接入点失败，接入点均ping不可达"),
            )

        return self.construct_return_data(
            ap_id_obj_map=ap_id_obj_map, bk_host_id=host.bk_host_id, ap_id=detect_result["min_ping_ap_id"]
        )

    @controller.ConcurrentController(
        data_list_name="detect_and_choose_ap_params_list",
        batch_call_func=concurrent.batch_call,
        get_config_dict_func=core.get_config_dict,
        get_config_dict_kwargs={"config_name": core.ServiceCCConfigName.SSH.value},
    )
    def handle_detect_condition(self, detect_and_choose_ap_params_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        处理需要探测选择接入点的情况
        :param detect_and_choose_ap_params_list: 调用 self.detect_and_choose_ap 的参数列表
        :return: 接入点选择结果列表
        """
        if not detect_and_choose_ap_params_list:
            return []

        return concurrent.batch_call(
            func=self.detect_and_choose_ap, params_list=detect_and_choose_ap_params_list, get_data=lambda x: x
        )

    def handle_pagent_condition(
        self,
        pagent_host_ids__gby_cloud_id: Dict[int, List[int]],
        ap_id_obj_map: Dict[Optional[int], models.AccessPoint],
    ) -> List[Dict[str, Any]]:
        """
        处理Pagent的情况，随机选择存活接入点
        :param pagent_host_ids__gby_cloud_id: PAgent 主机ID - 云区域ID 映射
        :param ap_id_obj_map: 接入点ID - 接入点对象映射
        :return: 接入点选择结果列表
        """
        if not pagent_host_ids__gby_cloud_id:
            return []
        bk_cloud_ids = pagent_host_ids__gby_cloud_id.keys()

        # 获取指定云区域范围内全部的Proxy
        all_proxies = models.Host.objects.filter(
            bk_cloud_id__in=bk_cloud_ids, node_type=constants.NodeType.PROXY
        ).values("bk_host_id", "bk_cloud_id", "ap_id")
        all_proxy_host_ids = [proxy["bk_host_id"] for proxy in all_proxies]
        proxy_host_id__ap_id_map = {proxy["bk_host_id"]: proxy["ap_id"] for proxy in all_proxies}

        # 获取存活的Proxy ID 列表
        alive_proxy_host_ids = models.ProcessStatus.objects.filter(
            bk_host_id__in=all_proxy_host_ids, status=constants.ProcStateType.RUNNING
        ).values_list("bk_host_id", flat=True)

        # 将存活的 Proxy 按云区域进行聚合
        # 转为set，提高 in 的执行效率
        alive_proxy_host_ids = set(alive_proxy_host_ids)
        alive_proxy_host_ids_gby_cloud_id: Dict[int, List[int]] = defaultdict(list)
        for proxy in all_proxies:
            if proxy["bk_host_id"] not in alive_proxy_host_ids:
                continue
            alive_proxy_host_ids_gby_cloud_id[proxy["bk_cloud_id"]].append(proxy["bk_host_id"])

        # 随机选取Proxy
        choose_ap_results: List[Dict[str, Any]] = []
        for bk_cloud_id, bk_host_ids in pagent_host_ids__gby_cloud_id.items():
            alive_proxy_host_ids_in_cloud = alive_proxy_host_ids_gby_cloud_id[bk_cloud_id]
            if not alive_proxy_host_ids_in_cloud:
                for bk_host_id in bk_host_ids:
                    choose_ap_results.append(
                        self.construct_return_data(
                            ap_id_obj_map=ap_id_obj_map,
                            bk_host_id=bk_host_id,
                            ap_id=self.FAILED_AP_ID,
                            log=_("云区域 -> {bk_cloud_id} 下无存活的 Proxy").format(bk_cloud_id=bk_cloud_id),
                        )
                    )
                continue

            for bk_host_id in bk_host_ids:
                alive_proxy_host_id = random.choice(alive_proxy_host_ids_in_cloud)
                ap_id = proxy_host_id__ap_id_map[alive_proxy_host_id]
                choose_ap_results.append(
                    self.construct_return_data(ap_id_obj_map=ap_id_obj_map, bk_host_id=bk_host_id, ap_id=ap_id)
                )

        return choose_ap_results

    def handle_choose_ap_results(
        self,
        choose_ap_results: List[Dict[str, Any]],
        bk_host_id__sub_inst_id_map: Dict[int, int],
        host_id_obj_map: Dict[int, models.Host],
    ) -> None:
        """
        聚合打日志，更新接入点 host
        :param choose_ap_results: 接入点选择结果
        :param bk_host_id__sub_inst_id_map: 主机ID - 订阅实例ID 映射
        :param host_id_obj_map: 主机ID - 主机对象 映射
        :return: None
        """
        failed_choose_ap_results: List[Dict[str, Any]] = []
        succeed_choose_ap_results: List[Dict[str, Any]] = []
        for choose_ap_result in choose_ap_results:
            if choose_ap_result["ap_id"] == self.FAILED_AP_ID:
                failed_choose_ap_results.append(choose_ap_result)
            else:
                succeed_choose_ap_results.append(choose_ap_result)

        # 移除失败的实例ID并打印错误信息
        failed_sub_inst_ids_gby_log = self.get_sub_inst_ids_gby_log(
            choose_ap_results=failed_choose_ap_results, bk_host_id__sub_inst_id_map=bk_host_id__sub_inst_id_map
        )
        for log, sub_inst_ids in failed_sub_inst_ids_gby_log.items():
            self.move_insts_to_failed(sub_inst_ids=sub_inst_ids, log_content=log)

        # 更新主机接入点
        bk_host_ids__gby_ap_id: Dict[int, List[int]] = defaultdict(list)
        for succeed_choose_ap_result in succeed_choose_ap_results:
            bk_host_ids__gby_ap_id[succeed_choose_ap_result["ap_id"]].append(succeed_choose_ap_result["bk_host_id"])
        for ap_id, bk_host_ids in bk_host_ids__gby_ap_id.items():
            bk_host_ids_to_be_updated = []
            for bk_host_id in bk_host_ids:
                if ap_id != host_id_obj_map[bk_host_id].ap_id:
                    bk_host_ids_to_be_updated.append(bk_host_id)
            if bk_host_ids_to_be_updated:
                models.Host.objects.filter(bk_host_id__in=bk_host_ids_to_be_updated).update(ap_id=ap_id)

        # 打印成功选择接入点的信息
        succeed_sub_inst_ids__gby_log = self.get_sub_inst_ids_gby_log(
            choose_ap_results=succeed_choose_ap_results, bk_host_id__sub_inst_id_map=bk_host_id__sub_inst_id_map
        )
        for log, sub_inst_ids in succeed_sub_inst_ids__gby_log.items():
            self.log_info(sub_inst_ids=sub_inst_ids, log_content=log)

    @classmethod
    def get_sub_inst_ids_gby_log(
        cls, choose_ap_results: List[Dict[str, Any]], bk_host_id__sub_inst_id_map: Dict[int, int]
    ) -> Dict[str, List[int]]:
        sub_inst_ids__gby_log: Dict[str, List[int]] = defaultdict(list)
        for choose_ap_result in choose_ap_results:
            sub_inst_id = bk_host_id__sub_inst_id_map[choose_ap_result["bk_host_id"]]
            sub_inst_ids__gby_log[choose_ap_result["log"]].append(sub_inst_id)
        return sub_inst_ids__gby_log

    def _execute(self, data, parent_data, common_data: AgentCommonData):
        ap_id_obj_map = common_data.ap_id_obj_map
        host_id_obj_map = common_data.host_id_obj_map
        ap_objs = models.AccessPoint.objects.all()
        subscription_instance_ids = common_data.subscription_instance_ids

        if not ap_objs:
            self.move_insts_to_failed(sub_inst_ids=subscription_instance_ids, log_content=_("自动选择接入点失败，请到全局配置新建接入点"))
            return

        detect_and_choose_ap_params_list: List[Dict[str, Any]] = []
        choose_ap_results: List[Dict[str, Any]] = []
        bk_host_id__sub_inst_id_map: Dict[int, int] = {}
        # 按云区域划分PAGENT
        pagent_host_ids__gby_cloud_id: Dict[int, List[int]] = defaultdict(list)

        for sub_inst in common_data.subscription_instances:
            bk_host_id = sub_inst.instance_info["host"]["bk_host_id"]
            host = host_id_obj_map[bk_host_id]

            bk_host_id__sub_inst_id_map[bk_host_id] = sub_inst.id

            # 主机已指定接入点
            if host.ap_id != constants.DEFAULT_AP_ID:
                choose_ap_results.append(
                    self.construct_return_data(
                        ap_id_obj_map=ap_id_obj_map,
                        bk_host_id=bk_host_id,
                        ap_id=host.ap_id,
                        log=_("当前主机已分配接入点[{ap_name}]").format(ap_name=ap_id_obj_map[host.ap_id].name),
                    )
                )

            # PAGENT 需要从所在云区域下随机选取一台存活的Proxy
            elif host.node_type == constants.NodeType.PAGENT:
                pagent_host_ids__gby_cloud_id[host.bk_cloud_id].append(host.bk_host_id)

            # 其余情况，从已有接入点中选择网络情况最好（to gse task svr）的一个
            else:
                detect_and_choose_ap_params_list.append(
                    {"sub_inst_id": sub_inst.id, "host": host, "ap_objs": ap_objs, "ap_id_obj_map": ap_id_obj_map}
                )

        # 处理 PAGENT 选择接入点的逻辑
        choose_ap_results.extend(
            self.handle_pagent_condition(
                pagent_host_ids__gby_cloud_id=pagent_host_ids__gby_cloud_id, ap_id_obj_map=ap_id_obj_map
            )
        )

        # 处理探测接入点的情况，这里采用多线程
        choose_ap_results.extend(
            self.handle_detect_condition(detect_and_choose_ap_params_list=detect_and_choose_ap_params_list)
        )

        self.handle_choose_ap_results(
            # 返回结果中的 None 表示执行过程中抛出异常，此处无需处理，需要过滤防止流程卡住
            choose_ap_results=list(filter(None, choose_ap_results)),
            bk_host_id__sub_inst_id_map=bk_host_id__sub_inst_id_map,
            host_id_obj_map=host_id_obj_map,
        )
