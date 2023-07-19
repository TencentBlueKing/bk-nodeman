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
import copy
import logging
from typing import Any, Dict, List, Optional, Set, Union

from django.conf import settings
from django.core.paginator import Paginator
from django.db import transaction
from django.utils import timezone
from django.utils.translation import get_language
from django.utils.translation import ugettext_lazy as _

from apps.backend.subscription.errors import SubscriptionTaskNotReadyError
from apps.exceptions import ApiResultError
from apps.node_man import constants, exceptions, models, tools
from apps.node_man.handlers import validator
from apps.node_man.handlers.ap import APHandler
from apps.node_man.handlers.cloud import CloudHandler
from apps.node_man.handlers.cmdb import CmdbHandler
from apps.node_man.handlers.host import HostHandler
from apps.utils import APIModel
from apps.utils.basic import filter_values, to_int_or_default
from apps.utils.local import get_request_username
from apps.utils.time_tools import local_dt_str2utc_dt
from common.api import NodeApi

logger = logging.getLogger("app")


class JobHandler(APIModel):
    def __init__(self, job_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.job_id = job_id

    def _get_data(self) -> models.Job:
        try:
            return models.Job.objects.get(pk=self.job_id)
        except models.Job.DoesNotExist:
            raise exceptions.JobDostNotExistsError(_("不存在ID为{job_id}的任务").format(job_id=self.job_id))

    def ugettext_to_unicode(self, ip_filter_list: list):
        """
        针对ip_filter_list里的ugettext_lazy做字符串化的操作
        :param ip_filter_list: ip过滤列表
        :return: 格式化后的ip过滤列表
        """
        # ugettext_lazy需要转为unicode才可进行序列化
        for filter_info in ip_filter_list:
            filter_info["msg"] = str(filter_info["msg"])
        return ip_filter_list

    def check_ap_and_biz_scope(self, node_type: str, host: dict, cloud_info: dict):
        """
        返回主机的接入点、业务范围、节点类型。
        兼容订阅任务版注册<br>
        如果是非直连区域，获得该管控区域下的ap_id为空<br>
        如果是直连区域，ap_id直接从参数拿, 如果是proxy，则ap_id为空<br>
        :param node_type: 节点类型
        :param host: 主机信息
        :param cloud_info: 管控区域信息
        :return:
        """
        if node_type == constants.NodeType.AGENT:
            if host["bk_cloud_id"] == constants.DEFAULT_CLOUD:
                # 根据bk_cloud_id判断是否为AGENT
                host_ap_id = host["ap_id"]
                host_node_type = constants.NodeType.AGENT
            else:
                # 根据bk_cloud_id判断是否为PAGENT
                # 如果传了ap_id优先使用传入的以适配重载配置
                host_ap_id = host.get("ap_id") or cloud_info.get(host["bk_cloud_id"], {}).get("ap_id", "")
                host_node_type = constants.NodeType.PAGENT
        else:
            # PROXY
            # 如果传了ap_id优先使用传入的以适配重载配置
            host_ap_id = host.get("ap_id") or cloud_info.get(host["bk_cloud_id"], {}).get("ap_id", "")
            host_node_type = constants.NodeType.PROXY

        return host_ap_id, host_node_type

    def get_commands(self, request_bk_host_id: int, is_uninstall: bool):
        """
        获取命令
        :param request_bk_host_id: 主机ID
        :param is_uninstall: 是否为卸载
        :return: 主机ID，命令列表, 提示信息
        """
        job = self.data
        try:
            host: models.Host = models.Host.objects.get(bk_host_id=request_bk_host_id)
        except models.Host.DoesNotExist:
            raise exceptions.HostNotExists()

        host_id__pipeline_id_map: Dict[int, str] = {}
        # 主机ID - 订阅实例ID映射
        host_id__sub_inst_id_map: Dict[int, int] = {}
        # 获取任务状态
        task_result = NodeApi.get_subscription_task_status(
            {"subscription_id": job.subscription_id, "task_id_list": job.task_id_list, "return_all": True}
        )
        for result in task_result["list"]:
            bk_host_id = result["instance_info"]["host"].get("bk_host_id")
            if not bk_host_id:
                # 主机没注册成功
                continue
            host_id__sub_inst_id_map[bk_host_id] = result["record_id"]
            # 获取每台主机安装任务的pipeline_id
            sub_steps = result["steps"][0]["target_hosts"][0]["sub_steps"]
            for step in sub_steps:
                if step["node_name"] in ["安装", "卸载Agent", "Uninstall Agent", "Install"] and (
                    step["status"] in [constants.JobStatusType.RUNNING, constants.JobStatusType.SUCCESS]
                ):
                    pipeline_id = step["pipeline_id"]
                    host_id__pipeline_id_map[bk_host_id] = pipeline_id

        if request_bk_host_id not in host_id__pipeline_id_map.keys():
            return {"status": constants.JobStatusType.PENDING}

        command_solutions: Dict[str, Union[List[str], str]] = NodeApi.fetch_commands(
            {
                "bk_host_id": host.bk_host_id,
                "host_install_pipeline_id": host_id__pipeline_id_map[host.bk_host_id],
                "is_uninstall": is_uninstall,
                "sub_inst_id": host_id__sub_inst_id_map[host.bk_host_id],
            }
        )

        return command_solutions

    def list(self, params: dict, username: str):
        """
        Job 任务历史列表
        :param params: 请求参数的字典
        :param username: 用户名
        """

        kwargs = {
            **tools.JobTools.parse_job_list_filter_kwargs(query_params=params),
            "status__in": params.get("status"),
            "created_by__in": params.get("created_by"),
            "start_time__gte": params.get("start_time"),
            "start_time__lte": params.get("end_time"),
            "is_auto_trigger": False if params.get("hide_auto_trigger_job") else None,
        }

        # 获得业务id与名字的映射关系(用户有权限获取的业务)
        all_biz_info = CmdbHandler().biz_id_name_without_permission()
        biz_info = CmdbHandler().biz_id_name({"action": constants.IamActionType.task_history_view})
        biz_permission = list(biz_info.keys())

        # 用户搜索的业务
        search_biz = []
        if params.get("bk_biz_id"):
            # 如果有带筛选条件，则只返回筛选且有权业务的主机
            search_biz = [bk_biz_id for bk_biz_id in params["bk_biz_id"] if bk_biz_id in biz_info]

        if params.get("job_id"):
            job_ids = set()
            for job_id_var in params["job_id"]:
                # 获得合法整型
                job_id = to_int_or_default(job_id_var)
                if job_id is None:
                    continue
                job_ids.add(job_id)
            kwargs["id__in"] = job_ids

        # 过滤None值并筛选Job
        # 此处不过滤空列表（filter_empty=False），job_id, job_type 存在二次解析，若全部值非法得到的是空列表，期望应是查不到数据
        job_result = models.Job.objects.filter(**filter_values(kwargs))

        if params.get("sort"):
            sort_head = params["sort"]["head"]
            job_result = job_result.extra(select={sort_head: f"JSON_EXTRACT(statistics, '$.{sort_head}')"})
            if params["sort"]["sort_type"] == constants.SortType.DEC:
                job_result = job_result.order_by(str("-") + sort_head)
            else:
                job_result = job_result.order_by(sort_head)

        # TODO 全量拉取，待优化
        job_result = job_result.values()

        job_list = []
        for job in job_result:
            if not job["end_time"]:
                job["cost_time"] = f'{(timezone.now() - job["start_time"]).seconds}'
            else:
                job["cost_time"] = f'{(job["end_time"] - job["start_time"]).seconds}'
            job["bk_biz_scope_display"] = [all_biz_info.get(biz) for biz in job["bk_biz_scope"]]
            job["job_type_display"] = constants.JOB_TYPE_DICT.get(job["job_type"])

            # 如果任务没有业务则不显示
            if not job["bk_biz_scope"]:
                continue

            # 判断权限
            if set(job["bk_biz_scope"]) - set(biz_permission) == set():
                if set(job["bk_biz_scope"]) - set(search_biz) != set(job["bk_biz_scope"]):
                    # 此种情况说明job业务范围包括查询业务的其中一个
                    job_list.append(job)
                    continue
                elif not search_biz:
                    # 查询所有业务情况
                    job_list.append(job)
                    continue
                elif search_biz == biz_permission:
                    job_list.append(job)
                    continue

            # 创建者是自己
            if job["created_by"] == username and not params.get("bk_biz_id"):
                job_list.append(job)
                continue

        # 分页
        paginator = Paginator(job_list, params["pagesize"])
        job_page: List[Dict[str, Any]] = paginator.page(params["page"]).object_list

        # 填充策略名称
        sub_infos = models.Subscription.objects.filter(
            id__in=[job["subscription_id"] for job in job_page], show_deleted=True
        ).values("id", "name")

        # 建立订阅ID和订阅详细信息的映射
        sub_id__sub_info_map = {sub_info["id"]: sub_info for sub_info in sub_infos}

        # 预处理数据：字段填充，计算等
        for job in job_page:
            job.update(tools.JobTools.unzip_job_type(job["job_type"]))

            # 填充订阅相关信息
            job["policy_name"] = sub_id__sub_info_map.get(job["subscription_id"], {}).get("name")

        return {"total": len(job_list), "list": job_page}

    def install(
        self,
        hosts: List[Dict[str, Any]],
        op_type: str,
        node_type: str,
        job_type: str,
        ticket: str,
        extra_params: Dict[str, Any],
        extra_config: Dict[str, Any],
    ):
        """
        Job 任务处理器
        :param hosts: 主机列表
        :param op_type: 操作类型
        :param node_type: 节点类型
        :param job_type: 任务作业类型
        :param ticket: 请求参数的字典
        :param extra_params: 额外的订阅参数
        :param extra_config: 额外的订阅配置参数
        """

        # 获取Hosts中的cloud_id列表、ap_id列表、内网、外网、登录IP列表、bk_biz_scope列表
        ap_ids = set()
        is_manual = set()
        bk_biz_scope = set()
        bk_cloud_ids = set()
        inner_ips_info: Dict[str, Set[str]] = {"inner_ips": set(), "inner_ipv6s": set()}

        for host in hosts:
            bk_cloud_ids.add(host["bk_cloud_id"])
            bk_biz_scope.add(host["bk_biz_id"])
            is_manual.add(host["is_manual"])

            # 遍历需要支持的 IP 字段，汇总安装信息中存在该 IP 字段的值
            if host.get("inner_ip"):
                inner_ips_info["inner_ips"].add(host["inner_ip"])
            if host.get("inner_ipv6"):
                inner_ips_info["inner_ipv6s"].add(host["inner_ipv6"])

            # 用户ticket，用于后台异步执行时调用第三方接口使用
            host["ticket"] = ticket
            if host.get("ap_id"):
                ap_ids.add(host["ap_id"])

        # 如果混合了【手动安装】，【自动安装】则不允许通过
        # 此处暂不合入 job validator.
        if len(is_manual) > 1:
            raise exceptions.MixedOperationError
        else:
            is_manual = list(is_manual)[0]

        # 获得所有的业务列表
        # 格式 { bk_biz_id: bk_biz_name , ...}
        biz_info = CmdbHandler().biz_id_name_without_permission()
        # 获得相应管控区域 id, name, ap_id
        # 格式 { cloud_id: {'bk_cloud_name': name, 'ap_id': id}, ...}
        cloud_info = CloudHandler().list_cloud_info(bk_cloud_ids)

        # 获得接入点列表
        # 格式 { id: name, ...}
        ap_id_name = APHandler().ap_list(ap_ids)

        # 获得用户输入的ip是否存在于数据库中
        # 格式 { bk_cloud_id+ip: { 'bk_host_id': ..., 'bk_biz_id': ..., 'node_type': ...}}
        host_infos_gby_ip_key: Dict[str, List[Dict[str, Any]]] = HostHandler.get_host_infos_gby_ip_key(
            ips=inner_ips_info["inner_ips"], ip_version=constants.CmdbIpVersion.V4.value
        )
        host_infos_gby_ip_key.update(
            HostHandler.get_host_infos_gby_ip_key(
                ips=inner_ips_info["inner_ipv6s"], ip_version=constants.CmdbIpVersion.V6.value
            )
        )

        # 对数据进行校验
        # 重装则校验IP是否存在，存在才可重装
        ip_filter_list, accept_list, proxy_not_alive = validator.install_validate(
            hosts, op_type, node_type, job_type, biz_info, cloud_info, ap_id_name, host_infos_gby_ip_key
        )

        if proxy_not_alive:
            raise exceptions.AliveProxyNotExistsError(
                context="不存在可用代理", data={"job_id": "", "ip_filter": self.ugettext_to_unicode(proxy_not_alive)}
            )

        if not accept_list:
            # 如果都被过滤了
            raise exceptions.AllIpFiltered(data={"job_id": "", "ip_filter": self.ugettext_to_unicode(ip_filter_list)})

        if any(
            [
                op_type in [constants.OpType.INSTALL, constants.OpType.REPLACE, constants.OpType.RELOAD],
                # 开启动态主机配置协议适配时，通过基础信息进行重装
                settings.BKAPP_ENABLE_DHCP and op_type in [constants.OpType.REINSTALL],
            ]
        ):
            # 安装、替换Proxy操作
            subscription_nodes = self.subscription_install(accept_list, node_type, cloud_info, biz_info)
            subscription = self.create_subscription(
                job_type, subscription_nodes, extra_params=extra_params, extra_config=extra_config
            )
        else:
            # 重装、卸载等操作
            # 此步骤需要校验密码、秘钥
            subscription_nodes, ip_filter_list = self.update_host(accept_list, ip_filter_list, is_manual)
            if not subscription_nodes:
                raise exceptions.AllIpFiltered(
                    data={"job_id": "", "ip_filter": self.ugettext_to_unicode(ip_filter_list)}
                )
            subscription = self.create_subscription(
                job_type, subscription_nodes, extra_params=extra_params, extra_config=extra_config
            )

        # ugettext_lazy 需要转为 unicode 才可进行序列化
        ip_filter_list = self.ugettext_to_unicode(ip_filter_list)

        create_job_result: Dict[str, Any] = tools.JobTools.create_job(
            job_type=job_type,
            subscription_id=subscription["subscription_id"],
            task_id=subscription["task_id"],
            bk_biz_scope=bk_biz_scope,
            statistics={
                "success_count": 0,
                "failed_count": len(ip_filter_list),
                "pending_count": len(subscription_nodes),
                "running_count": 0,
                "total_count": len(ip_filter_list) + len(subscription_nodes),
            },
            error_hosts=ip_filter_list,
        )

        return {**create_job_result, "ip_filter": ip_filter_list}

    def subscription_install(self, accept_list: list, node_type: str, cloud_info: dict, biz_info: dict):
        """
        Job 订阅安装任务
        :param accept_list: 所有通过校验需要新安装的主机
        :param node_type: 节点类型
        :param cloud_info: 管控区域信息
        :param biz_info: 业务ID及其对应的名称
        :return
        """

        # 节点变量，用于后续订阅任务注册主机，安装等操作
        subscription_nodes = []
        cipher = tools.HostTools.get_asymmetric_cipher()
        for host in accept_list:
            host_ap_id, host_node_type = self.check_ap_and_biz_scope(node_type, host, cloud_info)
            instance_info = copy.deepcopy(host)
            instance_info.update(
                {
                    "is_manual": host["is_manual"],
                    "ap_id": host_ap_id,
                    "install_channel_id": host.get("install_channel_id"),
                    "bk_os_type": constants.BK_OS_TYPE[host["os_type"]],
                    "bk_host_innerip": host.get("inner_ip", ""),
                    "bk_host_innerip_v6": host.get("inner_ipv6", ""),
                    "bk_host_outerip": host.get("outer_ip", ""),
                    "bk_host_outerip_v6": host.get("outer_ipv6", ""),
                    "login_ip": host.get("login_ip", ""),
                    "username": get_request_username(),
                    "bk_biz_id": host["bk_biz_id"],
                    "bk_biz_name": biz_info.get(host["bk_biz_id"]),
                    "bk_cloud_id": host["bk_cloud_id"],
                    "bk_cloud_name": str(cloud_info.get(host["bk_cloud_id"], {}).get("bk_cloud_name")),
                    "bk_addressing": host["bk_addressing"],
                    "bk_supplier_account": settings.DEFAULT_SUPPLIER_ACCOUNT,
                    "host_node_type": host_node_type,
                    "os_type": host["os_type"],
                    "auth_type": host.get("auth_type", "MANUAL"),
                    "account": host.get("account", "MANUAL"),
                    "port": host.get("port"),
                    "password": tools.HostTools.USE_ASYMMETRIC_PREFIX + cipher.encrypt(host.get("password", "")),
                    "key": tools.HostTools.USE_ASYMMETRIC_PREFIX + cipher.encrypt(host.get("key", "")),
                    "retention": host.get("retention", 1),
                    "peer_exchange_switch_for_agent": host.get("peer_exchange_switch_for_agent"),
                    "bt_speed_limit": host.get("bt_speed_limit"),
                    "enable_compression": host.get("enable_compression"),
                    "agent_setup_extra_info": {"force_update_agent_id": host.get("force_update_agent_id", False)},
                }
            )

            if host_node_type == constants.NodeType.PROXY and host.get("data_path"):
                # proxy增加数据文件路径
                instance_info.update({"data_path": host["data_path"]})

            if host.get("bk_host_id"):
                instance_info.update({"bk_host_id": host.get("bk_host_id")})

            # 写入ticket
            if host.get("auth_type") == constants.AuthType.TJJ_PASSWORD:
                instance_info["extra_data"] = {"oa_ticket": host["ticket"]}

            # 写入节点变量
            subscription_nodes.append(
                {
                    "bk_supplier_account": settings.DEFAULT_SUPPLIER_ACCOUNT,
                    "bk_cloud_id": host["bk_cloud_id"],
                    "ip": host.get("inner_ip", "") or host.get("inner_ipv6", ""),
                    "instance_info": instance_info,
                }
            )

        return subscription_nodes

    @staticmethod
    def update_host(accept_list: list, ip_filter_list: list, is_manual: bool = False):
        """
        用于更新identity认证信息
        :param accept_list: 所有需要修改的数据
        :param ip_filter_list: 过滤数据
        :param is_manual: 是否手动安装
        """

        identity_to_create = []
        host_to_create = []

        identity_id_to_delete = []
        host_id_to_delete = []

        # 获得需要修改的认证信息的rentention
        if not is_manual:
            # 非手动模式需要认证信息
            identity_info = {
                identity["bk_host_id"]: {
                    "auth_type": identity["auth_type"],
                    "retention": identity["retention"],
                    "account": identity["account"],
                    "password": identity["password"],
                    "key": identity["key"],
                    "port": identity["port"],
                    "extra_data": identity["extra_data"],
                }
                for identity in models.IdentityData.objects.filter(
                    bk_host_id__in=[host["bk_host_id"] for host in accept_list]
                ).values("bk_host_id", "auth_type", "retention", "account", "password", "key", "port", "extra_data")
            }
        else:
            # 手动模式无需认证信息
            identity_info = {}

        host_info = {
            host["bk_host_id"]: {
                "bk_host_id": host["bk_host_id"],
                "bk_biz_id": host["bk_biz_id"],
                "bk_cloud_id": host["bk_cloud_id"],
                "inner_ip": host["inner_ip"],
                "inner_ipv6": host["inner_ipv6"],
                "outer_ip": host["outer_ip"],
                "outer_ipv6": host["outer_ipv6"],
                "login_ip": host["login_ip"],
                "data_ip": host["data_ip"],
                "os_type": host["os_type"],
                "node_type": host["node_type"],
                "ap_id": host["ap_id"],
                "install_channel_id": host["install_channel_id"],
                "upstream_nodes": host["upstream_nodes"],
                "created_at": host["created_at"],
                "updated_at": host["updated_at"],
                "is_manual": host["is_manual"],
                "extra_data": host["extra_data"],
            }
            for host in models.Host.objects.filter(bk_host_id__in=[host["bk_host_id"] for host in accept_list]).values()
        }

        # 认证信息和Host校验
        update_data_info, ip_filter_list = validator.bulk_update_validate(
            host_info, accept_list, identity_info, ip_filter_list, is_manual
        )

        # 准备对需要修改的identity数据bulk_create
        for host in update_data_info["modified_identity"]:
            update_time = timezone.now()
            the_identity = identity_info[host["bk_host_id"]]
            # 更新ticket
            if host.get("auth_type") == constants.AuthType.TJJ_PASSWORD:
                extra_data = {"oa_ticket": host.get("ticket")}
            else:
                extra_data = the_identity["extra_data"]
            identity_to_create.append(
                models.IdentityData(
                    **{
                        "bk_host_id": host["bk_host_id"],
                        "auth_type": host.get("auth_type", the_identity["auth_type"]),
                        "account": host.get("account", the_identity["account"]),
                        "password": host.get("password", the_identity["password"]),
                        "port": host.get("port", the_identity["port"]),
                        "key": host.get("key", the_identity["key"]),
                        "retention": host.get("retention", the_identity["retention"]),
                        "extra_data": extra_data,
                        "updated_at": update_time,
                    }
                )
            )
            identity_id_to_delete.append(host["bk_host_id"])

        # 准备对需要修改的Host数据bulk_create
        for host in update_data_info["modified_host"]:
            # 如果 操作系统 或 接入点 发生修改
            update_time = timezone.now()
            origin_host = host_info[host["bk_host_id"]]
            host_extra_data = {
                "peer_exchange_switch_for_agent": host.get(
                    "peer_exchange_switch_for_agent",
                    origin_host["extra_data"].get("peer_exchange_switch_for_agent"),
                ),
                "bt_speed_limit": host.get("bt_speed_limit", origin_host["extra_data"].get("bt_speed_limit")),
                "enable_compression": host.get(
                    "enable_compression", origin_host["extra_data"].get("enable_compression")
                ),
            }
            # 更新为新传入或者使用原来的数据
            if host.get("data_path") or origin_host["extra_data"].get("data_path"):
                host_extra_data.update(
                    {"data_path": host.get("data_path") or origin_host["extra_data"].get("data_path")}
                )
            host_to_create.append(
                models.Host(
                    **{
                        "bk_host_id": origin_host["bk_host_id"],
                        "bk_biz_id": origin_host["bk_biz_id"],
                        "bk_cloud_id": origin_host["bk_cloud_id"],
                        "inner_ip": origin_host["inner_ip"],
                        "outer_ip": origin_host["outer_ip"],
                        "inner_ipv6": origin_host["inner_ipv6"],
                        "outer_ipv6": origin_host["outer_ipv6"],
                        "login_ip": host.get("login_ip", origin_host["login_ip"]),
                        "data_ip": origin_host["data_ip"],
                        "os_type": host.get("os_type", origin_host["os_type"]),
                        "node_type": origin_host["node_type"],
                        "ap_id": host.get("ap_id", origin_host["ap_id"]),
                        "install_channel_id": host.get("install_channel_id", origin_host["install_channel_id"]),
                        "upstream_nodes": origin_host["upstream_nodes"],
                        "created_at": origin_host["created_at"],
                        "updated_at": update_time,
                        "is_manual": is_manual,
                        "extra_data": host_extra_data,
                    }
                )
            )
            host_id_to_delete.append(host["bk_host_id"])

        with transaction.atomic():
            # 修改是否手动安装为is_manual
            host_id_no_modified = [host["bk_host_id"] for host in update_data_info["not_modified_host"]]
            models.Host.objects.filter(bk_host_id__in=host_id_no_modified).update(is_manual=is_manual)
            # 删除需要修改的原数据
            models.IdentityData.objects.filter(bk_host_id__in=identity_id_to_delete).delete()
            models.Host.objects.filter(bk_host_id__in=host_id_to_delete).delete()
            # bulk_create创建新的信息
            models.IdentityData.objects.bulk_create(identity_to_create)
            models.Host.objects.bulk_create(host_to_create)

        return update_data_info["subscription_host_ids"], ip_filter_list

    def operate(self, job_type, bk_host_ids, bk_biz_scope, extra_params, extra_config):
        """
        用于只有bk_host_id参数的下线、重启等操作
        """
        # 校验器进行校验

        subscription = self.create_subscription(
            job_type, bk_host_ids, extra_params=extra_params, extra_config=extra_config
        )

        return tools.JobTools.create_job(
            job_type=job_type,
            subscription_id=subscription["subscription_id"],
            task_id=subscription["task_id"],
            bk_biz_scope=bk_biz_scope,
            statistics={
                "success_count": 0,
                "failed_count": 0,
                "pending_count": len(bk_host_ids),
                "running_count": 0,
                "total_count": len(bk_host_ids),
            },
        )

    def create_subscription(
        self,
        job_type,
        nodes: list,
        extra_params: Optional[Dict[str, Any]] = None,
        extra_config: Optional[Dict[str, Any]] = None,
    ):
        """
        创建订阅任务
        :param job_type: INSTALL_AGENT
        :param nodes: 任务范围
        :param extra_params: 额外的参数
        :param extra_config: 额外的配置
        1.重装、卸载等操作
        [{"bk_host_id": 1}, {"bk_host_id": 2}]

        2.新装，替换：
        [
            {
                "bk_supplier_account": "0",
                "bk_cloud_id": 0,
                "ip": "127.0.0.1",
                "instance_info": {
                    "ap_id": 1,
                    "bk_os_type": "1",
                    "bk_host_innerip": "127.0.0.1",
                    "bk_host_outerip": "127.0.0.1",
                    "bk_biz_id": 2,
                    "bk_biz_name": "蓝鲸",
                    "bk_cloud_id": 0,
                    "bk_cloud_name": "default area",
                    "bk_supplier_account": "0",
                    "auth_type": "PASSWORD",
                    "account": "root",
                    "port": 22,
                    "auth_type": "PASSWORD",
                    "password": "xxx",
                    "key": "",
                    "retention": 1
                }
            }
        ]
        :return:
        """
        extra_params = extra_params or {}
        extra_config = extra_config or {}
        params = {
            "run_immediately": True,
            "bk_app_code": "nodeman",
            "bk_username": "admin",
            "scope": {"node_type": "INSTANCE", "object_type": "HOST", "nodes": nodes},
            "steps": [
                {
                    "id": "agent",
                    "type": "AGENT",
                    "config": {"job_type": job_type, **extra_config},
                    "params": {"context": {}, "blueking_language": get_language(), **extra_params},
                }
            ],
        }
        return NodeApi.create_subscription(params)

    def retry(self, instance_id_list: List[str] = None):
        """
        重试部分实例或主机
        :param instance_id_list: 需重试的实例列表
        :return: task_id_list
        """
        params = {
            "subscription_id": self.data.subscription_id,
            "task_id_list": self.data.task_id_list,
            "instance_id_list": instance_id_list,
        }
        task_id = NodeApi.retry_subscription_task(params)["task_id"]
        self.data.task_id_list.append(task_id)
        if instance_id_list:
            running_count = self.data.statistics["running_count"] + len(instance_id_list)
            failed_count = self.data.statistics["failed_count"] - len(instance_id_list)
        else:
            running_count = self.data.statistics["failed_count"]
            failed_count = 0
        self.data.statistics.update({"running_count": running_count, "failed_count": failed_count})
        self.data.status = constants.JobStatusType.RUNNING
        self.data.save()
        return self.data.task_id_list

    def revoke(self, instance_id_list: list):
        params = {
            "subscription_id": self.data.subscription_id,
        }
        if instance_id_list:
            params["instance_id_list"] = instance_id_list
        NodeApi.revoke_subscription_task(params)
        self.data.status = constants.JobStatusType.TERMINATED
        self.data.end_time = timezone.now()
        self.data.save()
        return self.data.task_id_list

    def retrieve(self, params: Dict[str, Any]):
        """
        任务详情页接口
        :param params: 接口请求参数
        """
        if self.data.task_id_list:

            try:
                task_result = NodeApi.get_subscription_task_status(
                    tools.JobTools.parse2task_result_query_params(job=self.data, query_params=params)
                )
            except ApiResultError as err:
                logger.exception(err)
                if err.code != SubscriptionTaskNotReadyError().code:
                    raise err

                # 任务未准备就绪
                task_result = {"list": [], "total": 0, "status_counter": {"total": 0}}
            else:
                # 任务已准备就绪，但执行数量为0，代表没有需要变更的主机，插入一条忽略的主机在前端进行提示
                # task_result["total"]是筛选条件过滤后的数量，全部执行数量通过状态计数获取 - task_result["status_counter"]
                if task_result["status_counter"].get("total", 0) == 0 and not self.data.error_hosts:
                    # lazy object 通过save保存到db，如果不先转为字符串，会报错：
                    # TypeError at /en/ Object of type '__proxy__' is not JSON serializable
                    # 参考：https://stackoverflow.com/questions/48454398/
                    self.data.error_hosts = [
                        {"ip": "", "msg": str(_("没有需要变更的实例")), "status": constants.JobStatusType.IGNORED}
                    ]
                    self.data.save(update_fields=["error_hosts"])

        else:
            # 异步执行任务，任务状态默认为PENDING
            task_result = {"list": [], "total": 0, "status_counter": {"total": 0}}

        bk_host_ids = []
        host_execute_status_list = []
        for instance_status in task_result["list"]:
            host_info = instance_status["instance_info"]["host"]
            job_type_info = tools.JobTools.unzip_job_type(
                tools.JobTools.get_job_type_in_inst_status(instance_status, self.data.job_type)
            )
            inner_ip = host_info.get("bk_host_innerip")
            inner_ipv6 = host_info.get("bk_host_innerip_v6")
            host_execute_status = {
                "instance_id": instance_status["instance_id"],
                "ip": inner_ip or inner_ipv6,
                "inner_ip": inner_ip,
                "inner_ipv6": inner_ipv6,
                "bk_host_id": host_info.get("bk_host_id"),
                "bk_cloud_id": host_info["bk_cloud_id"],
                "bk_cloud_name": host_info.get("bk_cloud_name"),
                "bk_biz_id": host_info["bk_biz_id"],
                "bk_biz_name": host_info["bk_biz_name"],
                "status": instance_status["status"],
                "start_time": local_dt_str2utc_dt(dt_str=instance_status["start_time"]),
                "end_time": local_dt_str2utc_dt(dt_str=instance_status["finish_time"]),
                **{"op_type": job_type_info["op_type"], "op_type_display": job_type_info["op_type_display"]},
                **tools.JobTools.get_current_step_display(instance_status),
            }
            if host_execute_status["start_time"]:
                end_time = host_execute_status["end_time"] or timezone.now()
                # 不能通过.seconds获取datetime对象的时间差值总秒数，在间隔超过一天时会有bug
                # 在源码中，.seconds的计算为：days, seconds = divmod(seconds, 24*3600)，由一天的总秒数取模而得
                # 正确做法是使用 .total_seconds()：((self.days * 86400 + self.seconds) * 106 + self.microseconds) / 106
                # 参考：https://stackoverflow.com/questions/4362491/
                host_execute_status["cost_time"] = (end_time - host_execute_status["start_time"]).total_seconds()

            host_execute_status_list.append(host_execute_status)
            bk_host_ids.append(host_info.get("bk_host_id"))

        id__host_extra_info_map = {
            host_extra_info["bk_host_id"]: host_extra_info
            for host_extra_info in models.Host.objects.filter(bk_host_id__in=bk_host_ids).values(
                "bk_host_id", "ap_id", "is_manual", "os_type", "cpu_arch"
            )
        }
        for host in host_execute_status_list:
            host["is_manual"] = id__host_extra_info_map.get(host.get("bk_host_id"), {}).get("is_manual", False)
            host["ap_id"] = id__host_extra_info_map.get(host.get("bk_host_id"), {}).get("ap_id")

        statuses_in_conditions = tools.JobTools.fetch_values_from_conditions(
            conditions=params.get("conditions", []), key="status"
        )
        filter_hosts = []
        for host in self.data.error_hosts:
            status = host.get("status", constants.JobStatusType.FAILED)
            # conditions中无status或者筛选条件为空列表 视为全选，过滤不在筛选条件中的排除主机
            if statuses_in_conditions and status not in statuses_in_conditions:
                continue

            filter_host_info: Dict[str, Union[bool, str, int]] = {
                "filter_host": True,
                "bk_host_id": host.get("bk_host_id"),
                "ip": host["ip"],
                "inner_ip": host.get("inner_ip"),
                "inner_ipv6": host.get("inner_ipv6"),
                "bk_cloud_id": host.get("bk_cloud_id"),
                "bk_cloud_name": host.get("bk_cloud_name"),
                "bk_biz_id": host.get("bk_biz_id"),
                "bk_biz_name": host.get("bk_biz_name"),
                "job_id": host.get("job_id"),
                "status": host.get("status") or constants.JobStatusType.FAILED,
                "status_display": host.get("msg"),
                "step": "",
            }
            host_suppressed_by_id = host.get("suppressed_by_id", None)
            if host_suppressed_by_id is not None:
                filter_host_info.update({"suppressed_by_id": host_suppressed_by_id})
            filter_hosts.append(filter_host_info)
        host_execute_status_list.extend(filter_hosts)

        # 补充业务名、管控区域名称
        cloud_id_name_map = models.Cloud.cloud_id_name_map()
        biz_name_map = CmdbHandler.biz_id_name_without_permission()
        for host_execute_status in host_execute_status_list:
            host_execute_status.update(
                bk_biz_name=biz_name_map.get(host_execute_status.get("bk_biz_id")),
                bk_cloud_name=cloud_id_name_map.get(host_execute_status["bk_cloud_id"]),
            )

        tools.JobTools.update_job_statistics(self.data, task_result["status_counter"])

        job_detail = {
            "job_id": self.data.id,
            "created_by": self.data.created_by,
            "job_type": self.data.job_type,
            "job_type_display": constants.JOB_TYPE_DICT.get(self.data.job_type, ""),
            "ip_filter_list": [host["ip"] for host in self.data.error_hosts],
            "total": task_result["total"],
            "list": host_execute_status_list,
            "statistics": self.data.statistics,
            "status": self.data.status,
            "end_time": self.data.end_time,
            "start_time": self.data.start_time,
        }

        tools.JobTools.fill_cost_time(job_detail, job_detail)
        tools.JobTools.fill_sub_info_to_job_detail(job=self.data, job_detail=job_detail)

        if job_detail["meta"].get("category") != models.Subscription.CategoryType.POLICY:
            return job_detail

        # 策略关联任务填充目标版本及当前插件版本
        policy_info = tools.PolicyTools.get_policy(self.data.subscription_id, show_deleted=True, need_steps=True)

        os_cpu__config_map = tools.PolicyTools.get_os_cpu__config_map(policy_info)
        bk_host_id__plugin_version_map = tools.HostV2Tools.get_bk_host_id_plugin_version_map(
            project=policy_info["plugin_name"], bk_host_ids=bk_host_ids
        )
        for host_execute_status in job_detail["list"]:
            host_extra_info = id__host_extra_info_map.get(host_execute_status["bk_host_id"])
            if not host_extra_info:
                host_execute_status.update({"current_version": None, "target_version": None})
                continue

            os_cpu_key = f"{host_extra_info['os_type'].lower()}_{host_extra_info['cpu_arch']}"
            host_execute_status["current_version"] = bk_host_id__plugin_version_map.get(
                host_execute_status["bk_host_id"]
            )
            host_execute_status["target_version"] = os_cpu__config_map.get(os_cpu_key, {}).get("version")

        return job_detail

    @staticmethod
    def get_log_base(subscription_id: int, task_id_list: List[int], instance_id: str) -> list:
        """
        根据订阅任务ID，实例ID，获取日志
        :param subscription_id: 订阅任务ID
        :param task_id_list: 任务ID列表
        :param instance_id: 实例ID
        :return: 日志列表
        """
        params = {"subscription_id": subscription_id, "instance_id": instance_id, "task_id_list": task_id_list}
        task_result_detail = NodeApi.get_subscription_task_detail(params)
        logs = []
        if task_result_detail.get("steps"):
            if task_result_detail["steps"][0].get("target_hosts"):
                for step in task_result_detail["steps"][0]["target_hosts"][0].get("sub_steps"):
                    logs.append(
                        {
                            "step": step["node_name"],
                            "status": step["status"],
                            "log": step["log"],
                            "start_time": step.get("start_time"),
                            "finish_time": step.get("finish_time"),
                        }
                    )
        return logs

    def get_log(self, instance_id: str) -> list:
        """
        获得日志
        :param instance_id: 实例ID
        :return: 日志列表
        """
        # 获得并返回日志
        return JobHandler.get_log_base(self.data.subscription_id, self.data.task_id_list, instance_id)

    def collect_log(self, instance_id: int) -> list:
        return NodeApi.collect_subscription_task_detail({"job_id": self.job_id, "instance_id": instance_id})

    def retry_node(self, instance_id: str):
        """
        安装过程原子粒度重试
        :param instance_id: 实例id，eg： host|instance|host|127.0.0.1-0-0
        :return: 重试pipeline节点id，重试节点名称
        {
            "retry_node_id": "6f48169ed1193574961757a57d03a778",
            "retry_node_name": "安装"
        }
        """
        params = {
            "subscription_id": self.data.subscription_id,
            "instance_id": instance_id,
        }
        retry_node_info = NodeApi.retry_node(params)

        # 更新作业执行情况
        running_count = self.data.statistics["running_count"] + 1
        failed_count = self.data.statistics["failed_count"] - 1
        self.data.statistics.update({"running_count": running_count, "failed_count": failed_count})
        self.data.status = constants.JobStatusType.RUNNING
        self.data.save(update_fields=["statistics", "status"])

        return retry_node_info
