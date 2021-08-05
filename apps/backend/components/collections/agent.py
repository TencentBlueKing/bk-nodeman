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
import ntpath
import os
import posixpath
import re
import socket
import time
import traceback
from pathlib import Path

import ujson as json
from django.conf import settings
from django.db import transaction
from django.db.models import Max, Subquery
from django.utils import timezone, translation
from django.utils.translation import ugettext_lazy as _

from apps.backend.agent.tools import gen_commands
from apps.backend.api.constants import POLLING_INTERVAL, POLLING_TIMEOUT, JobDataStatus
from apps.backend.api.gse import GseClient
from apps.backend.components import task_service
from apps.backend.components.collections.gse import GseBaseService
from apps.backend.components.collections.job import (
    JobFastExecuteScriptService,
    JobFastPushFileService,
    JobPushMultipleConfigFileService,
)
from apps.backend.exceptions import GenCommandsError
from apps.backend.subscription.tools import update_job_status
from apps.backend.utils.ssh import SshMan
from apps.backend.utils.wmi import execute_cmd, put_file
from apps.backend.views import generate_gse_config
from apps.component.esbclient import client_v2
from apps.exceptions import AuthOverdueException, ComponentCallError
from apps.node_man import constants
from apps.node_man.exceptions import HostNotExists
from apps.node_man.handlers.tjj import TjjHandler
from apps.node_man.models import (
    AccessPoint,
    Host,
    IdentityData,
    Job,
    JobTask,
    Packages,
    ProcessStatus,
    SubscriptionInstanceRecord,
)
from apps.node_man.policy.tencent_vpc_client import VpcClient
from apps.utils.basic import suffix_slash
from pipeline.component_framework.component import Component
from pipeline.core.flow import Service, StaticIntervalGenerator

win_ping_pattern = re.compile(r"(?<=\=\s)\d+(?=ms)")


class AgentService(Service):
    """
    AGENT安装基类
    """

    def __init__(self, name):
        super().__init__(name=name)

    def execute(self, data, parent_data):
        # 国际化
        translation.activate(data.get_one_of_inputs("blueking_language", "zh-hans"))

        try:
            bk_host_id = data.get_one_of_inputs("bk_host_id") or data.get_one_of_inputs("host_info")["bk_host_id"]
            description = data.get_one_of_inputs("description")
        except (KeyError, TypeError):
            pass
        else:
            subscription_instance = SubscriptionInstanceRecord.objects.get(pipeline_id=self.root_pipeline_id)
            job = Job.objects.get(subscription_id=subscription_instance.subscription_id)
            if bk_host_id:
                update_fields = {
                    "job_id": job.id,
                    "status": constants.JobStatusType.RUNNING,
                    "current_step": _("正在{description}").format(description=description),
                    "pipeline_id": self.id,
                    "instance_id": subscription_instance.instance_id,
                }
                # do not use update_or_create, prevent of deadlock
                job_task = JobTask.objects.filter(bk_host_id=bk_host_id)
                if job_task.exists():
                    job_task.update(**update_fields)
                else:
                    JobTask.objects.create(bk_host_id=bk_host_id, **update_fields)

        self.logger.info(_("开始{name}").format(name=self.name))
        try:
            result = self._execute(data, parent_data)
            if not result:
                self.logger.info(_("{name}失败").format(name=self.name))
        except Exception as err:
            reason = str(err)
            # traceback日志进行折叠
            self.logger.error(
                "[DEBUG]{debug_begin}\n{traceback}\n{debug_end}".format(
                    debug_begin=" Begin of collected logs: ".center(40, "*"),
                    traceback=traceback.format_exc(),
                    debug_end=" End of collected logs ".center(40, "*"),
                )
            )
            self.logger.error(traceback.format_exc())
            self.logger.info(_("{name}失败: {reason}, 请先尝试查看日志并处理，若无法解决，请联系管理员处理。").format(name=self.name, reason=reason))
            result = False

        return result

    def _execute(self, data, parent_data):
        raise NotImplementedError


class QueryTjjPasswordService(AgentService):
    """
    查询主机是否支持铁将军密码
    """

    name = _("查询铁将军密码")

    def __init__(self):
        super().__init__(name=self.name)

    def inputs_format(self):
        return [
            Service.InputItem(name="host_info", key="host_info", type="object", required=True),
            Service.InputItem(name="creator", key="creator", type="str", required=True),
        ]

    def _execute(self, data, parent_data):
        # 查询主机是否支持铁将军
        host_info = data.get_one_of_inputs("host_info")
        creator = data.get_one_of_inputs("creator")
        host = Host.get_by_host_info(host_info)

        if host.identity.auth_type != constants.AuthType.TJJ_PASSWORD:
            self.logger.info(_("当前主机验证类型无需查询密码"))
            return True

        is_ok, success_ips, failed_ips, err_msg = TjjHandler().get_password(
            creator, [host.inner_ip], host.identity.extra_data.get("oa_ticket")
        )

        if not is_ok:
            self.logger.error(err_msg)
            self.logger.error(_("若 OA TICKET 过期，请重新登录 OA 后再重试您的操作。请注意不要直接使用此任务中的重试功能~"))
            return False

        if host.inner_ip in failed_ips:
            self.logger.error(failed_ips[host.inner_ip]["Message"])
            return False

        host.identity.retention = 1
        host.identity.password = success_ips.get(host.inner_ip, "")
        host.identity.save()
        return True


class RegisterHostService(AgentService):
    name = _("注册主机到配置平台")

    __need_schedule__ = True
    interval = StaticIntervalGenerator(POLLING_INTERVAL)

    def __init__(self):
        super().__init__(name=self.name)

    def inputs_format(self):
        return [
            Service.InputItem(name="host_info", key="host_info", type="object", required=True),
        ]

    def outputs_format(self):
        return [
            Service.OutputItem(name="bk_host_id", key="bk_host_id", type="int"),
        ]

    def register_host(self, bk_biz_id, host_info):
        """
        请求cmdb进行注册
        :param bk_biz_id: 业务id
        :param host_info: 注册信息

        结果保存在self.cmdb_result
        """
        kwargs = {"host_info": host_info}
        if int(bk_biz_id) != settings.BK_CMDB_RESOURCE_POOL_BIZ_ID:
            kwargs["bk_biz_id"] = int(bk_biz_id)
        try:
            client_v2.cc.add_host_to_resource(kwargs)
        except ComponentCallError as err:
            self.logger.error(_("调用CMDB异常, {err}").format(err=err))

    @staticmethod
    def list_biz_host(kwargs):
        biz_host_result = client_v2.cc.list_biz_hosts(kwargs).get("info") or []
        if biz_host_result:
            return {"result": True, "bk_host_id": biz_host_result[0]["bk_host_id"]}

        return {"result": False}

    def list_host_without_biz(self, kwargs, bk_biz_name):
        without_biz_result = client_v2.cc.list_hosts_without_biz(kwargs).get("info") or []
        if not without_biz_result:
            return {"result": False, "message": _("查询CMDB主机失败，未在CMDB中查询到主机信息")}

        # 属于其它业务查询业务信息
        bk_host_id = without_biz_result[0]["bk_host_id"]
        find_biz_kwargs = {"page": {"start": 0, "limit": 1}, "bk_host_id": [bk_host_id]}
        cc_bk_host_relations_result = client_v2.cc.find_host_biz_relations(find_biz_kwargs)
        cmdb_bk_biz_id = cc_bk_host_relations_result[0]["bk_biz_id"]

        if kwargs["bk_biz_id"] == cmdb_bk_biz_id:
            return {"result": True, "bk_host_id": bk_host_id}

        return {
            "result": False,
            "message": _(
                "本次安装的业务为 {bk_biz_name}({bk_biz_id}), CMDB 中此主机已被注册到 {cmdb_bk_biz_name}({cmdb_bk_biz_id}), "
                "请调整本次安装的业务或往配置平台移动主机"
            ).format(
                bk_biz_name=bk_biz_name,
                bk_biz_id=kwargs["bk_biz_id"],
                cmdb_bk_biz_name=self.search_business(cmdb_bk_biz_id)[0]["bk_biz_name"],
                cmdb_bk_biz_id=cmdb_bk_biz_id,
            ),
        }

    @staticmethod
    def search_business(bk_biz_id):
        """
        查询相应业务的业务运维
        :param bk_biz_id: 业务ID
        :return: 列表 ，包含 业务ID、名字、业务运维
        """
        kwargs = {
            "fields": ["bk_biz_id", "bk_biz_name", "bk_biz_maintainer"],
            "condition": {"bk_biz_id": bk_biz_id},
        }
        result = client_v2.cc.search_business(kwargs)["info"]
        return result

    def _execute(self, data, parent_data):
        host_info = data.get_one_of_inputs("host_info")
        try:
            host = Host.get_by_host_info(host_info)
        except HostNotExists:
            self.logger.info(_("主机待注册"))
        else:
            # 主机已存在，Agent 转安装 Proxy的场景，无需再注册
            if host.node_type != constants.NodeType.PROXY and host_info["host_node_type"] == constants.NodeType.PROXY:
                data.outputs.is_register = True
                return True

        # 是否为手动安装
        is_manual = host_info.get("is_manual", False)

        if host_info.get("auth_type") != constants.AuthType.TJJ_PASSWORD and not is_manual:
            if not (host_info.get("password") or host_info.get("key")):
                self.logger.error(_("该主机的登录认证信息已被清空，无法重试，请重新发起安装任务"))
                return False

        # 准备注册数据
        inner_ip = host_info["bk_host_innerip"]
        outer_ip = host_info.get("bk_host_outerip", "")

        bk_cloud_id = host_info["bk_cloud_id"]
        if host_info["bk_biz_id"] != settings.BK_CMDB_RESOURCE_POOL_BIZ_ID:
            biz_info = self.search_business(bk_biz_id=host_info["bk_biz_id"])
        else:
            # 资源池业务
            biz_info = [{"bk_biz_maintainer": host_info.get("username")}]
        register_args = {
            0: {
                "bk_host_innerip": inner_ip,
                "import_from": "3",
                "bk_cloud_id": bk_cloud_id,
                "bk_host_outerip": outer_ip,
                "bk_os_type": constants.BK_OS_TYPE[host_info["os_type"]],
                "bk_bak_operator": biz_info[0].get("bk_biz_maintainer"),
                "operator": biz_info[0].get("bk_biz_maintainer"),
            }
        }
        self.logger.info(_("注册主机参数为:\n {params}").format(params=json.dumps(register_args, indent=2)))

        kwargs = {"host_info": register_args}
        if int(host_info["bk_biz_id"]) != settings.BK_CMDB_RESOURCE_POOL_BIZ_ID:
            kwargs["bk_biz_id"] = int(host_info["bk_biz_id"])

        client_v2.cc.add_host_to_resource(kwargs)

        data.outputs.polling_time = 0
        data.outputs.is_register = False
        data.outputs.query_cc_count = 0
        return True

    def schedule(self, data, parent_data, callback_data=None):
        polling_time = data.get_one_of_outputs("polling_time") or 0
        is_register = data.get_one_of_outputs("is_register") or False
        host_info = data.get_one_of_inputs("host_info")
        bk_host_id = data.get_one_of_outputs("bk_host_id")
        query_cc_count = data.get_one_of_outputs("query_cc_count") or 0
        inner_ip = host_info["bk_host_innerip"]
        outer_ip = host_info.get("bk_host_outerip", "")
        login_ip = host_info.get("login_ip", "")
        data_ip = host_info.get("data_ip", "")
        is_manual = host_info.get("is_manual", False)

        if not is_register:
            list_host_kwargs = {
                "page": {"start": 0, "limit": 1, "sort": "bk_host_id"},
                "fields": ["bk_host_id"],
                "bk_biz_id": host_info["bk_biz_id"],
                "host_property_filter": {
                    "condition": "AND",
                    "rules": [
                        {"field": "bk_cloud_id", "operator": "equal", "value": host_info["bk_cloud_id"]},
                        {"field": "bk_host_innerip", "operator": "equal", "value": inner_ip},
                    ],
                },
            }
            if query_cc_count > 3:
                cc_host_result = self.list_host_without_biz(list_host_kwargs, host_info["bk_biz_name"])
                if not cc_host_result["result"]:
                    self.logger.error(cc_host_result["message"])
                    self.finish_schedule()
                    return False

                data.outputs.is_register = True
                data.outputs.bk_host_id = cc_host_result["bk_host_id"]
            else:
                cc_host_result = self.list_biz_host(list_host_kwargs)
                if not cc_host_result["result"]:
                    data.outputs.query_cc_count += 1
                else:
                    data.outputs.is_register = True
                    data.outputs.bk_host_id = cc_host_result["bk_host_id"]

        if bk_host_id:
            # 写入数据库
            if host_info["host_node_type"] == constants.NodeType.PROXY:
                login_ip = login_ip or outer_ip or inner_ip
            else:
                login_ip = login_ip or inner_ip

            try:
                with transaction.atomic():
                    extra_data = {
                        "peer_exchange_switch_for_agent": host_info.get("peer_exchange_switch_for_agent", True),
                        "bt_speed_limit": host_info.get("bt_speed_limit", 0),
                    }
                    if host_info.get("data_path"):
                        extra_data.update({"data_path": host_info.get("data_path")})
                    host, created = Host.objects.update_or_create(
                        bk_host_id=bk_host_id,
                        defaults={
                            "bk_biz_id": host_info["bk_biz_id"],
                            "bk_cloud_id": host_info["bk_cloud_id"],
                            "inner_ip": inner_ip,
                            "outer_ip": outer_ip,
                            "login_ip": login_ip,
                            "data_ip": data_ip,
                            "is_manual": is_manual,
                            "os_type": host_info["os_type"],
                            "node_type": host_info["host_node_type"],
                            "ap_id": host_info["ap_id"],
                            "install_channel_id": host_info.get("install_channel_id"),
                            "upstream_nodes": host_info.get("upstream_nodes", []),
                            "updated_at": timezone.now(),
                            "extra_data": extra_data,
                        },
                    )
                    if created:
                        # 初次创建主机时，初始化CPU架构，根据操作系统设置默认值，后续通过安装上报日志修正
                        if host_info["os_type"] == constants.OsType.AIX:
                            host.cpu_arch = constants.CpuType.powerpc
                        else:
                            host.cpu_arch = constants.CpuType.x86_64
                        host.save(update_fields=["cpu_arch"])
                    IdentityData.objects.update_or_create(
                        bk_host_id=bk_host_id,
                        defaults={
                            "auth_type": host_info.get("auth_type"),
                            "account": host_info.get("account"),
                            "password": base64.b64decode(host_info.get("password", "")).decode(),
                            "port": host_info.get("port"),
                            "key": base64.b64decode(host_info.get("key", "")).decode(),
                            "retention": host_info.get("retention", 1),
                            "extra_data": host_info.get("extra_data", {}),
                            "updated_at": timezone.now(),
                        },
                    )
                    process_status, created = ProcessStatus.objects.get_or_create(
                        bk_host_id=bk_host_id,
                        name=ProcessStatus.GSE_AGENT_PROCESS_NAME,
                        source_type=ProcessStatus.SourceType.DEFAULT,
                    )
                    if created:
                        process_status.status = constants.ProcStateType.NOT_INSTALLED
                        process_status.save()
            except Exception as error:
                self.logger.info(f"something went wrong: {error}")
            else:
                subscription_instance = SubscriptionInstanceRecord.objects.get(pipeline_id=self.root_pipeline_id)
                subscription_instance.instance_info["host"]["bk_host_id"] = bk_host_id
                subscription_instance.instance_info["host"]["is_manual"] = is_manual
                subscription_instance.save()

                self.logger.info(_("注册CMDB完成"))
                self.finish_schedule()
                return True

        # 判断超时
        elif polling_time + POLLING_INTERVAL > POLLING_TIMEOUT / 2:
            self.logger.error(_("注册主机成功，写入节点管理失败，请重试"))
            self.finish_schedule()
            return False

        data.outputs.polling_time = polling_time + POLLING_INTERVAL
        return True


class ChooseAccessPointService(AgentService):
    """
    选择接入点
    """

    name = _("选择接入点")
    MIN_PING_TIME = 9999

    def __init__(self):
        super().__init__(name=self.name)

    def inputs_format(self):
        return [
            Service.InputItem(name="host_info", key="host_info", type="object", required=True),
        ]

    def _execute(self, data, parent_data):
        # 1. 查询当前主机是否已配置接入点
        bk_host_id = data.get_one_of_inputs("bk_host_id")
        host_info = data.get_one_of_inputs("host_info")
        host = Host.get_by_host_info({"bk_host_id": bk_host_id} if bk_host_id else host_info)

        if host.ap_id != constants.DEFAULT_AP_ID:
            self.logger.info(_("当前主机已分配接入点[{ap_name}]").format(ap_name=host.ap.name))
            return True

        if host.node_type == constants.NodeType.PAGENT:
            proxy = host.get_random_alive_proxy()
            host.ap_id = proxy.ap_id
            host.save()
            self.logger.info(_("已选择[{ap_name}]作为本次安装接入点").format(ap_name=proxy.ap.name))
            return True
        else:
            min_ping_ap_id, ap_ping_time, min_ping_time = self._agent_choose_ap(host)
            if not ap_ping_time:
                self.logger.error(_("自动选择接入点失败，请到全局配置新建接入点"))
                return False
            if min_ping_time == self.MIN_PING_TIME:
                self.logger.error(_("自动选择接入点失败，没有可以用接入点"))
                return False
            host.ap_id = min_ping_ap_id
            host.save()
            self.logger.info(_("已选择[{ap_name}]作为本次安装接入点").format(ap_name=host.ap.name))
            return True

    def _agent_choose_ap(self, host):
        is_linux = host.os_type in [constants.OsType.LINUX, constants.OsType.AIX, constants.OsType.SOLARIS]
        ssh_man = None
        if is_linux:
            ssh_man = SshMan(host, self.logger)
            # 一定要先设置一个干净的提示符号，否则会导致console_ready识别失效
            ssh_man.get_and_set_prompt()
            # 2. 若未配置接入点，登录机器ping接入点，选择平均延迟最低的接入点
        ap_ping_time = {}
        min_ping_time = self.MIN_PING_TIME
        min_ping_ap_id = -1
        for ap in AccessPoint.objects.all():
            gse_ping_time = []
            for gse_server in ap.taskserver:
                ip = gse_server["inner_ip"] if host.bk_cloud_id == constants.DEFAULT_CLOUD else gse_server["outer_ip"]
                if is_linux:
                    ping_time = ssh_man.send_cmd(
                        f"ping {ip} -i 0.1 -c 4 -s 100 -W 1 | tail -1 | awk -F '/' '{{print $5}}'"
                    )
                    if ping_time:
                        gse_ping_time.append(float(ping_time))
                else:
                    output = execute_cmd(
                        f"ping {ip} -w 1000",
                        host.login_ip or host.inner_ip,
                        host.identity.account,
                        host.identity.password,
                    )["data"]
                    try:
                        ping_time = win_ping_pattern.findall(output)[-1]
                        gse_ping_time.append(float(ping_time))
                    except IndexError:
                        pass
            if gse_ping_time:
                ap_ping_time[ap.id] = sum(gse_ping_time) / len(gse_ping_time)
            else:
                ap_ping_time[ap.id] = self.MIN_PING_TIME
            self.logger.info(
                _("连接至接入点[{ap_name}]的平均延迟为{ap_ping_time}").format(ap_name=ap.name, ap_ping_time=ap_ping_time[ap.id])
            )

            if ap_ping_time[ap.id] < min_ping_time:
                min_ping_time = ap_ping_time[ap.id]
                min_ping_ap_id = ap.id
        if is_linux:
            ssh_man.safe_close(ssh_man.ssh)
        return min_ping_ap_id, ap_ping_time, min_ping_time


class ConfigurePolicyService(AgentService):
    """
    配置网络策略
    """

    name = _("配置到Gse&Nginx的策略")

    __need_schedule__ = True
    interval = StaticIntervalGenerator(POLLING_INTERVAL)

    def __init__(self):
        super().__init__(name=self.name)

    def inputs_format(self):
        return [Service.InputItem(name="host_info", key="host_info", type="object", required=True)]

    def outputs_format(self):
        return [Service.OutputItem(name="login_ip", key="login_ip", type="str", required=True)]

    def _execute(self, data, parent_data):
        """
        添加策略的接口不能同时调用，此原子只用查询，策略由configuration_policy周期任务进行添加
        """
        host_info = data.get_one_of_inputs("host_info")
        host = Host.get_by_host_info(host_info)
        data.outputs.login_ip = host.login_ip
        data.outputs.polling_time = 0
        self.logger.info(_("等待策略生效..."))
        return True

    def schedule(self, data, parent_data, callback_data=None):
        login_ip = data.get_one_of_outputs("login_ip")
        polling_time = data.get_one_of_outputs("polling_time")
        client = VpcClient()
        is_ok, message = client.init()
        if not is_ok:
            self.logger.error(_("配置到Gse和Nginx的策略失败:{message}").format(message=message))
            return False

        policy_ip_list = client.describe_address_templates(client.ip_templates[0])
        if login_ip in policy_ip_list:
            self.logger.info(_("[{login_ip}]到Gse和Nginx的策略配置成功").format(login_ip=login_ip))
            self.finish_schedule()
            return True

        elif polling_time + POLLING_INTERVAL > POLLING_TIMEOUT / 2:
            self.logger.error(_("[{login_ip}]配置到Gse和Nginx的策略失败请联系节点管理维护人员").format(login_ip=login_ip))
            self.finish_schedule()
            return False

        data.outputs.polling_time = polling_time + POLLING_INTERVAL
        return True


class InstallService(AgentService, JobFastExecuteScriptService):
    name = _("下发脚本命令")

    def __init__(self):
        super().__init__(name=self.name)

    __need_schedule__ = True
    __multi_callback_enabled__ = True
    interval = None

    def inputs_format(self):
        return [
            Service.InputItem(name="host_info", key="host_info", type="object", required=True),
            Service.InputItem(name="is_uninstall", key="is_uninstall", type="bool", required=False),
            Service.InputItem(
                name="success_callback_step",
                key="success_callback_step",
                type="str",
                required=True,
            ),
        ]

    def _execute(self, data, parent_data):
        bk_host_id = data.get_one_of_inputs("bk_host_id")
        host_info = data.get_one_of_inputs("host_info")
        host = Host.get_by_host_info({"bk_host_id": bk_host_id} if bk_host_id else host_info)
        bk_username = data.get_one_of_inputs("bk_username")

        is_uninstall = data.get_one_of_inputs("is_uninstall")
        is_manual = host.is_manual

        if is_manual:
            self.logger.info(_("等待手动执行安装命令"))
            return True
        else:
            self.logger.info(_("开始执行远程安装"))

        # Windows相关提醒
        if host.os_type == constants.OsType.WINDOWS:
            self.logger.info(
                _(
                    "正在安装Windows AGENT, 请确认: \n"
                    "1. 检查文件共享相关服务，确认以下服务均已开启\n"
                    "    - Function Discovery Resource Publication\n"
                    "    - SSDP Discovery \n"
                    "    - UPnP Device Host\n"
                    "    - Server\n"
                    "    - NetLogon // 如果没有加入域，可以不启动这个\n"
                    "    - TCP/IP NetBIOS Helper\n"
                    "2. 开启网卡 Net BOIS \n"
                    "3. 开启文件共享 Net share \n"
                    "4. 检查防火墙是否有放开 139/135/445 端口 \n"
                )
            )

        # 生成安装命令
        try:
            installation_tool = gen_commands(host, self.id, is_uninstall)
        except GenCommandsError as e:
            self.logger.info(e.message)
            return False

        if installation_tool.script_file_name == constants.SetupScriptFileName.SETUP_PAGENT_PY.value:
            # PAGENT 走 作业平台，再 ssh 到 PAGENT，这样可以无需保存 proxy 密码
            self.logger.info(_("主机的上游节点为: {proxies}").format(proxies=",".join(installation_tool.upstream_nodes)))
            self.logger.info(_("已选择 {inner_ip} 作为本次安装的跳板机").format(inner_ip=installation_tool.jump_server.inner_ip))
            return self.execute_job_commands(
                bk_username,
                installation_tool.jump_server,
                host,
                installation_tool.run_cmd,
                installation_tool.pre_commands,
            )
        else:
            # AGENT 或 PROXY安装走 ssh或wmi 连接
            if host.os_type == constants.OsType.WINDOWS:
                self.execute_windows_commands(
                    host, [f'if not exist "{installation_tool.dest_dir}" mkdir {installation_tool.dest_dir}']
                )
                self.push_curl_exe(host, installation_tool.dest_dir)
                try:
                    return self.execute_windows_commands(host, installation_tool.win_commands)
                except socket.error:
                    self.logger.error(
                        _("连接失败，请确认节点管理后台 -> 目标机器 [{ip}] 的端口 [{port}] 策略是否开通").format(
                            ip=host.login_ip or host.inner_ip, port=host.identity.port
                        )
                    )
                    return False
            else:
                try:
                    return self.execute_linux_commands(host, installation_tool.run_cmd, installation_tool.pre_commands)
                except socket.timeout:
                    self.logger.error(
                        _("连接失败，请确认节点管理后台 -> 目标机器 [{ip}] 的端口 [{port}] 策略是否开通").format(
                            ip=host.login_ip or host.outer_ip or host.inner_ip, port=host.identity.port
                        )
                    )
                    return False

    def execute_windows_commands(self, host, commands):
        # windows command executing
        ip = host.login_ip or host.inner_ip
        identity_data = IdentityData.objects.get(bk_host_id=host.bk_host_id)
        if (identity_data.auth_type == constants.AuthType.PASSWORD and not identity_data.password) or (
            identity_data.auth_type == constants.AuthType.KEY and not identity_data.key
        ):
            self.logger.info(_("认证信息已过期, 请重装并填入认证信息"))
            raise AuthOverdueException
        retry_times = 5
        for i, cmd in enumerate(commands, 1):
            for try_time in range(retry_times):
                try:
                    if i == len(commands):
                        # Executing scripts is the last command and takes time, using asynchronous
                        self.logger.info(f"Sending install cmd: {cmd}")
                        execute_cmd(
                            cmd,
                            ip,
                            identity_data.account,
                            identity_data.password,
                            no_output=True,
                        )
                    else:
                        # Other commands is quick and depends on previous ones, using synchronous
                        self.logger.info(f"Sending cmd: {cmd}")
                        execute_cmd(cmd, ip, identity_data.account, identity_data.password)
                except ConnectionResetError as e:
                    if try_time < retry_times:
                        time.sleep(1)
                        continue
                    else:
                        raise e
                else:
                    break
        return True

    def push_curl_exe(self, host, dest_dir):
        ip = host.login_ip or host.inner_ip or host.outer_ip
        identity_data = IdentityData.objects.get(bk_host_id=host.bk_host_id)
        retry_times = 5
        for name in ("curl.exe", "curl-ca-bundle.crt", "libcurl-x64.dll"):
            for try_time in range(retry_times):
                try:
                    curl_file = str(Path.cwd() / "script_tools" / name)
                    self.logger.info(f"pushing file {curl_file} to {dest_dir}")
                    put_file(
                        curl_file,
                        dest_dir,
                        ip,
                        identity_data.account,
                        identity_data.password,
                    )
                except ConnectionResetError as e:
                    if try_time < retry_times:
                        time.sleep(1)
                        continue
                    else:
                        raise e
                else:
                    break

    def execute_job_commands(self, bk_username, proxy, host, run_cmd, pre_commands=None):
        path = os.path.join(settings.PROJECT_ROOT, "script_tools", "setup_pagent.py")
        with open(path, encoding="utf-8") as fh:
            script = fh.read()
        # 使用全业务执行作业
        bk_biz_id = settings.BLUEKING_BIZ_ID
        kwargs = {
            "bk_biz_id": bk_biz_id,
            "ip_list": [{"ip": proxy.inner_ip, "bk_cloud_id": proxy.bk_cloud_id}],
            "script_timeout": 300,
            "script_type": 1,
            "account": "root",
            "script_content": base64.b64encode(script.encode()).decode(),
            "script_param": base64.b64encode(run_cmd.encode()).decode(),
            "is_param_sensitive": 1,
        }
        try:
            data = client_v2.job.fast_execute_script(kwargs)
        except Exception as err:
            self.logger.error(f"start job failed: {err}")
            return False
        else:
            task_inst_id = data.get("job_instance_id")
            self.logger.info(
                _('作业任务ID为[{job_instance_id}]，点击跳转到<a href="{link}" target="_blank">[作业平台]</a>').format(
                    job_instance_id=task_inst_id,
                    link=f"{settings.BK_JOB_HOST}/{settings.BLUEKING_BIZ_ID}/execute/step/{task_inst_id}",
                )
            )

            task_service.callback.apply_async(
                (
                    self.id,
                    [
                        {
                            "timestamp": time.time(),
                            "level": "INFO",
                            "step": "wait_for_job",
                            "log": "waiting job result",
                            "status": "-",
                            "job_status_kwargs": {"bk_biz_id": bk_biz_id, "job_instance_id": task_inst_id},
                            "prefix": "job",
                        }
                    ],
                ),
                countdown=5,
            )
        return True

    def execute_linux_commands(self, host, run_cmd, pre_commands=None):
        if not pre_commands:
            pre_commands = []
        ssh_man = SshMan(host, self.logger)

        # 一定要先设置一个干净的提示符号，否则会导致console_ready识别失效
        ssh_man.get_and_set_prompt()
        for cmd in pre_commands:
            self.logger.info(f"Sending cmd: {cmd}")
            ssh_man.send_cmd(cmd)

        if "echo" in run_cmd:
            self.logger.info(f"Sending install cmd with host_data: {run_cmd.split('&&')[-1]}")
        else:
            self.logger.info(f"Sending install cmd: {run_cmd}")
        ssh_man.send_cmd(run_cmd, wait_console_ready=False)
        ssh_man.safe_close(ssh_man.ssh)
        return True

    def schedule(self, data, parent_data, callback_data=None):
        """
        回调函数
        :param data:
        :param parent_data:
        :param callback_data: 回调数据
        [
            {
                "timestamp": "1580870937",
                "level": "INFO",
                "step": "check_deploy_result",
                "log": "gse agent has been deployed successfully",
                "status": "DONE",
                "job_status_kwargs": {
                    "bk_biz_id": bk_biz_id,
                    "job_instance_id": job_instance_id,
                }
            }
        ]
        :return:
        """
        # 等待脚本上报日志
        for log in callback_data:

            # 作业平台回调
            job_status_kwargs = log.get("job_status_kwargs")
            if job_status_kwargs:
                # 判断任务是否在执行中或成功
                job_instance_log = client_v2.job.get_job_instance_log(job_status_kwargs)

                job_status = job_instance_log[0].get("status", "")
                if job_status == JobDataStatus.PENDING:
                    self.logger.info(f"[job] {job_status_kwargs['job_instance_id']} is pending")
                    task_service.callback.apply_async(
                        (
                            self.id,
                            [
                                {
                                    "timestamp": time.time(),
                                    "level": "INFO",
                                    "step": "wait_for_job",
                                    "log": "waiting job result",
                                    "status": "-",
                                    "job_status_kwargs": job_status_kwargs,
                                }
                            ],
                        ),
                        countdown=5,
                    )
                    return True
                elif job_status == JobDataStatus.SUCCESS:
                    bk_host_id = data.get_one_of_inputs("bk_host_id")
                    host_info = data.get_one_of_inputs("host_info")
                    host = Host.get_by_host_info({"bk_host_id": bk_host_id} if bk_host_id else host_info)
                    self.logger.info(
                        f"[job] {job_status_kwargs['job_instance_id']} is succeeded. Waiting for script report. "
                        f"If there is no any report for a long time, please check the connection "
                        f"from pagent({host.inner_ip} to proxy({host.jump_server.inner_ip}):"
                        f"{settings.BK_NODEMAN_NGINX_DOWNLOAD_PORT},{settings.BK_NODEMAN_NGINX_PROXY_PASS_PORT}."
                    )
                    return True
                elif job_status == JobDataStatus.FAILED:
                    self.logger.error(f"[job] {job_status_kwargs['job_instance_id']} is failed")
                    try:
                        log_content = job_instance_log[0]["step_results"][0]["ip_logs"][0]["log_content"]
                    except (IndexError, KeyError):
                        self.logger.error("[job] get job instance log error!")
                    else:
                        self.logger.error(f"[job] {log_content}")
                    self.finish_schedule()
                    return False

            # 日志上报
            _log = f'{log.get("step")} {log.get("status")} {log.get("log")}'
            tag = log.get("prefix") if log.get("prefix") else "[script]"
            if log["status"] == "FAILED":
                self.logger.error(f"{tag} {_log}")
                self.finish_schedule()
                return False
            else:
                self.logger.info(f"{tag} {_log}")

            if log["step"] == "report_cpu_arch":
                # 上报主机的CPU架构
                bk_host_id = data.get_one_of_inputs("bk_host_id")
                host_info = data.get_one_of_inputs("host_info")
                host = Host.get_by_host_info({"bk_host_id": bk_host_id} if bk_host_id else host_info)
                host.cpu_arch = log["log"]
                host.save(update_fields=["cpu_arch"])

            if log["status"] == "DONE" and log["step"] == data.get_one_of_inputs("success_callback_step"):
                self.finish_schedule()
                return True


class PushUpgradePackageService(JobFastPushFileService):
    name = _("下发升级包")

    def __init__(self):
        super().__init__(name=self.name)

    def inputs_format(self):
        inputs = super().inputs_format()
        inputs.append(Service.InputItem(name="host_info", key="host_info", type="object", required=True))
        return inputs

    def outputs_format(self):
        outputs = super().outputs_format()
        outputs.append(Service.OutputItem(name="package_name", key="package_name", type="str", required=True))
        return outputs

    def execute(self, data, parent_data):
        self.logger.info(_("开始下发升级包"))
        host_info = data.get_one_of_inputs("host_info")
        host = Host.get_by_host_info(host_info)
        nginx_path = host.ap.nginx_path or settings.DOWNLOAD_PATH
        data.inputs.file_target_path = host.agent_config["temp_path"]

        os_type = host.os_type.lower()

        # 根据节点类型、位数、系统等组装包名
        gse_type = "proxy" if host.node_type == constants.NodeType.PROXY else "client"
        package_name = f"gse_{gse_type}-{os_type}-{host.cpu_arch}_upgrade.tgz"
        files = [package_name]

        # windows机器需要添加解压文件
        if os_type == constants.OsType.WINDOWS:
            files.extend(["7z.dll", "7z.exe"])
        file_source = [{"files": [f"{nginx_path}/{file}" for file in files]}]

        data.inputs.file_source = file_source

        data.outputs.package_name = package_name
        return super().execute(data, parent_data)


class RunUpgradeCommandService(JobFastExecuteScriptService):
    name = _("下发升级脚本命令")

    def __init__(self):
        super().__init__(name=self.name)

    def inputs_format(self):
        inputs = super().inputs_format()
        inputs.append(Service.InputItem(name="host_info", key="host_info", type="object", required=True))
        return inputs

    def execute(self, data, parent_data):
        self.logger.info(_("开始执行升级脚本"))
        host_info = data.get_one_of_inputs("host_info")
        package_name = data.get_one_of_inputs("package_name")
        host = Host.get_by_host_info(host_info)
        agent_config = host.agent_config
        temp_path = agent_config["temp_path"]
        setup_path = agent_config["setup_path"]
        if host.os_type.lower() == "windows":
            # 1. 停止agent，此时无法从Job获取任务结果
            # 2. 解压升级包到目标路径，使用 -aot 参数把已存在的二进制文件重命名
            # 3. 启动agent
            scripts = (
                'reg add "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" '
                '/v gse_agent /t reg_sz /d "{setup_path}\\agent\\bin\\gsectl.bat start" /f 1>nul 2>&1'
                " && start gsectl.bat stop && ping -n 20 127.0.0.1 >> c:\\ping_ip.txt && {temp_path}\\7z.exe x"
                " {temp_path}\\{package_name} -o{temp_path} -y 1>nul 2>&1 && {temp_path}\\7z.exe x "
                "{temp_path}\\{package_name_tar} -aot -o{setup_path} -y 1>nul 2>&1 && gsectl.bat start"
            )
            data.inputs.script_content = scripts.format(
                setup_path=setup_path,
                temp_path=temp_path,
                package_name=package_name,
                package_name_tar=package_name.replace("tgz", "tar"),
            )
        else:
            path = os.path.join(settings.PROJECT_ROOT, "script_tools", "upgrade_agent.sh.tpl")
            with open(path, encoding="utf-8") as fh:
                script = fh.read()
            if host.node_type == constants.NodeType.PROXY:
                node_type = "proxy"
                reload_cmd = """
result=0
count=0
for proc in gse_agent gse_transit gse_btsvr gse_data; do
     [ -f {setup_path}/{node_type}/bin/$proc ] && cd {setup_path}/{node_type}/bin && ./$proc --reload && \
     count=$((count + 1))
     sleep 1
     result=$((result + $?))
done
if [[ $result -gt 0 || $count -lt 3 ]]; then
   cd {setup_path}/{node_type}/bin && ./gsectl restart all
fi
                """.format(
                    setup_path=setup_path, node_type=node_type
                )
            else:
                node_type = "agent"
                reload_cmd = "cd {setup_path}/{node_type}/bin && ./gse_agent --reload || ./gsectl restart all".format(
                    setup_path=setup_path, node_type=node_type
                )
            data.inputs.script_content = script.format(
                setup_path=setup_path,
                temp_path=temp_path,
                package_name=package_name,
                node_type=node_type,
                reload_cmd=reload_cmd,
            )
        return super().execute(data, parent_data)

    def schedule(self, data, parent_data, callback_data=None):
        host_info = data.get_one_of_inputs("host_info")
        host = Host.get_by_host_info(host_info)
        if host.os_type.lower() == "windows":
            self.finish_schedule()
            return True
        else:
            return super().schedule(data, parent_data, callback_data=callback_data)


class RestartService(AgentService):
    name = _("重启")

    def __init__(self):
        super().__init__(name=self.name)

    def inputs_format(self):
        return [
            Service.InputItem(name="host_info", key="host_info", type="object", required=True),
            Service.InputItem(name="bk_username", key="bk_username", type="str", required=True),
        ]

    def _execute(self, data, parent_data):
        self.logger.info(_("调用作业平台重启Agent"))
        host_info = data.get_one_of_inputs("host_info")
        bk_username = data.get_one_of_inputs("bk_username")
        host = Host.get_by_host_info({"bk_host_id": host_info["bk_host_id"]})
        if host.node_type == constants.NodeType.PROXY and not host.os_type:
            host.os_type = constants.OsType.LINUX
            host.save()
        install_path = host.agent_config["setup_path"]
        install_path = suffix_slash(host.os_type, install_path)
        if host.node_type == constants.NodeType.PROXY:
            sub_path = "proxy"
        else:
            sub_path = "agent"

        if host.os_type.lower() == "windows":
            accounts = ["system", "Administrator"]
            script_type_num = 2
            script_content = base64.b64encode(f"{install_path}agent\\bin\\gsectl.bat restart".encode()).decode()
        else:
            accounts = ["root"]
            script_type_num = 1
            script_content = base64.b64encode(
                f"{install_path}{sub_path}/bin/gsectl restart >/dev/null 2>&1".encode()
            ).decode()

        for index, account in enumerate(accounts, 1):
            bk_biz_id = host.bk_biz_id
            kwargs = {
                "bk_biz_id": bk_biz_id,
                "ip_list": [{"ip": host.inner_ip, "bk_cloud_id": host.bk_cloud_id}],
                "script_timeout": 300,
                "script_type": script_type_num,
                "account": account,
            }
            kwargs.update({"script_content": script_content})
            self.logger.info("job parameter is：\n{}\n".format(json.dumps(kwargs, indent=2)))
            try:
                data = client_v2.job.fast_execute_script(kwargs, bk_username=bk_username)
            except Exception as err:
                if index != len(accounts):
                    self.logger.info("start job failed: {} ({}/{})".format(err, index, len(accounts)))
                    continue
                self.logger.error(f"start job failed: {err}")
                return False
            else:
                task_inst_id = data.get("job_instance_id")
                time.sleep(5)
                job_status_kwargs = {
                    "bk_biz_id": bk_biz_id,
                    "job_instance_id": task_inst_id,
                }
                job_status_data = client_v2.job.get_job_instance_status(job_status_kwargs, bk_username=bk_username)
                # 判断任务是否在执行中
                if job_status_data.get("job_instance", {}).get("status", "") != 2:
                    self.logger.info(
                        f"[{task_inst_id}]Job execution failed, please go to the Job"
                        " platform to check the task execution details."
                    )
                    return False
                self.logger.info(f"[{task_inst_id}]start job success，begin poll agent status")
                break

        # 下发job作业后等待5秒后再开始查状态,
        time.sleep(5)
        return True


class GetAgentStatusService(AgentService):
    name = _("查询 GSE 状态")

    def __init__(self):
        super().__init__(name=self.name)

    __need_schedule__ = True
    interval = StaticIntervalGenerator(5)

    def inputs_format(self):
        return [
            Service.InputItem(name="host_info", key="host_info", type="object", required=True),
            Service.InputItem(name="expect_status", key="expect_status", type="str", required=True),
        ]

    def _execute(self, data, parent_data):
        expect_status = data.get_one_of_inputs("expect_status")
        self.logger.info(_("期望的GSE主机状态为{expect_status}").format(expect_status=expect_status))
        return True

    def schedule(self, data, parent_data, callback_data=None):
        expect_status = data.get_one_of_inputs("expect_status")
        bk_host_id = data.get_one_of_inputs("bk_host_id")
        host_info = data.get_one_of_inputs("host_info")
        host = Host.get_by_host_info({"bk_host_id": bk_host_id} if bk_host_id else host_info)
        status_queryset = ProcessStatus.objects.filter(
            bk_host_id=host.bk_host_id,
            name=ProcessStatus.GSE_AGENT_PROCESS_NAME,
            source_type=ProcessStatus.SourceType.DEFAULT,
        )
        if not status_queryset:
            # 需要创建process status
            status = ProcessStatus.objects.create(
                bk_host_id=host.bk_host_id,
                name=ProcessStatus.GSE_AGENT_PROCESS_NAME,
                source_type=ProcessStatus.SourceType.DEFAULT,
            )
        elif status_queryset.count() > 1:
            # 需要清理掉重复记录
            status = status_queryset.first()
            status_queryset.exclude(id=status.id).delete()
        else:
            status = status_queryset.first()

        bk_inner_ip = host.inner_ip
        bk_cloud_id = host.bk_cloud_id
        params = {"hosts": [{"ip": bk_inner_ip, "bk_cloud_id": bk_cloud_id}]}
        host_key = f"{bk_cloud_id}:{bk_inner_ip}"
        try:
            agent_status = client_v2.gse.get_agent_status(params)[host_key]
            agent_info = client_v2.gse.get_agent_info(params)[host_key]
        except Exception as error:
            self.logger.error(f"get agent status error, {error}")
            return

        status.status = constants.PROC_STATUS_DICT[agent_status["bk_agent_alive"]]
        status.version = agent_info["version"] if status.status == constants.PROC_STATUS_DICT[1] else ""
        status.save(update_fields=["status", "version"])
        self.logger.info(
            _("查询GSE主机({host_key})状态为{status}, 版本为{version}").format(
                host_key=host_key, status=status.status, version=status.version
            )
        )

        if status.status == expect_status:
            self.finish_schedule()
            # 更新主机来源
            if host.node_from == constants.NodeFrom.CMDB:
                host.node_from = constants.NodeFrom.NODE_MAN
                host.save(update_fields=["node_from"])
            return True

        if self.interval.count > 60:
            self.logger.error(_("查询GSE状态超时"))
            self.finish_schedule()
            return False


class UpdateProcessStatusService(AgentService):
    name = _("更新主机进程状态")

    def __init__(self):
        super().__init__(name=self.name)

    def inputs_format(self):
        return [
            Service.InputItem(name="host_info", key="host_info", type="object", required=True),
            Service.InputItem(name="status", key="status", type="str", required=True),
        ]

    def _execute(self, data, parent_data):
        status = data.get_one_of_inputs("status")
        bk_host_id = data.get_one_of_inputs("bk_host_id")
        host_info = data.get_one_of_inputs("host_info")
        if status == constants.ProcStateType.NOT_INSTALLED:
            host = Host.get_by_host_info({"bk_host_id": bk_host_id} if bk_host_id else host_info)
            host.node_from = "CMDB"
            host.save()
            process = ProcessStatus.objects.get(bk_host_id=host.bk_host_id, name="gseagent")
            process.status = constants.ProcStateType.NOT_INSTALLED
            process.save()

        self.logger.info(_("更新主机状态为{status}").format(status=status))
        return True


class UpdateJobStatusService(AgentService):
    name = _("更新任务状态")

    def __init__(self):
        super().__init__(name=self.name)

    def inputs_format(self):
        return [
            Service.InputItem(name="host_info", key="host_info", type="object", required=True),
            Service.InputItem(name="expect_status", key="expect_status", type="int", required=True),
        ]

    def _execute(self, data, parent_data):
        update_job_status(self.root_pipeline_id, result=True)
        return True


class OperatePluginService(AgentService, GseBaseService):
    """
    操作插件基类
    """

    name = _("操作插件")
    __need_schedule__ = True
    interval = StaticIntervalGenerator(POLLING_INTERVAL)

    def __init__(self):
        super().__init__(name=self.name)

    def _execute(self, data, parent_data):
        bk_username = data.get_one_of_inputs("bk_username")
        plugin_name = data.get_one_of_inputs("plugin_name")
        action = data.get_one_of_inputs("action")
        bk_host_id = data.get_one_of_inputs("bk_host_id")
        host_info = data.get_one_of_inputs("host_info")
        host = Host.get_by_host_info({"bk_host_id": bk_host_id} if bk_host_id else host_info)

        newest = (
            Packages.objects.filter(project=plugin_name, cpu_arch=constants.CpuType.x86_64)
            .values("os")
            .annotate(max_id=Max("id"))
        )

        packages = Packages.objects.filter(id__in=Subquery(newest.values("max_id")))
        os_type = host.os_type.lower()
        package_by_os = {package.os: package for package in packages}
        if os_type not in package_by_os:
            self.logger.info(f"{plugin_name} dose not support {os_type}!")
            return True
        package = package_by_os[os_type]
        control = package.proc_control
        control = {
            "start_cmd": control.start_cmd,
            "stop_cmd": control.stop_cmd,
            "restart_cmd": control.restart_cmd,
            "reload_cmd": control.reload_cmd or control.restart_cmd,
            "kill_cmd": control.kill_cmd,
            "version_cmd": control.version_cmd,
            "health_cmd": control.health_cmd,
        }

        gse_client = GseClient(username=bk_username, os_type=os_type, _logger=self.logger)

        hosts = [
            {"bk_cloud_id": host.bk_cloud_id, "ip": host.inner_ip, "bk_supplier_id": constants.DEFAULT_SUPPLIER_ID}
        ]
        if package.os == constants.PluginOsType.windows:
            path_handler = ntpath
        else:
            path_handler = posixpath

        setup_path = path_handler.join(
            package.proc_control.install_path, constants.PluginChildDir.OFFICIAL.value, "bin"
        )
        pid_path = package.proc_control.pid_path

        result = gse_client.register_process(hosts, control, setup_path, pid_path, plugin_name, plugin_name)
        if result["failed"]:
            data.outputs.result = result  # result字段存注册结果
            self.logger.error("GSE register process failed. result:\n[{}]".format(json.dumps(result, indent=2)))
            data.outputs.ex_data = "以下主机注册进程失败：{}".format(
                ",".join(["[{}] {}".format(host["ip"], host.get("error_msg")) for host in result["failed"]])
            )
            return False
        # self.logger.info('GSE register process success. result->[{}]'.format(json.dumps(result, indent=2)))
        self.logger.info("GSE register process success.")
        # 从 GSE Client 获取相应的动作
        operate_method = getattr(gse_client, "{}_process".format(action))
        task_id = operate_method(hosts, plugin_name)
        self.logger.info("GSE {} Process and get task_id: [{}]".format(action.upper(), task_id))
        data.outputs.task_id = task_id
        data.outputs.polling_time = 0
        return True

    def schedule(self, data, parent_data, callback_data=None):
        task_id = data.get_one_of_outputs("task_id")
        if not task_id:
            self.finish_schedule()
            return True

        bk_username = data.get_one_of_inputs("bk_username")
        bk_host_id = data.get_one_of_inputs("bk_host_id")
        host_info = data.get_one_of_inputs("host_info")
        host = Host.get_by_host_info({"bk_host_id": bk_host_id} if bk_host_id else host_info)
        polling_time = data.get_one_of_outputs("polling_time")
        gse_client = GseClient(username=bk_username, os_type=host.os_type.lower(), _logger=self.logger)

        is_finished, task_result = gse_client.get_task_result(task_id)
        self.logger.info(
            "GSE(task_id: [{}]) get schedule task result:\n[{}].".format(task_id, json.dumps(task_result, indent=2))
        )
        if is_finished:
            data.outputs.task_result = task_result  # task_result字段保存轮询结果
            if task_result["failed"]:
                self.logger.error(
                    "gse task(task_id: [{}]) failed. task_result:\n[{}]".format(
                        task_id, json.dumps(task_result, indent=2)
                    ),
                )
                data.outputs.ex_data = "以下主机操作进程失败：{}".format(self.format_error_msg(task_result))
                return False
            self.logger.info("GSE(task_id: [{}]) get schedule finished].".format(task_id))
            self.finish_schedule()
        elif polling_time + POLLING_INTERVAL > POLLING_TIMEOUT:
            data.outputs.ex_data = "任务轮询超时"
            self.logger.error("GSE(task_id: [{}]) schedule timeout.".format(task_id))
            return False

        data.outputs.polling_time = polling_time + POLLING_INTERVAL
        return True

    def inputs_format(self):
        return [
            Service.InputItem(name="host_info", key="host_info", type="object", required=True),
            Service.InputItem(name="bk_username", key="bk_username", type="str", required=True),
            Service.InputItem(name="plugin_name", key="plugin_name", type="str", required=True),
            Service.InputItem(name="action", key="action", type="str", required=True),
        ]


class WaitService(AgentService):
    name = _("等待")

    __need_schedule__ = True
    interval = StaticIntervalGenerator(5)

    def __init__(self):
        super().__init__(name=self.name)

    def inputs_format(self):
        return [
            Service.InputItem(name="sleep_time", key="sleep_time", type="int", required=True),
        ]

    def _execute(self, data, parent_data):
        return True

    def schedule(self, data, parent_data, callback_data=None):
        # 等待一段时间，用于重启Agent、安装Proxy等场景
        sleep_time = data.get_one_of_inputs("sleep_time", 5)
        time.sleep(sleep_time)
        self.finish_schedule()
        return True


class CheckAgentStatusService(AgentService):
    name = _("检查Agent状态")

    def __init__(self):
        super().__init__(name=self.name)

    def inputs_format(self):
        return [
            Service.InputItem(name="bk_host_id", key="bk_host_id", type="int", required=True),
        ]

    def _execute(self, data, parent_data):
        bk_host_id = data.get_one_of_inputs("bk_host_id")
        process_status = ProcessStatus.objects.filter(bk_host_id=bk_host_id, name=ProcessStatus.GSE_AGENT_PROCESS_NAME)
        running_status = process_status.filter(status=constants.ProcStateType.RUNNING)
        process_status_count = process_status.count()

        if running_status:
            if process_status_count > 1:
                # 如果状态记录重复进行清理
                process_status.exclude(id=running_status.first().id).delete()
            self.logger.info(_("Agent 状态【正常】"))
            return True
        else:
            if process_status_count > 1:
                # 如果状态记录重复进行清理
                process_status.exclude(id=process_status.first().id).delete()
            self.logger.error(_("Agent 状态【异常】"))
            return False


class RenderAndPushGseConfigService(JobPushMultipleConfigFileService):
    name = _("渲染并下发Agent配置")

    def __init__(self):
        super().__init__(name=self.name)

    def inputs_format(self):
        return [
            Service.InputItem(name="bk_host_id", key="bk_host_id", type="int", required=True),
            Service.InputItem(name="host_info", key="host_info", type="object", required=True),
        ]

    def execute(self, data, parent_data):
        file_name = "agent.conf"
        host_info = data.get_one_of_inputs("host_info")
        host = Host.get_by_host_info(host_info)

        # 路径处理器
        path_handler = ntpath if host.os_type == constants.OsType.WINDOWS else posixpath

        setup_path = host.agent_config["setup_path"]

        # 新配置写入数据库
        extra_data = {
            "peer_exchange_switch_for_agent": host_info.get("peer_exchange_switch_for_agent", True),
            "bt_speed_limit": host_info.get("bt_speed_limit", 0),
        }
        if host_info.get("data_path"):
            extra_data.update({"data_path": host_info["data_path"]})
        host.extra_data = extra_data
        host.ap_id = host_info["ap_id"]
        host.save()

        # 生成配置
        config = generate_gse_config(
            host_info["bk_cloud_id"], file_name, host_info["host_node_type"].lower(), host_info["bk_host_innerip"]
        )
        node_type = "proxy" if host.node_type == constants.NodeType.PROXY else "agent"

        file_params = [
            {
                "file_target_path": path_handler.join(setup_path, node_type, "etc"),
                "file_list": [{"name": file_name, "content": config}],
            }
        ]

        data.inputs.file_params = file_params
        return super(RenderAndPushGseConfigService, self).execute(data, parent_data)


class ReloadAgentConfigService(JobFastExecuteScriptService):
    """
    重载Agent配置
    """

    def execute(self, data, parent_data):
        host_info = data.get_one_of_inputs("host_info")
        host = Host.get_by_host_info(host_info)

        # 路径处理器
        path_handler = ntpath if host.os_type == constants.OsType.WINDOWS else posixpath
        node_type = "proxy" if host.node_type == constants.NodeType.PROXY else "agent"
        setup_path = host.agent_config["setup_path"]
        agent_path = path_handler.join(setup_path, node_type, "bin")
        script_content = f"cd {agent_path} && ./gse_agent --reload"
        data.inputs.script_content = script_content
        return super(ReloadAgentConfigService, self).execute(data, parent_data)


class CheckPolicyGseToProxyService(JobFastExecuteScriptService):
    """
    检测GSE svr到proxy的策略
    """

    def inputs_format(self):
        return [
            Service.InputItem(name="bk_host_id", key="bk_host_id", type="int", required=True),
        ]

    @staticmethod
    def query_gse_svr_biz(gse_svr_list):
        # 查询GSE SVR所在业务
        if settings.JOB_VERSION == "V3":
            bk_biz_id = settings.BLUEKING_BIZ_ID
        else:
            # 查询bk_host_id
            bk_host_ids = (
                client_v2.cc.list_hosts_without_biz(
                    {
                        "page": {"start": 0, "limit": 500, "sort": "bk_host_id"},
                        "fields": ["bk_host_id"],
                        "host_property_filter": {
                            "condition": "AND",
                            "rules": [
                                {
                                    "field": "bk_host_innerip",
                                    "operator": "in",
                                    "value": [svr["inner_ip"] for svr in gse_svr_list],
                                },
                                {"field": "bk_cloud_id", "operator": "equal", "value": constants.DEFAULT_CLOUD},
                            ],
                        },
                    }
                ).get("info")
                or []
            )
            host_data = (
                client_v2.cc.find_host_biz_relations({"bk_host_id": [_host["bk_host_id"] for _host in bk_host_ids]})
                or []
            )

            if not host_data:
                return None

            bk_biz_id = host_data[0]["bk_biz_id"]
        return bk_biz_id

    def execute(self, data, parent_data):
        bk_host_id = data.get_one_of_inputs("bk_host_id")
        host = Host.get_by_host_info({"bk_host_id": bk_host_id})
        port_config = host.ap.port_config
        script_content = """
#!/bin/bash
is_target_reachable () {
    local ip=${1}
    local target_port=$2
    local _port err ret

    if [[ $target_port =~ [0-9]+-[0-9]+ ]]; then
        target_port=$(seq ${target_port//-/ })
    fi
    for _port in $target_port; do
        timeout 5 bash -c ">/dev/tcp/$ip/$_port" 2>/dev/null
        case $? in
            0) return 0 ;;
            1) ret=1 && echo "GSE server connect to proxy($ip:$_port) connection refused" ;;
            ## 超时的情况，只有要一个端口是超时的情况，认定为网络不通，不继续监测
            124) echo "GSE server connect to proxy($ip:$target_port) failed: NETWORK TIMEOUT %(msg)s" && return 124;;
        esac
    done

    return $ret;
}
ret=0
is_target_reachable %(proxy_ip)s %(btsvr_thrift_port)s || ret=$?
is_target_reachable %(proxy_ip)s %(bt_port)s-%(tracker_port)s || ret=$?
exit $ret
""" % {
            "proxy_ip": host.outer_ip,
            "btsvr_thrift_port": port_config.get("btsvr_thrift_port"),
            "bt_port": port_config.get("bt_port"),
            "tracker_port": port_config.get("tracker_port"),
            "msg": _("请检查数据传输IP是否正确或策略是否开通"),
        }

        gse_svr_biz = self.query_gse_svr_biz(host.ap.btfileserver)
        if not gse_svr_biz:
            self.logger.error(_("查询GSE Svr业务失败，请确认GSE Svr是否存在CMDB中"))
            return False

        data.inputs.job_client = {
            "bk_biz_id": gse_svr_biz,
            "username": settings.SYSTEM_USE_API_ACCOUNT,
            "os_type": "linux",
        }
        data.inputs.ip_list = [
            {"ip": svr["inner_ip"], "bk_cloud_id": constants.DEFAULT_CLOUD} for svr in host.ap.btfileserver
        ]
        data.inputs.script_content = script_content
        return super(CheckPolicyGseToProxyService, self).execute(data, parent_data)


class QueryTjjPasswordComponent(Component):
    name = _("查询铁将军密码")
    code = "query_tjj_password"
    bound_service = QueryTjjPasswordService


class ChooseAccessPointComponent(Component):
    name = _("选择接入点")
    code = "choose_access_point"
    bound_service = ChooseAccessPointService


class ConfigurePolicyComponent(Component):
    name = _("配置策略")
    code = "configure_policy"
    bound_service = ConfigurePolicyService


class InstallComponent(Component):
    name = _("安装")
    code = "install"
    bound_service = InstallService


class PushUpgradePackageComponent(Component):
    name = _("升级")
    code = "push_upgrade_package"
    bound_service = PushUpgradePackageService


class RunUpgradeCommandComponent(Component):
    name = _("升级")
    code = "run_upgrade_command"
    bound_service = RunUpgradeCommandService


class RestartComponent(Component):
    name = _("重启")
    code = "restart"
    bound_service = RestartService


class GetAgentStatusComponent(Component):
    name = _("查询Agent状态")
    code = "get_agent_status"
    bound_service = GetAgentStatusService


class UpdateProcessStatusComponent(Component):
    name = _("更新主机进程状态")
    code = "update_process_status"
    bound_service = UpdateProcessStatusService


class RegisterHostComponent(Component):
    name = _("注册主机到配置平台")
    code = "register_host_to_cmdb"
    bound_service = RegisterHostService


class UpdateJobStatusComponent(Component):
    name = _("更新任务状态")
    code = "update_job_status"
    bound_service = UpdateJobStatusService


class OperatePluginComponent(Component):
    name = _("操作插件")
    code = "operate_plugin"
    bound_service = OperatePluginService


class WaitComponent(Component):
    name = _("等待")
    code = "wait"
    bound_service = WaitService


class CheckAgentStatusComponent(Component):
    name = _("检查Agent状态")
    code = "agent_check_agent_status"
    bound_service = CheckAgentStatusService


class RenderAndPushGseConfigComponent(Component):
    name = _("渲染并下发Agent配置")
    code = "render_and_push_gse_config"
    bound_service = RenderAndPushGseConfigService


class ReloadAgentConfigComponent(Component):
    name = _("重载Agent配置")
    code = "reload_agent_config"
    bound_service = ReloadAgentConfigService


class CheckPolicyGseToProxyComponent(Component):
    name = _("检测GSE Server到Proxy策略")
    code = "check_policy_gse_to_proxy"
    bound_service = CheckPolicyGseToProxyService
