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
from typing import Any, Dict, List, Optional

from asgiref.sync import sync_to_async
from django.utils.translation import ugettext_lazy as _

from apps.backend import constants as backend_constants
from apps.backend.utils.wmi import execute_cmd
from apps.core.concurrent import controller
from apps.core.remote import conns
from apps.node_man import constants, models
from apps.utils import concurrent, exc

from .. import core
from ..common import remote
from .base import AgentBaseService, AgentCommonData


class ExternalRemoteConnHelper(remote.RemoteConnHelper):
    ap_id__info_map: Dict[int, Dict] = None

    def __init__(
        self, sub_inst_id: int, host: models.Host, identity_data: models.IdentityData, ap_id__info_map: Dict[int, Dict]
    ):
        self.ap_id__info_map = ap_id__info_map
        super().__init__(sub_inst_id, host, identity_data)


class ChooseAccessPointService(AgentBaseService, remote.RemoteServiceMixin):
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
        bk_host_id: int,
        ap_id: int,
        ap_name: str,
        log: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        构造接入点选择结果
        :param bk_host_id: 主机ID
        :param ap_id:
        :param ap_name:
        :param log: 日志，为空会根据ap_id 取值情况打印默认日志
        :return: 接入点选择结果
        """
        if not log:
            if ap_id == cls.FAILED_AP_ID:
                log = _("选择接入点失败")
            else:
                log = _("已选择 [{ap_name}] 作为本次安装的接入点").format(ap_name=ap_name)
        return {"bk_host_id": bk_host_id, "ap_id": ap_id, "log": log}

    @staticmethod
    def get_ping_cmd(host: models.Host, detect_host_info: Dict[str, Dict]) -> str:
        """
        获取 ping 命令
        :param host:
        :param detect_host_info:
        :return:
        """
        detect_host = (detect_host_info["inner_ip"], detect_host_info["inner_ip"])[
            host.bk_cloud_id == constants.DEFAULT_CLOUD
        ]
        if host.os_type == constants.OsType.WINDOWS:
            return f"ping {detect_host} -w 1000"
        else:
            return f"ping {detect_host} -i 0.1 -c 4 -s 100 -W 1 | tail -1 | awk -F '/' '{{print $5}}'"

    def parse_ping_time(self, os_type: str, ping_stdout: str) -> float:
        """
        解析探测耗时
        :param os_type:
        :param ping_stdout:
        :return:
        """
        if not ping_stdout:
            return self.MIN_PING_TIME

        if os_type.lower() == constants.OsType.WINDOWS.lower():
            try:
                ping_time_str = self.WIN_PING_PATTERN.findall(ping_stdout)[-1]
                return float(ping_time_str)
            except IndexError:
                return self.MIN_PING_TIME
        else:
            return float(ping_stdout)

    def handle_single_detect_result(
        self, remote_conn_helper: ExternalRemoteConnHelper, ping_times_gby_ap_id: Dict[int, List[float]]
    ) -> Dict[str, Any]:
        """
        处理探测结果
        :param remote_conn_helper:
        :param ping_times_gby_ap_id:
        :return:
        """
        detect_logs: List[str] = []
        # 最少的ping时间
        min_ping_time: float = self.MIN_PING_TIME
        # 最少ping时间的接入点id
        min_ping_ap_id: int = self.FAILED_AP_ID
        ap_id__ping_time_map: Dict[int, float] = {}
        for ap_id, ping_times in ping_times_gby_ap_id.items():
            ave = sum(ping_times) / len(ping_times)
            ap_id__ping_time_map[ap_id] = ave
            min_ping_ap_id = (min_ping_ap_id, ap_id)[ave < min_ping_time]
            min_ping_time = (min_ping_time, ave)[ave < min_ping_time]
            detect_logs.append(
                _("连接至接入点 [{ap_name}] 的平均延迟为 {ping_time}ms").format(
                    ap_name=remote_conn_helper.ap_id__info_map[ap_id]["name"], ping_time=round(ave, 3)
                )
            )

        self.log_info(
            sub_inst_ids=remote_conn_helper.sub_inst_id,
            log_content=_("主机 <--> 接入点网络情况检测结果：\n{detect_logs_str}".format(detect_logs_str="\n".join(detect_logs))),
        )

        if min_ping_ap_id == self.FAILED_AP_ID:
            return self.construct_return_data(
                bk_host_id=remote_conn_helper.host.bk_host_id,
                ap_id=self.FAILED_AP_ID,
                ap_name="",
                log=_("自动选择接入点失败，接入点均 ping 不可达"),
            )

        return self.construct_return_data(
            bk_host_id=remote_conn_helper.host.bk_host_id,
            ap_id=min_ping_ap_id,
            ap_name=remote_conn_helper.ap_id__info_map[min_ping_ap_id]["name"],
        )

    @exc.ExceptionHandler(exc_handler=remote.sub_inst_task_exc_handler)
    async def detect_host_to_aps_network__ssh(self, remote_conn_helper: ExternalRemoteConnHelper) -> Dict[str, Any]:
        """
        通过 SSH 通道探测网络情况
        :param remote_conn_helper:
        :return:
        """
        ping_times_gby_ap_id: Dict[int, List[float]] = defaultdict(list)
        for ap_id, ap_info in remote_conn_helper.ap_id__info_map.items():
            async with conns.AsyncsshConn(**remote_conn_helper.conns_init_params) as conn:
                for detect_host_info in ap_info["detect_host_infos"]:
                    ping_cmd = self.get_ping_cmd(remote_conn_helper.host, detect_host_info=detect_host_info)
                    run_output = await conn.run(
                        command=ping_cmd, check=False, timeout=backend_constants.SSH_RUN_TIMEOUT
                    )
                    ping_times_gby_ap_id[ap_id].append(
                        self.parse_ping_time(remote_conn_helper.host.os_type, run_output.stdout)
                    )
        return await sync_to_async(self.handle_single_detect_result)(remote_conn_helper, ping_times_gby_ap_id)

    @exc.ExceptionHandler(exc_handler=remote.sub_inst_task_exc_handler)
    def detect_host_to_aps_network__win(self, remote_conn_helper: ExternalRemoteConnHelper) -> Dict[str, Any]:
        """
        通过 Windows WMI 方式探测网络情况
        :param remote_conn_helper:
        :return:
        """
        ping_times_gby_ap_id: Dict[int, List[float]] = defaultdict(list)
        for ap_id, ap_info in remote_conn_helper.ap_id__info_map.items():
            for detect_host_info in ap_info["detect_host_infos"]:
                ping_cmd = self.get_ping_cmd(remote_conn_helper.host, detect_host_info=detect_host_info)
                stdout = execute_cmd(
                    ping_cmd,
                    remote_conn_helper.host.login_ip or remote_conn_helper.host.inner_ip,
                    remote_conn_helper.host.identity.account,
                    remote_conn_helper.host.identity.password,
                )["data"]
                ping_times_gby_ap_id[ap_id].append(self.parse_ping_time(remote_conn_helper.host.os_type, stdout))
        return self.handle_single_detect_result(remote_conn_helper, ping_times_gby_ap_id)

    @controller.ConcurrentController(
        data_list_name="remote_conn_helpers",
        batch_call_func=concurrent.batch_call,
        get_config_dict_func=core.get_config_dict,
        get_config_dict_kwargs={"config_name": core.ServiceCCConfigName.SSH.value},
    )
    def handle_detect_condition__ssh(self, remote_conn_helpers: List[ExternalRemoteConnHelper]):
        """
        批量处理 SSH 探测
        :param remote_conn_helpers:
        :return:
        """
        params_list = [{"remote_conn_helper": remote_conn_helper} for remote_conn_helper in remote_conn_helpers]
        return concurrent.batch_call_coroutine(func=self.detect_host_to_aps_network__ssh, params_list=params_list)

    @controller.ConcurrentController(
        data_list_name="remote_conn_helpers",
        batch_call_func=concurrent.batch_call,
        get_config_dict_func=core.get_config_dict,
        get_config_dict_kwargs={"config_name": core.ServiceCCConfigName.WMIEXE.value},
    )
    def handle_detect_condition__win(self, remote_conn_helpers: List[ExternalRemoteConnHelper]):
        """
        批量处理 Windows 探测
        :param remote_conn_helpers:
        :return:
        """
        params_list = [{"remote_conn_helper": remote_conn_helper} for remote_conn_helper in remote_conn_helpers]
        return concurrent.batch_call_serial(func=self.detect_host_to_aps_network__win, params_list=params_list)

    def handle_detect_condition(self, remote_conn_helpers: List[ExternalRemoteConnHelper]) -> List[Dict[str, Any]]:
        """
        处理需要探测选择接入点的情况
        :param remote_conn_helpers:
        :return: 接入点选择结果列表
        """
        if not remote_conn_helpers:
            return []

        # 通过 SSH 通道探测网络
        ssh_remote_conn_helpers: List[ExternalRemoteConnHelper] = []
        windows_remote_conn_helpers: List[ExternalRemoteConnHelper] = []
        for remote_conn_helper in remote_conn_helpers:
            if remote_conn_helper.host.os_type == constants.OsType.WINDOWS:
                windows_remote_conn_helpers.append(remote_conn_helper)
            else:
                ssh_remote_conn_helpers.append(remote_conn_helper)

        remote_conn_helpers_gby_result_type = self.bulk_check_ssh(remote_conn_helpers=windows_remote_conn_helpers)

        ssh_remote_conn_helpers.extend(
            remote_conn_helpers_gby_result_type.get(remote.SshCheckResultType.AVAILABLE.value, [])
        )
        windows_ch_remote_conn_helpers = remote_conn_helpers_gby_result_type.get(
            remote.SshCheckResultType.UNAVAILABLE.value, []
        )

        return self.handle_detect_condition__ssh(
            remote_conn_helpers=ssh_remote_conn_helpers
        ) + self.handle_detect_condition__win(remote_conn_helpers=windows_ch_remote_conn_helpers)

    def handle_pagent_condition(
        self,
        pagent_host_ids__gby_cloud_id: Dict[int, List[int]],
        ap_id_obj_map: Dict[int, models.AccessPoint],
    ) -> List[Dict[str, Any]]:
        """
        处理Pagent的情况，随机选择存活接入点
        :param pagent_host_ids__gby_cloud_id: PAgent 主机ID - 云区域ID 映射
        :param ap_id_obj_map: 接入点ID - 信息映射
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
                            bk_host_id=bk_host_id,
                            ap_id=self.FAILED_AP_ID,
                            ap_name="",
                            log=_("云区域 -> {bk_cloud_id} 下无存活的 Proxy").format(bk_cloud_id=bk_cloud_id),
                        )
                    )
                continue

            for bk_host_id in bk_host_ids:
                alive_proxy_host_id = random.choice(alive_proxy_host_ids_in_cloud)
                ap_id = proxy_host_id__ap_id_map[alive_proxy_host_id]
                choose_ap_results.append(
                    self.construct_return_data(bk_host_id=bk_host_id, ap_id=ap_id, ap_name=ap_id_obj_map[ap_id].name)
                )
        return choose_ap_results

    def handle_proxy_condition(
        self,
        proxy_host_ids__gby_cloud_id: Dict[int, List[int]],
        ap_id_obj_map: Dict[int, models.AccessPoint],
    ) -> List[Dict[str, Any]]:
        choose_ap_results = []
        cloud_id__info_map: Dict[int, Dict[str, Any]] = {
            cloud_info["bk_cloud_id"]: {"ap_id": cloud_info["ap_id"], "bk_cloud_name": cloud_info["bk_cloud_name"]}
            for cloud_info in models.Cloud.objects.filter(bk_cloud_id__in=proxy_host_ids__gby_cloud_id.keys()).values(
                "bk_cloud_id", "ap_id", "bk_cloud_name"
            )
        }
        for cloud_id, proxy_host_ids in proxy_host_ids__gby_cloud_id.items():
            cloud_info = cloud_id__info_map[cloud_id]
            choose_ap_results.extend(
                [
                    self.construct_return_data(
                        bk_host_id=proxy_host_id,
                        ap_id=cloud_info["ap_id"],
                        ap_name=ap_id_obj_map[cloud_info["ap_id"]].name,
                        log=_("已选择 Proxy 所在云区域「{bk_cloud_name}」[{bk_cloud_id}] 指定的接入点 [{ap_name}]").format(
                            bk_cloud_name=cloud_info["bk_cloud_name"],
                            bk_cloud_id=cloud_id,
                            ap_name=ap_id_obj_map[cloud_info["ap_id"]].name,
                        ),
                    )
                    for proxy_host_id in proxy_host_ids
                ]
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

        ap_id__info_map: Dict[int, Dict] = {}
        for ap_obj in ap_objs:
            ap_id__info_map[ap_obj.id] = {
                "ap_id": ap_obj.id,
                "name": ap_obj.name,
                "detect_host_infos": ap_obj.taskserver,
            }

        host_id_identity_map = {
            identity.bk_host_id: identity
            for identity in models.IdentityData.objects.filter(bk_host_id__in=common_data.bk_host_ids)
        }
        remote_conn_helpers: List[ExternalRemoteConnHelper] = []
        choose_ap_results: List[Dict[str, Any]] = []
        bk_host_id__sub_inst_id_map: Dict[int, int] = {}
        proxy_host_ids__gby_cloud_id: Dict[int, List[int]] = defaultdict(list)
        # 按云区域划分PAGENT
        pagent_host_ids__gby_cloud_id: Dict[int, List[int]] = defaultdict(list)

        for sub_inst in common_data.subscription_instances:
            bk_host_id = sub_inst.instance_info["host"]["bk_host_id"]
            host = host_id_obj_map[bk_host_id]

            bk_host_id__sub_inst_id_map[bk_host_id] = sub_inst.id

            # Proxy 设置为所在云区域的接入点，每次都需要重置，防止云区域修改后 Proxy 未同步
            if host.node_type == constants.NodeType.PROXY:
                proxy_host_ids__gby_cloud_id[host.bk_cloud_id].append(host.bk_host_id)
            # 主机已指定接入点
            elif host.ap_id != constants.DEFAULT_AP_ID:
                choose_ap_results.append(
                    self.construct_return_data(
                        ap_id=host.ap_id,
                        ap_name=ap_id_obj_map[host.ap_id].name,
                        bk_host_id=bk_host_id,
                        log=_("当前主机已分配接入点 [{ap_name}]").format(ap_name=ap_id_obj_map[host.ap_id].name),
                    )
                )

            # PAGENT 需要从所在云区域下随机选取一台存活的Proxy
            elif host.node_type == constants.NodeType.PAGENT:
                pagent_host_ids__gby_cloud_id[host.bk_cloud_id].append(host.bk_host_id)

            # 其余情况，从已有接入点中选择网络情况最好（to gse task svr）的一个
            else:
                remote_conn_helpers.append(
                    ExternalRemoteConnHelper(
                        sub_inst_id=sub_inst.id,
                        host=host,
                        # 避免部分主机认证信息丢失的情况下，通过host.identity重新创建来兜底保证不会异常
                        identity_data=host_id_identity_map[host.bk_host_id] or host.identity,
                        ap_id__info_map=ap_id__info_map,
                    )
                )

        # ap_id_obj_map 包含默认值接入点ID，用于处理 Proxy & PAgent ap_id 为 DEFAULT_AP_ID 的情况
        # 处理 Proxy 选择所在云区域接入点的情况
        choose_ap_results.extend(
            self.handle_proxy_condition(
                proxy_host_ids__gby_cloud_id=proxy_host_ids__gby_cloud_id, ap_id_obj_map=ap_id_obj_map
            )
        )

        # 处理 PAGENT 选择接入点的情况
        choose_ap_results.extend(
            self.handle_pagent_condition(
                pagent_host_ids__gby_cloud_id=pagent_host_ids__gby_cloud_id, ap_id_obj_map=ap_id_obj_map
            )
        )

        # 处理探测接入点的情况
        choose_ap_results.extend(self.handle_detect_condition(remote_conn_helpers))

        self.handle_choose_ap_results(
            # 返回结果中的 None 表示执行过程中抛出异常，此处无需处理，需要过滤防止流程卡住
            choose_ap_results=list(filter(None, choose_ap_results)),
            bk_host_id__sub_inst_id_map=bk_host_id__sub_inst_id_map,
            host_id_obj_map=host_id_obj_map,
        )
