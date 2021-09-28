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
import logging
import re
from typing import Any, Dict, List

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
from apps.utils.basic import filter_values, suffix_slash, to_int_or_default
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

    def check_job_permission(self, username: str, bk_biz_scope: list):
        """
        检测用户是否有当前任务的权限
        :param username: 用户名
        :param bk_biz_scope: 任务业务范围
        """
        # 检测是否有权限：拥有业务权限或创建人可以访问当前任务
        biz_info = CmdbHandler().biz_id_name({"action": constants.IamActionType.task_history_view})
        diff = list(set(bk_biz_scope).difference(set(biz_info.keys())))
        if diff != [] and self.data.created_by != username:
            raise exceptions.JobNotPermissionError(_("用户无权限访问当前任务"))

    def task_status_list(self):
        """
        返回任务执行的状态
        :return: 以Host ID为键，返回任务执行状态
        {
            bk_host_id: {
                'job_id': job_id,
                'status': status
            }
        }
        """
        task_info = {
            task["bk_host_id"]: {"status": task["status"]}
            for task in models.JobTask.objects.values("bk_host_id", "instance_id", "job_id", "status")
        }
        return task_info

    def check_ap_and_biz_scope(self, node_type: str, host: dict, cloud_info: dict):
        """
        返回主机的接入点、业务范围、节点类型。
        兼容订阅任务版注册<br>
        如果是非直连区域，获得该云区域下的ap_id为空<br>
        如果是直连区域，ap_id直接从参数拿, 如果是proxy，则ap_id为空<br>
        :param node_type: 节点类型
        :param host: 主机信息
        :param cloud_info: 云区域信息
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

    def get_commands(self, username: str, request_bk_host_id: int, is_uninstall: bool):
        """
        获取命令
        :param username: 用户名
        :param request_bk_host_id: 主机ID
        :param is_uninstall: 是否为卸载
        :return: ips_commands 每个ip的安装命令， total_commands：
        """

        job = self.data

        # 检查权限
        self.check_job_permission(username, job.bk_biz_scope)

        def gen_pre_manual_command(host, host_install_pipeline_id, batch_install):
            result = NodeApi.fetch_commands(
                {
                    "bk_host_id": host.bk_host_id,
                    "host_install_pipeline_id": host_install_pipeline_id[host.bk_host_id],
                    "is_uninstall": is_uninstall,
                    "batch_install": batch_install,
                }
            )
            win_commands = result["win_commands"]
            pre_commands = result["pre_commands"]
            run_cmd = result["run_cmd"]

            if isinstance(win_commands, list):
                win_commands = " & ".join(win_commands)
            if isinstance(pre_commands, list):
                pre_commands = " && ".join(pre_commands)

            manual_pre_command = (win_commands or pre_commands) + (" && " if pre_commands else " & ")
            return run_cmd, manual_pre_command

        # 云区域下的主机
        cloud_host_id = {}
        # 所有主机对应的安装步骤node_id
        host_install_pipeline_id = {}
        # 获取任务状态
        task_result = NodeApi.get_subscription_task_status(
            {"subscription_id": job.subscription_id, "task_id_list": job.task_id_list, "return_all": True}
        )
        for result in task_result["list"]:
            bk_cloud_id = result["instance_info"]["host"]["bk_cloud_id"]
            bk_host_id = result["instance_info"]["host"].get("bk_host_id")
            if not bk_host_id:
                # 还有主机没注册成功
                return {"status": "PENDING"}

            # 获取每台主机安装任务的pipeline_id
            sub_steps = result["steps"][0]["target_hosts"][0]["sub_steps"]
            for step in sub_steps:
                if step["node_name"] in ["手动安装", "手动卸载"] and (
                    step["status"] == "RUNNING" or step["status"] == "SUCCESS"
                ):
                    pipeline_id = step["pipeline_id"]
                    if bk_cloud_id not in cloud_host_id:
                        cloud_host_id[bk_cloud_id] = [bk_host_id]
                    else:
                        cloud_host_id[bk_cloud_id].append(bk_host_id)
                    host_install_pipeline_id[bk_host_id] = pipeline_id

        # 每个云区域下只选一个主机
        bk_host_ids = [cloud_host_id[cloud][0] for cloud in cloud_host_id]
        hosts = {host.bk_host_id: host for host in models.Host.objects.filter(bk_host_id__in=bk_host_ids)}

        # 所有需要安装的主机信息
        bk_host_ids = []
        for cloud in cloud_host_id:
            for host_id in cloud_host_id[cloud]:
                bk_host_ids.append(host_id)
        all_hosts = {host.bk_host_id: host for host in models.Host.objects.filter(bk_host_id__in=bk_host_ids)}

        commands = {}
        if request_bk_host_id == -1:
            host_to_gen = list(hosts.values())
        elif all_hosts.get(request_bk_host_id):
            host_to_gen = [all_hosts[request_bk_host_id]]
        else:
            host_to_gen = []

        for host in host_to_gen:
            # 生成命令
            batch_install = False
            # 是否为批量安装
            if len(cloud_host_id[host.bk_cloud_id]) > 1:
                batch_install = True

            run_cmd, manual_pre_command = gen_pre_manual_command(host, host_install_pipeline_id, batch_install)

            # 每个IP的单独执行命令
            ips_commands = []
            # 用于生成每个Cloud下的批量安装命令
            host_commands = []
            # 该云区域下的所有主机
            host_ids = cloud_host_id[host.bk_cloud_id]
            for host_id in host_ids:
                batch_install = False
                single_run_cmd, single_manual_pre_command = gen_pre_manual_command(
                    host, host_install_pipeline_id, batch_install
                )
                login_ip = all_hosts[host_id].login_ip
                inner_ip = all_hosts[host_id].inner_ip
                bk_cloud_id = all_hosts[host_id].bk_cloud_id
                os_type = all_hosts[host_id].os_type.lower()

                # 获得安装目标目录
                dest_dir = host.agent_config["temp_path"]
                dest_dir = suffix_slash(host.os_type.lower(), dest_dir).replace("\\", "\\\\\\\\")

                echo_pattern = (
                    '["'
                    + '","'.join(
                        [
                            login_ip or inner_ip,
                            inner_ip,
                            "<span>账号</span>",
                            "<span>端口号</span>",
                            "<span>密码/密钥</span>",
                            str(bk_cloud_id),
                            all_hosts[host_id].node_type,
                            os_type,
                            dest_dir,
                        ]
                    )
                    + '"]'
                )
                # 批量安装命令
                host_commands.append(echo_pattern)
                single_run_cmd = re.sub(r"'\[\[.*\]\]'", "'[" + echo_pattern + "]'", single_run_cmd)

                # 每个IP的单独安装命令
                ips_commands.append(
                    {
                        "ip": inner_ip,
                        "command": (single_manual_pre_command + single_run_cmd),
                        "os_type": all_hosts[host_id].os_type,
                    }
                )

            host_commands = "'[" + ",".join(host_commands) + "]'"
            host_commands = re.sub(r"'\[\[.*\]\]'", host_commands, run_cmd)

            commands[host.bk_cloud_id] = {
                "ips_commands": ips_commands,
                "total_commands": (manual_pre_command + host_commands),
            }

        return commands

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

    def job(self, params: dict, username: str, is_superuser: bool, ticket: str):
        """
        Job 任务处理器

        :param params: 请求参数的字典
        """

        # 获取Hosts中的cloud_id列表、ap_id列表、内网、外网、登录IP列表、bk_biz_scope列表
        bk_cloud_ids = set()
        ap_ids = set()
        bk_biz_scope = set()
        inner_ips = set()
        is_manual = set()

        for host in params["hosts"]:
            bk_cloud_ids.add(host["bk_cloud_id"])
            bk_biz_scope.add(host["bk_biz_id"])
            inner_ips.add(host["inner_ip"])
            is_manual.add(host["is_manual"])
            if host.get("ap_id"):
                ap_ids.add(host["ap_id"])

        # 如果混合了【手动安装】，【自动安装】则不允许通过
        # 此处暂不和入job validator.
        if len(is_manual) > 1:
            raise exceptions.MixedOperationError
        else:
            is_manual = list(is_manual)[0]

        bk_biz_scope = list(bk_biz_scope)

        # 获得用户的业务列表
        # 格式 { bk_biz_id: bk_biz_name , ...}
        if params["node_type"] == constants.NodeType.PROXY:
            biz_info = CmdbHandler().biz_id_name({"action": constants.IamActionType.proxy_operate})
        else:
            biz_info = CmdbHandler().biz_id_name({"action": constants.IamActionType.agent_operate})

        # 获得相应云区域 id, name, ap_id
        # 格式 { cloud_id: {'bk_cloud_name': name, 'ap_id': id}, ...}
        cloud_info = CloudHandler().list_cloud_info(bk_cloud_ids)

        # 获得接入点列表
        # 格式 { id: name, ...}
        ap_id_name = APHandler().ap_list(ap_ids)

        # 获得用户输入的ip是否存在于数据库中
        # 格式 { bk_cloud_id+ip: { 'bk_host_id': ..., 'bk_biz_id': ..., 'node_type': ...}}
        inner_ip_info = HostHandler().ip_list(inner_ips)

        # 获得正在执行的任务状态
        task_info = self.task_status_list()

        # 对数据进行校验
        # 重装则校验IP是否存在，存在才可重装
        ip_filter_list, accept_list, proxy_not_alive = validator.job_validate(
            biz_info,
            params,
            cloud_info,
            ap_id_name,
            inner_ip_info,
            bk_biz_scope,
            task_info,
            username,
            is_superuser,
            ticket,
        )

        if proxy_not_alive:
            raise exceptions.AliveProxyNotExistsError(
                context="不存在可用代理", data={"job_id": "", "ip_filter": self.ugettext_to_unicode(proxy_not_alive)}
            )

        if not accept_list:
            # 如果都被过滤了
            raise exceptions.AllIpFiltered(
                context="所有IP均被过滤", data={"job_id": "", "ip_filter": self.ugettext_to_unicode(ip_filter_list)}
            )

        if params["op_type"] in [constants.OpType.INSTALL, constants.OpType.REPLACE, constants.OpType.RELOAD]:
            # 安装、替换Proxy操作
            subscription_nodes = self.subscription_install(
                accept_list, params["node_type"], cloud_info, biz_info, username
            )
            subscription = self.create_subscription(params["job_type"], subscription_nodes)
        else:
            # 重装、卸载等操作
            # 此步骤需要校验密码、秘钥
            subscription_nodes, ip_filter_list = self.update(accept_list, ip_filter_list, is_manual)
            if not subscription_nodes:
                raise exceptions.AllIpFiltered(
                    context="所有IP均被过滤", data={"job_id": "", "ip_filter": self.ugettext_to_unicode(ip_filter_list)}
                )
            subscription = self.create_subscription(params["job_type"], subscription_nodes)

        # ugettext_lazy需要转为unicode才可进行序列化
        ip_filter_list = self.ugettext_to_unicode(ip_filter_list)

        # 创建Job
        job = models.Job.objects.create(
            job_type=params["job_type"],
            bk_biz_scope=bk_biz_scope,
            subscription_id=subscription["subscription_id"],
            task_id_list=[subscription["task_id"]],
            statistics={
                "success_count": 0,
                "failed_count": len(ip_filter_list),
                "pending_count": len(subscription_nodes),
                "running_count": 0,
                "total_count": len(ip_filter_list) + len(subscription_nodes),
            },
            error_hosts=ip_filter_list,
            created_by=username,
        )

        # 返回被过滤的ip列表
        return {"job_id": job.id, "ip_filter": ip_filter_list}

    def subscription_install(self, accept_list: list, node_type: str, cloud_info: dict, biz_info: dict, username: str):
        """
        Job 订阅安装任务
        :param accept_list: 所有通过校验需要新安装的主机
        :param node_type: 节点类型
        :param cloud_info: 云区域信息
        :param biz_info: 业务ID及其对应的名称
        :param username: 用户名
        :return
        """

        # 节点变量，用于后续订阅任务注册主机，安装等操作
        subscription_nodes = []
        for host in accept_list:
            inner_ip = host["inner_ip"]
            outer_ip = host.get("outer_ip", "")
            login_ip = host.get("login_ip", "")

            host_ap_id, host_node_type = self.check_ap_and_biz_scope(node_type, host, cloud_info)

            instance_info = {
                "is_manual": host["is_manual"],
                "ap_id": host_ap_id,
                "install_channel_id": host.get("install_channel_id"),
                "bk_os_type": constants.BK_OS_TYPE[host["os_type"]],
                "bk_host_innerip": inner_ip,
                "bk_host_outerip": outer_ip,
                "login_ip": login_ip,
                "username": username,
                "bk_biz_id": host["bk_biz_id"],
                "bk_biz_name": biz_info.get(host["bk_biz_id"]),
                "bk_cloud_id": host["bk_cloud_id"],
                "bk_cloud_name": str(cloud_info.get(host["bk_cloud_id"], {}).get("bk_cloud_name")),
                "bk_supplier_account": settings.DEFAULT_SUPPLIER_ACCOUNT,
                "host_node_type": host_node_type,
                "os_type": host["os_type"],
                "auth_type": host.get("auth_type", "MANUAL"),
                "account": host.get("account", "MANUAL"),
                "port": host.get("port"),
                "password": base64.b64encode(host.get("password", "").encode()).decode(),
                "key": base64.b64encode(host.get("key", "").encode()).decode(),
                "retention": host.get("retention", 1),
                "peer_exchange_switch_for_agent": host.get("peer_exchange_switch_for_agent"),
                "bt_speed_limit": host.get("bt_speed_limit"),
            }

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
                    "ip": inner_ip,
                    "instance_info": instance_info,
                }
            )

        return subscription_nodes

    def update(self, accept_list: list, ip_filter_list: list, is_manual: bool = False):
        """
        用于更新identity认证信息
        :param accept_list: 所有需要修改的数据
        :param ip_filter_list: 过滤数据
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
                "outer_ip": host["outer_ip"],
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

    def operate(self, params: dict, username: str, is_superuser: bool):
        """
        用于只有bk_host_id参数的下线、重启等操作
        :param params: 任务类型及host_id
        :param is_superuser: 是否超管
        """

        # 获得正在执行的任务状态
        task_info = self.task_status_list()

        if params["node_type"] == constants.NodeType.PROXY:
            # 是否为针对代理的操作，用户有权限获取的业务
            # 格式 { bk_biz_id: bk_biz_name , ...}
            user_biz = CmdbHandler().biz_id_name({"action": constants.IamActionType.proxy_operate})
            filter_node_types = [constants.NodeType.PROXY]
            is_proxy = True
        else:
            # 用户有权限获取的业务
            # 格式 { bk_biz_id: bk_biz_name , ...}
            user_biz = CmdbHandler().biz_id_name({"action": constants.IamActionType.agent_operate})
            filter_node_types = [constants.NodeType.AGENT, constants.NodeType.PAGENT]
            is_proxy = False

        if params.get("exclude_hosts") is not None:
            # 跨页全选
            db_host_sql = (
                HostHandler()
                .multiple_cond_sql(params, user_biz, proxy=is_proxy)
                .exclude(bk_host_id__in=params.get("exclude_hosts", []))
                .values("bk_host_id", "bk_biz_id", "bk_cloud_id", "inner_ip", "node_type", "os_type")
            )

        else:
            # 不是跨页全选
            db_host_sql = models.Host.objects.filter(
                bk_host_id__in=params["bk_host_id"], node_type__in=filter_node_types
            ).values("bk_host_id", "bk_biz_id", "bk_cloud_id", "inner_ip", "node_type", "os_type")

        # 校验器进行校验
        db_host_ids, host_biz_scope = validator.operate_validator(
            list(db_host_sql), user_biz, username, task_info, is_superuser
        )
        subscription = self.create_subscription(params["job_type"], db_host_ids)

        # 创建Job
        job = models.Job.objects.create(
            job_type=params["job_type"],
            subscription_id=subscription["subscription_id"],
            task_id_list=[subscription["task_id"]],
            statistics={
                "success_count": 0,
                "failed_count": 0,
                "pending_count": len(db_host_ids),
                "running_count": 0,
                "total_count": len(db_host_ids),
            },
            error_hosts=[],
            created_by=username,
            bk_biz_scope=list(set(host_biz_scope)),
        )

        return {"job_id": job.id}

    def create_subscription(self, job_type, nodes: list):
        """
        创建订阅任务
        :param job_type: INSTALL_AGENT
        :param nodes: 任务范围

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
        params = {
            "run_immediately": True,
            "bk_app_code": "nodeman",
            "bk_username": "admin",
            "scope": {"node_type": "INSTANCE", "object_type": "HOST", "nodes": nodes},
            "steps": [
                {
                    "id": "agent",
                    "type": "AGENT",
                    "config": {"job_type": job_type},
                    "params": {"context": {}, "blueking_language": get_language()},
                }
            ],
        }
        return NodeApi.create_subscription(params)

    def retry(self, username: str, instance_id_list: List[str] = None):
        """
        重试部分实例或主机
        :param username: 用户名
        :param instance_id_list: 需重试的实例列表
        :return: task_id_list
        """

        # 检测是否有权限
        self.check_job_permission(username, self.data.bk_biz_scope)

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

    def revoke(self, instance_id_list: list, username: str):

        # 检测是否有权限
        self.check_job_permission(username, self.data.bk_biz_scope)

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

    def retrieve(self, params: Dict[str, Any], username: str):
        """
        任务详情页接口
        :param params: 接口请求参数
        :param username: 用户名
        """

        # 检测是否有权限
        self.check_job_permission(username, self.data.bk_biz_scope)

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
            host_execute_status = {
                "instance_id": instance_status["instance_id"],
                "inner_ip": host_info["bk_host_innerip"],
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
            filter_hosts.append(
                {
                    "filter_host": True,
                    "bk_host_id": host.get("bk_host_id"),
                    "inner_ip": host["ip"],
                    "bk_cloud_id": host.get("bk_cloud_id"),
                    "bk_cloud_name": host.get("bk_cloud_name"),
                    "bk_biz_id": host.get("bk_biz_id"),
                    "bk_biz_name": host.get("bk_biz_name"),
                    "job_id": host.get("job_id"),
                    "status": host.get("status") or constants.JobStatusType.FAILED,
                    "status_display": host.get("msg"),
                    "step": "",
                }
            )
        host_execute_status_list.extend(filter_hosts)

        # 补充业务名、云区域名称
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

    def get_log(self, instance_id: str, username: str) -> list:
        """
        获得日志
        :param instance_id: 实例ID
        :param username: 用户名
        :return: 日志列表
        """

        # 检测是否有权限
        self.check_job_permission(username, self.data.bk_biz_scope)

        # 获得并返回日志
        return JobHandler.get_log_base(self.data.subscription_id, self.data.task_id_list, instance_id)

    def collect_log(self, instance_id: int, username: str) -> list:
        self.check_job_permission(username, self.data.bk_biz_scope)

        res = NodeApi.collect_subscription_task_detail({"job_id": self.job_id, "instance_id": instance_id})
        return res

    def retry_node(self, instance_id: str, username: str):
        """
        安装过程原子粒度重试
        :param instance_id: 实例id，eg： host|instance|host|127.0.0.1-0-0
        :param username: 用户名
        :return: 重试pipeline节点id，重试节点名称
        {
            "retry_node_id": "6f48169ed1193574961757a57d03a778",
            "retry_node_name": "安装"
        }
        """

        # 检查是否有权限
        self.check_job_permission(username, self.data.bk_biz_scope)

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
