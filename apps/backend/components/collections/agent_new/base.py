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
import abc
import random
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Match,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)

import wrapt
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from apps.backend.agent.tools import InstallationTools, batch_gen_commands
from apps.backend.exceptions import OsVersionPackageValidationError
from apps.backend.subscription.steps.agent_adapter.adapter import AgentStepAdapter
from apps.node_man import constants, models

from .. import job
from ..base import BaseService, CommonData


class AgentBaseService(BaseService, metaclass=abc.ABCMeta):
    """
    AGENT安装基类
    """

    def sub_inst_failed_handler(self, sub_inst_ids: Union[List[int], Set[int]]):
        """
        订阅实例失败处理器
        :param sub_inst_ids: 订阅实例ID列表/集合
        """
        pass

    @classmethod
    def get_common_data(cls, data):
        """
        初始化常用数据，注意这些数据不能放在 self 属性里，否则会产生较大的 process snap shot，
        另外也尽量不要在 schedule 中使用，否则多次回调可能引起性能问题
        """

        common_data = super().get_common_data(data)

        # 默认接入点
        default_ap = models.AccessPoint.get_default_ap()
        # 主机ID - 接入点 映射关系
        # 引入背景：在聚合流程中，类似 host.agent_config, host.ap 的逻辑会引发 n + 1 DB查询问题
        host_id__ap_map: Dict[int, models.AccessPoint] = {}

        for bk_host_id in common_data.bk_host_ids:
            host = common_data.host_id_obj_map[bk_host_id]
            # 有两种情况需要使用默认接入点
            # 1. 接入点已被删除
            # 2. 主机未选择接入点 ap_id = -1
            host_id__ap_map[bk_host_id] = common_data.ap_id_obj_map.get(host.ap_id, default_ap)

        agent_step_adapter: AgentStepAdapter = AgentStepAdapter(common_data.subscription_step)

        return AgentCommonData(
            bk_host_ids=common_data.bk_host_ids,
            host_id_obj_map=common_data.host_id_obj_map,
            ap_id_obj_map=common_data.ap_id_obj_map,
            subscription=common_data.subscription,
            subscription_step=common_data.subscription_step,
            subscription_instances=common_data.subscription_instances,
            subscription_instance_ids=common_data.subscription_instance_ids,
            sub_inst_id__host_id_map=common_data.sub_inst_id__host_id_map,
            host_id__sub_inst_id_map=common_data.host_id__sub_inst_id_map,
            # Agent 新增的公共数据
            default_ap=default_ap,
            host_id__ap_map=host_id__ap_map,
            agent_step_adapter=agent_step_adapter,
        )

    @classmethod
    def get_general_node_type(cls, node_type: str) -> str:
        """
        获取广义上的节点类型，既仅为 proxy 或 agent
        :param node_type: 取值参考 models.HOST.node_type
        :return:
        """
        return (constants.NodeType.AGENT.lower(), constants.NodeType.PROXY.lower())[
            node_type == constants.NodeType.PROXY
        ]

    @classmethod
    def get_agent_pkg_name(
        cls,
        common_data: "AgentCommonData",
        host: models.Host,
        is_upgrade: bool = False,
        return_name_with_cpu_tmpl: bool = False,
    ) -> str:
        """
        获取 Agent 升级包名称
        :param common_data: AgentCommonData
        :param host: models.Host
        :param is_upgrade: bool 是否升级包
        :param return_name_with_cpu_tmpl: 是否返回带 cpu 模板的名称
        :return:
        """
        # GSE2.0 安装包和升级包复用同一个包
        package_type = ("client", "proxy")[host.node_type == constants.NodeType.PROXY]
        agent_step_adapter = common_data.agent_step_adapter
        if not agent_step_adapter.is_legacy:
            setup_info = agent_step_adapter.get_setup_info()
            return f"{setup_info.name}-{setup_info.version}.tgz"

        # GSE1.0 的升级包是独立的，添加了 _upgrade 后缀
        pkg_suffix = "_upgrade" if is_upgrade else ""
        if host.os_version:
            major_version_number = None
            if host.os_type == constants.OsType.AIX:
                major_version_match: Optional[Match] = re.compile(r"^(?P<version>\d+).\d+.*$").search(
                    host.os_version or ""
                )
                major_version_number: Optional[str] = (
                    major_version_match.group("version") if major_version_match else ""
                )
            if not major_version_number:
                raise OsVersionPackageValidationError(os_version=host.os_version, os_type=host.os_type)
            agent_pkg_name = (
                f"gse_{package_type}-{host.os_type.lower()}{major_version_number}-" + "{cpu_arch}" + f"{pkg_suffix}.tgz"
            )
        else:
            agent_pkg_name = f"gse_{package_type}-{host.os_type.lower()}-" + "{cpu_arch}" + f"{pkg_suffix}.tgz"

        return (agent_pkg_name.format(cpu_arch=host.cpu_arch), agent_pkg_name)[return_name_with_cpu_tmpl]

    @classmethod
    def get_agent_pkg_dir(cls, common_data: "AgentCommonData", host: models.Host) -> str:
        """
        获取 Agent 安装包目录
        :param common_data: AgentCommonData
        :param host: models.Host
        :return:
        """
        host_ap = common_data.host_id__ap_map[host.bk_host_id]
        download_path = host_ap.nginx_path or settings.DOWNLOAD_PATH
        if common_data.agent_step_adapter.is_legacy:
            # 旧版本 Agent 安装包位于下载目录
            agent_path = download_path
        else:
            # 新版本 Agent 目录规则为 agent/{os}/{cpu_arch}/
            # 具体参考：apps/backend/agent/artifact_builder/base.py make_and_upload_package
            agent_path = constants.LINUX_SEP.join([download_path, "agent", host.os_type.lower()])
        return agent_path

    @staticmethod
    def get_cloud_id__proxies_map(bk_cloud_ids: Iterable[int]) -> Dict[int, List[models.Host]]:
        proxies = models.Host.objects.filter(bk_cloud_id__in=set(bk_cloud_ids), node_type=constants.NodeType.PROXY)
        proxy_host_ids = [proxy.bk_host_id for proxy in proxies]
        alive_proxy_host_ids = models.ProcessStatus.objects.filter(
            bk_host_id__in=proxy_host_ids,
            name=models.ProcessStatus.GSE_AGENT_PROCESS_NAME,
            status=constants.ProcStateType.RUNNING,
        ).values_list("bk_host_id", flat=True)
        alive_proxy_host_ids: Set[int] = set(alive_proxy_host_ids)

        cloud_id__proxies_map: Dict[int, List[models.Host]] = defaultdict(list)
        for proxy in proxies:
            proxy.status = (constants.ProcStateType.TERMINATED, constants.ProcStateType.RUNNING)[
                proxy.bk_host_id in alive_proxy_host_ids
            ]
            cloud_id__proxies_map[proxy.bk_cloud_id].append(proxy)
        return cloud_id__proxies_map

    def get_host_id__install_channel_map(
        self,
        hosts: List[models.Host],
        host_id__sub_inst_id: Dict[int, int],
        host_id__ap_map: Dict[int, models.AccessPoint],
        cloud_id__proxies_map: Dict[int, List[models.Host]],
    ) -> Dict[int, Tuple[Optional[models.Host], Dict[str, List]]]:
        install_channel_ids: List[int] = list({host.install_channel_id for host in hosts})
        install_channel_id__jump_servers_map: Dict[
            int, List[models.Host]
        ] = models.InstallChannel.install_channel_id__host_objs_map(install_channel_ids)

        # 建立通道ID - 通道的映射关系
        id__install_channel_obj_map: Dict[int, models.InstallChannel] = {}
        for install_channel_obj in models.InstallChannel.objects.filter(id__in=install_channel_ids):
            id__install_channel_obj_map[install_channel_obj.id] = install_channel_obj

        cloud_id__alive_proxies_map: Dict[int, List[models.Host]] = defaultdict(list)
        for cloud_id, proxies in cloud_id__proxies_map.items():
            cloud_id__alive_proxies_map[cloud_id] = [
                proxy for proxy in proxies if proxy.status == constants.ProcStateType.RUNNING
            ]

        host_id__install_channel_map: Dict[int, Tuple[Optional[models.Host], Dict[str, List]]] = {}
        for host in hosts:
            sub_inst_id = host_id__sub_inst_id[host.bk_host_id]
            install_channel_obj = id__install_channel_obj_map.get(host.install_channel_id)
            if install_channel_obj:
                try:
                    jump_server = random.choice(install_channel_id__jump_servers_map[install_channel_obj.id])
                except IndexError:
                    self.move_insts_to_failed(
                        [sub_inst_id], log_content=_("所选安装通道「{name}」 没有可用跳板机".format(name=install_channel_obj.name))
                    )
                else:
                    host_id__install_channel_map[host.bk_host_id] = (jump_server, install_channel_obj.upstream_servers)
            elif host.bk_cloud_id != constants.DEFAULT_CLOUD and host.node_type != constants.NodeType.PROXY:
                alive_proxies = cloud_id__alive_proxies_map[host.bk_cloud_id]
                try:
                    jump_server = random.choice(alive_proxies)
                except IndexError:
                    self.move_insts_to_failed(
                        [sub_inst_id],
                        log_content=_("云区域 -> {bk_cloud_id} 下无存活的 Proxy").format(bk_cloud_id=host.bk_cloud_id),
                    )
                else:
                    proxy_ips = [alive_proxy.inner_ip for alive_proxy in alive_proxies]
                    upstream_servers = {"taskserver": proxy_ips, "btfileserver": proxy_ips, "dataserver": proxy_ips}
                    host_id__install_channel_map[host.bk_host_id] = (jump_server, upstream_servers)
            else:
                host_ap = host_id__ap_map[host.bk_host_id]
                jump_server = None
                upstream_servers = {
                    "taskserver": host_ap.cluster_endpoint_info.inner_hosts,
                    "btfileserver": host_ap.file_endpoint_info.inner_hosts,
                    "dataserver": host_ap.data_endpoint_info.inner_hosts,
                }
                host_id__install_channel_map[host.bk_host_id] = (jump_server, upstream_servers)

        return host_id__install_channel_map

    def get_host_id__installation_tool_map(
        self, common_data: "AgentCommonData", hosts_need_gen_commands: List[models.Host], is_uninstall: bool
    ) -> Dict[int, InstallationTools]:

        cloud_id__proxies_map = self.get_cloud_id__proxies_map(
            bk_cloud_ids=[host.bk_cloud_id for host in hosts_need_gen_commands]
        )

        host_id__install_channel_map = self.get_host_id__install_channel_map(
            hosts=hosts_need_gen_commands,
            host_id__sub_inst_id=common_data.host_id__sub_inst_id_map,
            host_id__ap_map=common_data.host_id__ap_map,
            cloud_id__proxies_map=cloud_id__proxies_map,
        )

        id__sub_inst_obj_map: Dict[int, models.SubscriptionInstanceRecord] = {
            sub_inst.id: sub_inst for sub_inst in common_data.subscription_instances
        }

        # get_host_id__install_channel_map 仅返回成功匹配安装通道的主机，需要过滤失败主机
        hosts_need_gen_commands = [
            host for host in hosts_need_gen_commands if host.bk_host_id in host_id__install_channel_map
        ]
        host_id__installation_tool_map = batch_gen_commands(
            base_agent_setup_info=common_data.agent_step_adapter.get_setup_info(),
            hosts=hosts_need_gen_commands,
            pipeline_id=self.id,
            is_uninstall=is_uninstall,
            host_id__sub_inst_id=common_data.host_id__sub_inst_id_map,
            ap_id_obj_map=common_data.ap_id_obj_map,
            cloud_id__proxies_map=cloud_id__proxies_map,
            id__sub_inst_obj_map=id__sub_inst_obj_map,
            host_id__install_channel_map=host_id__install_channel_map,
            script_hooks=common_data.subscription_step.params.get("script_hooks"),
        )
        return host_id__installation_tool_map

    @property
    def agent_proc_common_data(self) -> Dict[str, Any]:
        """
        获取 agent ProcessStatus 通用构造数据
        :return:
        """
        return {
            "name": models.ProcessStatus.GSE_AGENT_PROCESS_NAME,
            "source_type": models.ProcessStatus.SourceType.DEFAULT,
        }

    def maintain_agent_proc_status_uniqueness(self, bk_host_ids: Set[int]) -> None:
        """
        维持 Agent 进程的唯一性
        :param bk_host_ids: 主机ID列表
        :return:
        """
        proc_status_infos = models.ProcessStatus.objects.filter(
            **self.agent_proc_common_data, bk_host_id__in=bk_host_ids
        ).values("id", "bk_host_id", "status")

        proc_status_infos_gby_host_id: Dict[int, List[Dict[str, Union[str, int]]]] = defaultdict(list)
        for proc_status_info in proc_status_infos:
            proc_status_infos_gby_host_id[proc_status_info["bk_host_id"]].append(proc_status_info)

        # 对进程按 status 排序，保证 RUNNING 值最小位于列表第一位
        proc_status_infos_gby_host_id = {
            host_id: sorted(proc_status_infos, key=lambda x: (1, -1)[x["status"] == constants.ProcStateType.RUNNING])
            for host_id, proc_status_infos in proc_status_infos_gby_host_id.items()
        }

        # 记录多余的进程ID
        proc_status_ids_to_be_deleted: List[int] = []
        for __, proc_status_infos in proc_status_infos_gby_host_id.items():
            # 按上述的排序规则，保证保留至少一个RUNNING的记录 或 第一个异常记录
            proc_status_ids_to_be_deleted.extend([proc_status_info["id"] for proc_status_info in proc_status_infos[1:]])

        # 删除多余的进程
        models.ProcessStatus.objects.filter(id__in=proc_status_ids_to_be_deleted).delete()

        # 如果没有进程记录则创建
        proc_statuses_to_be_created: List[models.ProcessStatus] = []
        host_ids_without_proc = bk_host_ids - set(proc_status_infos_gby_host_id.keys())
        for host_id in host_ids_without_proc:
            proc_statuses_to_be_created.append(models.ProcessStatus(bk_host_id=host_id, **self.agent_proc_common_data))
        models.ProcessStatus.objects.bulk_create(proc_statuses_to_be_created, batch_size=self.batch_size)


@dataclass
class AgentCommonData(CommonData):
    # 默认接入点
    default_ap: models.AccessPoint
    # 主机ID - 接入点 映射关系
    host_id__ap_map: Dict[int, models.AccessPoint]
    # AgentStep 适配器
    agent_step_adapter: AgentStepAdapter


class RetryHandler:
    """重试处理器"""

    # 重试间隔
    interval: float = None
    # 重试次数
    retry_times: int = None
    # 需要重试的异常类型
    exception_types: List[Type[Exception]] = None

    def __init__(
        self, interval: float = 0, retry_times: int = 1, exception_types: Optional[List[Type[Exception]]] = None
    ):
        self.interval = max(interval, 0)
        self.retry_times = max(retry_times, 0)
        self.exception_types = exception_types or [Exception]

    @wrapt.decorator
    def __call__(self, wrapped: Callable, instance: Optional[object], args: Tuple[Any], kwargs: Dict[str, Any]):
        """
        :param wrapped: 被装饰的函数或类方法
        :param instance:
            - 如果被装饰者为普通类方法，该值为类实例
            - 如果被装饰者为 classmethod / 类方法，该值为类
            - 如果被装饰者为类/函数/静态方法，该值为 None
        :param args: 位置参数
        :param kwargs: 关键字参数
        :return:
        """
        call_times = self.retry_times + 1
        while call_times > 0:
            call_times = call_times - 1
            try:
                return wrapped(*args, **kwargs)
            except Exception as exc_val:
                # 重试次数已用完或者异常捕获未命中时，抛出原异常
                if call_times == 0 or not self.hit_exceptions(exc_val):
                    raise
                # 休眠一段时间
                time.sleep(self.interval)

    def hit_exceptions(self, exc_val: Exception) -> bool:
        for exception in self.exception_types:
            if isinstance(exc_val, exception):
                return True
        return False


# 根据 JOB 的插件额外封装一层，保证后续基于 Agent 增加定制化功能的可扩展性


class AgentExecuteScriptService(job.JobExecuteScriptService, AgentBaseService):
    pass


class AgentTransferFileService(job.JobTransferFileService, AgentBaseService):
    pass


class AgentPushConfigService(job.JobPushConfigService, AgentBaseService):
    pass
