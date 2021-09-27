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
import abc
import json
import logging
import operator
import os
from collections import defaultdict
from functools import reduce
from typing import Dict, List, Set, Tuple, Union

from django.conf import settings
from django.db import IntegrityError
from django.db.models import Q
from django.utils.translation import ugettext as _

from apps.backend.api.constants import (
    GSE_RUNNING_TASK_CODE,
    POLLING_INTERVAL,
    POLLING_TIMEOUT,
    GseDataErrCode,
)
from apps.backend.api.job import process_parms
from apps.backend.components.collections.base import BaseService, CommonData
from apps.backend.components.collections.job import JobV3BaseService
from apps.backend.subscription import errors
from apps.backend.subscription.errors import PackageNotExists
from apps.backend.subscription.steps.adapter import PolicyStepAdapter
from apps.backend.subscription.tools import (
    create_group_id,
    get_all_subscription_steps_context,
    render_config_files_by_config_templates,
)
from apps.exceptions import AppBaseException
from apps.node_man import constants, exceptions, models
from apps.node_man.handlers.cmdb import CmdbHandler
from apps.utils.batch_request import request_multi_thread
from apps.utils.files import PathHandler
from common.api import GseApi, JobApi
from pipeline.component_framework.component import Component
from pipeline.core.flow import Service, StaticIntervalGenerator

logger = logging.getLogger("app")

# 脚本内容缓存，减少重复打开文件读取
SCRIPT_CONTENT_CACHE = {}


class PluginCommonData(CommonData):
    def __init__(
        self,
        bk_host_ids: Set[int],
        process_statuses: List[models.ProcessStatus],
        host_id_obj_map: Dict[int, models.Host],
        target_host_objs: List[models.Host],
        ap_id_obj_map: Dict[int, models.AccessPoint],
        subscription: models.Subscription,
        policy_step_adapter,
        group_id_instance_map: Dict[str, models.SubscriptionInstanceRecord],
        subscription_instances: List[models.SubscriptionInstanceRecord],
        subscription_instance_ids: Set[int],
    ):
        from apps.backend.subscription.steps.adapter import PolicyStepAdapter

        self.bk_host_ids = bk_host_ids
        self.process_statuses = process_statuses
        self.host_id_obj_map = host_id_obj_map
        self.target_host_objs = target_host_objs
        self.ap_id_obj_map = ap_id_obj_map
        self.subscription = subscription
        self.policy_step_adapter: PolicyStepAdapter = policy_step_adapter
        self.group_id_instance_map = group_id_instance_map
        self.plugin_name = policy_step_adapter.plugin_name
        self.subscription_instances = subscription_instances
        self.subscription_instance_ids = subscription_instance_ids
        super().__init__(
            bk_host_ids, host_id_obj_map, ap_id_obj_map, subscription, subscription_instances, subscription_instance_ids
        )


class PluginBaseService(BaseService, metaclass=abc.ABCMeta):
    """
    插件原子基类，提供一些常用的数据获取方法
    """

    @classmethod
    def get_common_data(cls, data):
        """
        初始化常用数据，注意这些数据不能放在 self 属性里，否则会产生较大的 process snap shot，
        另外也尽量不要在 schedule 中使用，否则多次回调可能引起性能问题
        """
        from apps.backend.subscription.steps.adapter import PolicyStepAdapter

        common_data = super().get_common_data(data)
        subscription_instances = common_data.subscription_instances
        # 同一批执行的任务都源于同一个订阅任务
        subscription = common_data.subscription

        subscription_step_id = data.get_one_of_inputs("subscription_step_id")
        try:
            subscription_step = models.SubscriptionStep.objects.get(id=subscription_step_id)
        except models.SubscriptionStep.DoesNotExist:
            raise errors.SubscriptionStepNotExist({"step_id": subscription_step_id})

        bk_host_ids = set()
        subscription_instance_ids = set()
        group_id_instance_map: Dict[str, models.SubscriptionInstanceRecord] = {}
        for subscription_instance in subscription_instances:
            bk_host_ids.add(subscription_instance.instance_info["host"]["bk_host_id"])
            group_id = create_group_id(subscription, subscription_instance.instance_info)
            group_id_instance_map[group_id] = subscription_instance
            subscription_instance_ids.add(subscription_instance.id)

        target_host_objs = None
        if subscription.target_hosts:
            # 目标主机，用于远程采集场景
            query_conditions = reduce(
                operator.or_,
                [
                    Q(inner_ip=target_host["ip"], bk_cloud_id=target_host["bk_cloud_id"])
                    for target_host in subscription.target_hosts
                ],
            )
            target_host_objs = models.Host.objects.filter(query_conditions)
            for host in target_host_objs:
                bk_host_ids.add(host.bk_host_id)

        policy_step_adapter = PolicyStepAdapter(subscription_step)

        process_statuses = models.ProcessStatus.objects.filter(
            name=policy_step_adapter.plugin_name, group_id__in=group_id_instance_map.keys()
        )
        return PluginCommonData(
            common_data.bk_host_ids,
            process_statuses,
            common_data.host_id_obj_map,
            target_host_objs,
            common_data.ap_id_obj_map,
            common_data.subscription,
            policy_step_adapter,
            group_id_instance_map,
            common_data.subscription_instances,
            common_data.subscription_instance_ids,
        )

    @staticmethod
    def get_host_by_process_status(process_status: models.ProcessStatus, common_data: PluginCommonData) -> models.Host:
        """通过进程状态查询得到主机对象"""
        host_id_obj_map = common_data.host_id_obj_map
        bk_host_id = process_status.bk_host_id
        host = host_id_obj_map.get(bk_host_id)
        if not host:
            raise exceptions.HostNotExists()
        return host

    def get_agent_config_by_process_status(
        self, process_status: models.ProcessStatus, common_data: PluginCommonData
    ) -> Dict:
        """通过进程状态查询得到主机的接入点配置"""
        ap_id_obj_map = common_data.ap_id_obj_map
        host = self.get_host_by_process_status(process_status, common_data)
        ap = ap_id_obj_map.get(host.ap_id)
        if not ap:
            raise exceptions.ApIDNotExistsError()
        agent_config = ap.agent_config.get(host.os_type.lower()) or ap.agent_config["linux"]
        return agent_config

    def get_package_by_process_status(
        self, process_status: models.ProcessStatus, common_data: PluginCommonData
    ) -> models.Packages:
        """通过进程状态得到插件包对象"""
        host = self.get_host_by_process_status(process_status, common_data)
        policy_step_adapter = common_data.policy_step_adapter
        package = policy_step_adapter.get_matching_package_obj(host.os_type, host.cpu_arch)
        return package

    def get_plugin_root_by_process_status(
        self, process_status: models.ProcessStatus, common_data: PluginCommonData
    ) -> str:
        """
        通过进程状态得到插件根路径，目前分为两类，
        1. 官方插件通常为 /usr/local/gse/plugins/
        2. 第三方插件通常为 /usr/local/gse_bkte/external_plugins/${group_id}/${plugin_name}
        """
        host = self.get_host_by_process_status(process_status, common_data)
        policy_step_adapter = common_data.policy_step_adapter
        path_handler = PathHandler(host.os_type)
        plugin_root_mapping = {
            constants.CategoryType.official: path_handler.dirname(process_status.setup_path),
            constants.CategoryType.external: process_status.setup_path,
        }
        return plugin_root_mapping[policy_step_adapter.plugin_desc.category]


class InitProcessStatusService(PluginBaseService):
    """初始化进程状态，持久化记录并用于后续流程使用"""

    def _execute(self, data, parent_data, common_data: PluginCommonData):
        action = data.get_one_of_inputs("action")
        bk_host_ids = common_data.bk_host_ids
        subscription = common_data.subscription
        subscription_instances = common_data.subscription_instances
        host_id_obj_map = common_data.host_id_obj_map
        ap_id_obj_map = common_data.ap_id_obj_map

        source_type = self.get_source_type_by_subscription(subscription)
        source_id = subscription.id

        to_be_created_process_status = []
        to_be_updated_process_status = []

        # 提前查询拓扑顺序，用于策略抑制计算，得到当期策略所属层级
        topo_order = CmdbHandler.get_topo_order()
        # 此处steps的长度通常为1或2，此处不必担心时间复杂度问题
        for subscription_step in subscription.steps:
            policy_step_adapter = PolicyStepAdapter(subscription_step)
            plugin_name = policy_step_adapter.plugin_name

            statuses = models.ProcessStatus.objects.filter(
                source_type=source_type,
                source_id=source_id,
                name=plugin_name,
                bk_host_id__in=bk_host_ids,
            )
            group_id_status_map = {status.group_id: status for status in statuses}
            host_id__bk_obj_sub_map = models.Subscription.get_host_id__bk_obj_sub_map(bk_host_ids, plugin_name)

            for subscription_instance in subscription_instances:
                # 策略抑制计算
                result = subscription.check_is_suppressed(
                    action=action,
                    cmdb_host_info=subscription_instance.instance_info["host"],
                    topo_order=topo_order,
                    host_id__bk_obj_sub_map=host_id__bk_obj_sub_map,
                )
                bk_obj_id = result["sub_inst_bk_obj_id"]

                target_host_objs = self.get_target_host_objs(
                    subscription_instance,
                    host_id_obj_map,
                    common_data.target_host_objs,
                )
                # target_host_objs 的长度通常为1或2，此处也不必担心时间复杂度问题
                # 指定 target_host 主要用于远程采集的场景，常见于第三方插件，如拨测
                for host in target_host_objs:
                    bk_host_id = host.bk_host_id
                    os_type = host.os_type.lower()
                    cpu_arch = host.cpu_arch
                    group_id = create_group_id(subscription, subscription_instance.instance_info)
                    package = self.get_package(subscription_instance, policy_step_adapter, os_type, cpu_arch)
                    ap_config = self.get_ap_config(ap_id_obj_map, host)
                    setup_path, pid_path, log_path, data_path = self.get_plugins_paths(
                        package, plugin_name, ap_config, group_id, subscription
                    )
                    process_status_property = dict(
                        bk_host_id=bk_host_id,
                        name=plugin_name,
                        source_id=source_id,
                        source_type=source_type,
                        group_id=group_id,
                        proc_type=constants.ProcType.PLUGIN,
                        bk_obj_id=bk_obj_id,
                        setup_path=setup_path,
                        log_path=log_path,
                        data_path=data_path,
                        pid_path=pid_path,
                        version=getattr(package, "version", ""),
                    )
                    self.append_process_status(
                        group_id,
                        group_id_status_map,
                        process_status_property,
                        to_be_updated_process_status,
                        to_be_created_process_status,
                    )

        # 批量创建或更新进程状态表，受限于部分MySQL配置的原因，这里 BATCH_SIZE 支持可配置，默认为100
        batch_size = models.GlobalSettings.get_config("BATCH_SIZE", default=100)
        models.ProcessStatus.objects.bulk_create(to_be_created_process_status, batch_size=batch_size)
        models.ProcessStatus.objects.bulk_update(
            to_be_updated_process_status,
            fields=["setup_path", "log_path", "data_path", "pid_path", "version"],
            batch_size=batch_size,
        )

    def inputs_format(self):
        return self.inputs_format() + [
            Service.InputItem(name="action", key="action", type="str", required=True),
        ]

    def get_package(
        self,
        subscription_instance: models.SubscriptionInstanceRecord,
        policy_step_adapter: PolicyStepAdapter,
        os_type: str,
        cpu_arch: str,
    ) -> models.Packages:
        """获取插件包对象"""
        try:
            return policy_step_adapter.get_matching_package_obj(os_type, cpu_arch)
        except PackageNotExists as error:
            # 插件包不支持或不存在时，记录异常信息，此实例不参与后续流程
            self.move_insts_to_failed([subscription_instance.id], str(error))

    @staticmethod
    def get_source_type_by_subscription(subscription: models.Subscription) -> str:
        """根据订阅转化进程状态类型"""
        if subscription.is_main:
            source_type = models.ProcessStatus.SourceType.DEFAULT
        else:
            source_type = models.ProcessStatus.SourceType.SUBSCRIPTION
        return source_type

    def get_target_host_objs(
        self,
        subscription_instance: models.SubscriptionInstanceRecord,
        host_id_obj_map: Dict[int, models.Host],
        target_host_objs: List[models.Host] = None,
    ) -> List[models.Host]:
        """
        计算需要执行的目标主机
        一般远程采集时会指定目标主机 target_host_objs，如拨测场景
        当未指定 target_host_objs，则是普通下发下发场景，取当前实例的主机即可
        """
        if target_host_objs:
            return target_host_objs
        bk_host_id = subscription_instance.instance_info["host"]["bk_host_id"]
        host = host_id_obj_map.get(bk_host_id)
        if not host:
            self.move_insts_to_failed([subscription_instance.id], _("主机不存在或未同步"))
            return []
        return [host]

    @staticmethod
    def get_ap_config(ap_id_obj_map: Dict[int, models.AccessPoint], host: models.Host):
        """获取接入点配置"""
        ap = ap_id_obj_map.get(host.ap_id)
        os_type = host.os_type.lower()
        ap_config = ap.agent_config.get(os_type)
        if not ap_config:
            raise exceptions.ApNotSupportOsError(ap_id=ap.id, os_type=os_type)
        return ap_config

    @staticmethod
    def append_process_status(
        group_id: str,
        group_id_status_map: Dict[str, models.ProcessStatus],
        process_status_property: Dict,
        to_be_updated_process_status: List[models.ProcessStatus],
        to_be_created_process_status: List[models.ProcessStatus],
    ):
        """添加进程状态，对于不存在的进行新增，对于已存在的进行更新，此处处理后再由后续统一进行 bulk 批量操作"""
        if group_id in group_id_status_map:
            to_be_updated_process_status.append(
                models.ProcessStatus(id=group_id_status_map[group_id].id, **process_status_property)
            )
        else:
            to_be_created_process_status.append(models.ProcessStatus(**process_status_property))

    @staticmethod
    def get_plugins_paths(
        package: models.Packages, plugin_name: str, ap_config: Dict, group_id: str, subscription: models.Subscription
    ) -> Tuple[str, str, str, str]:
        """获取插件相关路径 (setup_path, pid_path, log_path, data_path)"""
        if not package:
            return "", "", "", ""
        # 配置插件进程实际运行路径配置信息
        path_handler = PathHandler(package.os)
        pid_filename = f"{plugin_name}.pid"
        if package.plugin_desc.category == constants.CategoryType.external:
            # 如果为 external 第三方插件，需要补上插件组目录
            setup_path = path_handler.join(
                ap_config["setup_path"], constants.PluginChildDir.EXTERNAL.value, group_id, package.project
            )

            if subscription.category == subscription.CategoryType.DEBUG:
                # debug模式下特殊处理这些路径
                pid_path = path_handler.join(setup_path, "pid", "%s.pid" % package.project)
                log_path = path_handler.join(setup_path, "log")
                data_path = path_handler.join(setup_path, "data")
            else:
                pid_path = path_handler.join(ap_config["run_path"], group_id, pid_filename)
                log_path = path_handler.join(ap_config["log_path"], group_id)
                data_path = path_handler.join(ap_config["data_path"], group_id)
        else:
            setup_path = path_handler.join(ap_config["setup_path"], constants.PluginChildDir.OFFICIAL.value, "bin")
            pid_path = path_handler.join(ap_config["run_path"], pid_filename)
            log_path = ap_config["log_path"]
            data_path = ap_config["data_path"]

        # Windows 插件的setup_path 需调整为左斜杠 /
        setup_path = setup_path.replace("\\", "/")
        return setup_path, pid_path, log_path, data_path


class UpdateHostProcessStatusService(PluginBaseService):
    """
    更新主机进程状态
    """

    def _execute(self, data, parent_data, common_data: PluginCommonData):
        status = data.get_one_of_inputs("status")
        plugin_name = common_data.plugin_name
        subscription = common_data.subscription
        process_statuses = common_data.process_statuses
        bk_host_ids = common_data.bk_host_ids

        to_be_deleted_process_status_ids = []
        to_be_updated_process_status_ids = []
        for process_status in process_statuses:
            if status == constants.ProcStateType.REMOVED:
                to_be_deleted_process_status_ids.append(process_status.id)
            else:
                to_be_updated_process_status_ids.append(process_status.id)

        if status in [
            constants.ProcStateType.RUNNING,
            constants.ProcStateType.TERMINATED,
            constants.ProcStateType.REMOVED,
            constants.ProcStateType.MANUAL_STOP,
        ]:
            # 先将所有相关记录更新为非最新，并将记录更新为is_latest=True
            update_fields = {"status": status}
            if subscription.is_main:
                # 主程序部署，需要把这批主机的插件都更新为非最新
                models.ProcessStatus.objects.filter(bk_host_id__in=bk_host_ids, name=plugin_name).update(
                    is_latest=False
                )
                update_fields["is_latest"] = True
            models.ProcessStatus.objects.filter(id__in=to_be_updated_process_status_ids).update(**update_fields)
        else:
            models.ProcessStatus.objects.filter(id__in=to_be_updated_process_status_ids).update(status=status)

        models.ProcessStatus.objects.filter(id__in=to_be_deleted_process_status_ids).delete()

    def inputs_format(self):
        return self.inputs_format() + [
            Service.InputItem(name="status", key="status", type="str", required=True),
        ]


class CheckAgentStatusService(PluginBaseService):
    """查询AGENT状态是否正常"""

    def _execute(self, data, parent_data, common_data: PluginCommonData):
        process_statuses = common_data.process_statuses
        group_id_instance_map = common_data.group_id_instance_map
        target_host_objs = common_data.target_host_objs
        if target_host_objs:
            # 远程采集时，只需要查询目标机器AGENT状态即可
            bk_host_ids = [host.bk_host_id for host in target_host_objs]
        else:
            bk_host_ids = common_data.bk_host_ids

        # 查询机器的AGENT状态
        host_id_agent_status_map = models.ProcessStatus.hosts_agent_status_map(bk_host_ids)
        for process_status in process_statuses:
            bk_host_id = process_status.bk_host_id
            subscription_instance = group_id_instance_map.get(process_status.group_id)
            status = host_id_agent_status_map.get(bk_host_id)
            if status != constants.ProcStateType.RUNNING:
                self.move_insts_to_failed(
                    [subscription_instance.id],
                    _("{bk_host_id}:AGENT异常[{status}]，请尝试恢复AGENT状态或重装AGENT。").format(
                        bk_host_id=bk_host_id, status=status
                    ),
                )
        return True


class TransferPackageService(JobV3BaseService, PluginBaseService):
    """调用作业平台传输插件包"""

    def _execute(self, data, parent_data, common_data: PluginCommonData):
        process_statuses = common_data.process_statuses
        group_id_instance_map = common_data.group_id_instance_map
        host_id_obj_map = common_data.host_id_obj_map

        # 按插件包和操作系统进行分组分发文件
        # 如 linux-arm、linux-x86、windows-x86 的插件，需分为三组
        # 把多个IP合并为一个任务，可以利用GSE文件管道的BT能力，提高传输效率
        jobs: Dict[str, Dict[str, Union[list, str]]] = defaultdict(lambda: defaultdict(list))
        nginx_path = settings.DOWNLOAD_PATH
        for process_status in process_statuses:
            bk_host_id = process_status.bk_host_id
            subscription_instance = group_id_instance_map.get(process_status.group_id)
            host = host_id_obj_map.get(bk_host_id)
            package = self.get_package_by_process_status(process_status, common_data)
            agent_config = self.get_agent_config_by_process_status(process_status, common_data)
            os_type = host.os_type.lower() or constants.OsType.LINUX.lower()
            package_path = "/".join((nginx_path, os_type, host.cpu_arch, package.pkg_name))
            jobs[package_path]["ip_list"].append({"bk_cloud_id": host.bk_cloud_id, "ip": host.inner_ip})
            jobs[package_path]["subscription_instance_ids"].append(subscription_instance.id)
            jobs[package_path]["temp_path"] = agent_config["temp_path"]
            jobs[package_path]["os_type"] = host.os_type

        # 组装作业平台请求参数
        multi_job_params = []
        for package_path, job in jobs.items():
            file_list = [package_path]
            file_list = self.append_extra_files(job["os_type"], file_list, nginx_path)

            multi_job_params.append(
                {
                    "job_func": JobApi.fast_transfer_file,
                    "subscription_instance_id": job["subscription_instance_ids"],
                    "subscription_id": common_data.subscription.id,
                    "job_params": {
                        "file_target_path": job["temp_path"],
                        "file_source_list": [{"file_list": file_list}],
                        "os_type": job["os_type"],
                        "target_server": {"ip_list": job["ip_list"]},
                    },
                }
            )
        # 对上面组装好的作业平台参数进行并发请求
        request_multi_thread(self.request_single_job_and_create_map, multi_job_params)
        return True

    @staticmethod
    def append_extra_files(os_type: str, file_list: List[str], nginx_path: str) -> List[str]:
        """
        根据不同的操作系统，添加一些额外的文件或执行脚本，避免脚本老旧有bug或者不存在的情况
        """
        if os_type == constants.OsType.WINDOWS:
            script_files = ["start.bat", "stop.bat", "restart.bat"]
            for unzip_file in ["7z.dll", "7z.exe"]:
                # Windows 添加 7z 用于解压
                file_list.append(os.path.sep.join([nginx_path, unzip_file]))
        elif os_type == constants.OsType.AIX:
            script_files = ["start.ksh", "stop.ksh", "restart.ksh", "reload.ksh"]
        else:
            script_files = ["start.sh", "stop.sh", "restart.sh", "reload.sh"]

        for script_file in script_files:
            file_list.append(os.path.sep.join([nginx_path, "plugin_scripts", script_file]))
        return file_list


class PluginExecuteScriptService(PluginBaseService, JobV3BaseService, metaclass=abc.ABCMeta):
    """
    插件快速执行脚本父类，用于插件操作过程中通用的脚本执行
    """

    @property
    def script_name(self):
        """
        插件需要执行的脚本文件名称，由子类继承定义
        """
        raise NotImplementedError

    def generate_script_params_by_process_status(
        self, process_status: models.ProcessStatus, common_data: PluginCommonData
    ) -> str:
        """
        生成脚本所需的参数，默认脚本无需参数，由子类继承编写参数生成逻辑
        """
        return ""

    def need_skipped(self, process_status: models.ProcessStatus, common_data: PluginCommonData) -> bool:
        """
        判断是否需要跳过，由子类继承并编写跳过规则，默认不跳过
        """
        return False

    def _execute(self, data, parent_data, common_data: PluginCommonData):
        process_statuses = common_data.process_statuses
        timeout = data.get_one_of_inputs("timeout")
        group_id_instance_map = common_data.group_id_instance_map

        # 批量请求作业平台的参数
        multi_job_params_map = {}
        for process_status in process_statuses:
            if self.need_skipped(process_status, common_data):
                continue

            subscription_instance = group_id_instance_map.get(process_status.group_id)
            try:
                host = self.get_host_by_process_status(process_status, common_data)
                script_param = self.generate_script_params_by_process_status(process_status, common_data)
            except AppBaseException as err:
                self.move_insts_to_failed([subscription_instance.id], err.message)
                continue

            script_content = self.get_script_content(host.os_type)

            # script_content 和 script_param md5一样的则认为是同样的脚本操作，合并到一个作业中，提高执行效率
            script_content_md5 = self.get_md5(script_content)
            script_param_md5 = self.get_md5(script_param)
            key = f"{script_content_md5}-{script_param_md5}"
            subscription_instance_id = group_id_instance_map.get(process_status.group_id).id
            if key in multi_job_params_map:
                multi_job_params_map[key]["subscription_instance_id"].append(subscription_instance_id)
                multi_job_params_map[key]["job_params"]["target_server"]["ip_list"].append(
                    {"bk_cloud_id": host.bk_cloud_id, "ip": host.inner_ip}
                )
            else:
                multi_job_params_map[key] = {
                    "job_func": JobApi.fast_execute_script,
                    "subscription_instance_id": [subscription_instance_id],
                    "subscription_id": common_data.subscription.id,
                    "job_params": {
                        "target_server": {"ip_list": [{"bk_cloud_id": host.bk_cloud_id, "ip": host.inner_ip}]},
                        "script_content": script_content,
                        "script_param": script_param,
                        "timeout": timeout,
                        "os_type": host.os_type,
                    },
                }
        self.run_job_or_finish_schedule(multi_job_params_map)
        return True

    def get_script_content(self, os_type: str) -> str:
        """
        读取脚本内容缓存，避免重复打开文件
        :param os_type: 操作系统类型
        :return: 脚本文件内容
        """
        # 读取脚本内容缓存，避免重复打开文件
        os_script_name_map = {
            constants.OsType.WINDOWS: f"{self.script_name}.bat",
            constants.OsType.LINUX: f"{self.script_name}.sh",
            constants.OsType.AIX: f"{self.script_name}.ksh",
        }
        file_name = os_script_name_map.get(os_type, f"{self.script_name}.sh")
        if file_name not in SCRIPT_CONTENT_CACHE:
            path = os.path.join(settings.PROJECT_ROOT, "script_tools", "plugin_scripts", file_name)
            with open(path, encoding="utf-8") as fh:
                SCRIPT_CONTENT_CACHE[file_name] = fh.read()
        return SCRIPT_CONTENT_CACHE[file_name]

    def run_job_or_finish_schedule(self, multi_job_params_map: Dict):
        """如果作业平台参数为空，代表无需执行，直接finish_schedule去执行下一个原子"""
        if multi_job_params_map:
            request_multi_thread(self.request_single_job_and_create_map, multi_job_params_map.values())
        else:
            self.finish_schedule()


class InstallPackageService(PluginExecuteScriptService):
    """调用作业平台安装插件包"""

    @property
    def script_name(self):
        return "update_binary"

    def generate_script_params_by_process_status(
        self, process_status: models.ProcessStatus, common_data: PluginCommonData
    ) -> str:
        agent_config = self.get_agent_config_by_process_status(process_status, common_data)
        package = self.get_package_by_process_status(process_status, common_data)

        policy_step_adapter = common_data.policy_step_adapter
        category = policy_step_adapter.plugin_desc.category
        script_param = "-t {category} -p {setup_path} -n {name} -f {package} -m {upgrade_type} -z {tmp_dir}".format(
            category=category,
            setup_path=agent_config["setup_path"],
            name=package.project,
            package=package.pkg_name,
            upgrade_type="OVERRIDE",
            tmp_dir=agent_config["temp_path"],
        )
        group_id = process_status.group_id
        if category == constants.CategoryType.external and group_id:
            # 设置插件实例目录
            script_param += " -i %s" % group_id
        return script_param


class UnInstallPackageService(PluginExecuteScriptService):
    """
    调用作业平台卸载安装包
    """

    @property
    def script_name(self):
        return "update_binary"

    def generate_script_params_by_process_status(self, process_status, common_data) -> str:
        agent_config = self.get_agent_config_by_process_status(process_status, common_data)
        package = self.get_package_by_process_status(process_status, common_data)

        policy_step_adapter = common_data.policy_step_adapter
        category = policy_step_adapter.plugin_desc.category
        script_param = "-t {category} -p {gse_home} -z {tmp_dir} -n {name} -r".format(
            category=category,
            gse_home=agent_config["setup_path"],
            name=package.project,
            tmp_dir=agent_config["temp_path"],
        )
        group_id = process_status.group_id
        if category == constants.CategoryType.external and group_id:
            # 设置插件实例目录
            script_param += " -i %s" % group_id

        return script_param


class RemoveConfigService(PluginExecuteScriptService):
    """调用作业平台移除配置"""

    @property
    def script_name(self):
        return "remove_config"

    def generate_script_params_by_process_status(
        self, process_status: models.ProcessStatus, common_data: PluginCommonData
    ) -> str:
        host = self.get_host_by_process_status(process_status, common_data)
        # 配置插件进程实际运行路径配置信息
        path_handler = PathHandler(host.os_type)
        plugin_root = self.get_plugin_root_by_process_status(process_status, common_data)

        config_path_list = [
            path_handler.join(plugin_root, config["file_path"], config["name"]) for config in process_status.configs
        ]
        # 兼容部分Windows版本路径不适配的问题
        if host.os_type == constants.OsType.WINDOWS:
            for index, config_path in enumerate(config_path_list):
                config_path_list[index] = config_path.replace("/", "\\")

        script_param = " ".join(config_path_list)
        return script_param


class JobAllocatePortService(PluginExecuteScriptService):
    """调用作业平台查询占用端口并分配"""

    @property
    def script_name(self):
        return "fetch_used_ports"

    def need_skipped(self, process_status: models.ProcessStatus, common_data: PluginCommonData) -> bool:
        """
        当满足以下条件之一时，无需重复执行分配端口号逻辑，直接跳过即可
        1. 该进程已分配端口号
        2. 该插件无需监听端口
        """
        package = self.get_package_by_process_status(process_status, common_data)
        plugin_control = package.proc_control
        if process_status.listen_port or not plugin_control.listen_port_required:
            return True
        return False

    @staticmethod
    def parse_used_port(log_content: str) -> Set[int]:
        """
        解析脚本返回日志中已使用的端口，log_content 格式如：
        127.0.0.1:53
        127.0.0.1:8080
        127.0.0.1:8090
        """
        used_ports = set()
        for line in log_content.splitlines():
            try:
                if ":" in line:
                    port_num = int(line.split(":")[-1])
                else:
                    # AIX使用 "." 来分隔端口
                    port_num = int(line.split(".")[-1])
            except (ValueError, AttributeError):
                continue
            else:
                used_ports.add(port_num)
        return used_ports

    def allocate_port_to_process_status(
        self,
        process_status: models.ProcessStatus,
        host: models.Host,
        plugin_control: models.ProcControl,
        subscription_instance: models.SubscriptionInstanceRecord,
        job_instance_id: int,
        step_instance_id: int,
    ):
        """根据job返回日志分配端口"""
        bk_host_id = process_status.bk_host_id

        # 查询并解析该主机已被占用的端口号
        result = JobApi.get_job_instance_ip_log(
            {
                "bk_biz_id": settings.BLUEKING_BIZ_ID,
                "job_instance_id": job_instance_id,
                "step_instance_id": step_instance_id,
                "bk_cloud_id": host.bk_cloud_id,
                "ip": host.inner_ip,
            }
        )
        used_ports = self.parse_used_port(result.get("log_content", ""))
        port_range_list = models.ProcControl.parse_port_range(plugin_control.port_range)
        queryset = models.ProcessStatus.objects.filter(bk_host_id=bk_host_id)
        # 当前主机已经注册的端口号集合
        registered_ports = {port for port in queryset.values_list("listen_port", flat=True) if port}
        registered_ports.update(used_ports)
        listen_ip = "127.0.0.1"
        process_status.listen_ip = listen_ip
        # 在给定范围内检索可用的端口号， 如 port_range 为 "8080,10000-65535"
        # 则优先判断8080端口是否被占用，若被占用，则尝试检查10000端口，以此类推
        for port_min, port_max in port_range_list:
            for port in range(port_min, port_max + 1):
                if port not in registered_ports:
                    # 检索完成，尝试保存退出
                    process_status.listen_port = port
                    try:
                        process_status.save()
                    except IntegrityError:
                        # 不满足完整性校验，如并发场景，其它进程已占用了端口，端口冲突，需要继续检查
                        continue
                    return True
        self.move_insts_to_failed(
            [subscription_instance.id], _("主机[{}]在ip->[{}]上无可用端口").format(host.inner_ip, listen_ip)
        )

    def get_job_instance_status(self, job_sub_map: models.JobSubscriptionInstanceMap, common_data: PluginCommonData):
        """查询作业平台执行状态"""
        bk_host_ids = common_data.bk_host_ids
        process_statuses = common_data.process_statuses
        group_id_instance_map = common_data.group_id_instance_map
        host_id_obj_map: Dict[int, models.Host] = models.Host.host_id_obj_map(bk_host_id__in=bk_host_ids)

        result = JobApi.get_job_instance_status(
            {
                "bk_biz_id": settings.BLUEKING_BIZ_ID,
                "job_instance_id": job_sub_map.job_instance_id,
                "return_ip_result": True,
            }
        )
        step_instance_id = result["step_instance_list"][0]["step_instance_id"]
        job_status = result["job_instance"]["status"]

        if job_status in (constants.BkJobStatus.PENDING, constants.BkJobStatus.RUNNING):
            # 任务未完成，直接跳过，等待下次查询
            return

        # 其它 job_status 则认为任务已结束，进一步查询IP的 JOB 日志，并进行端口分配
        multi_allocate_params = []
        for process_status in process_statuses:

            bk_host_id = process_status.bk_host_id
            host = host_id_obj_map.get(bk_host_id)
            subscription_instance = group_id_instance_map.get(process_status.group_id)
            package = self.get_package_by_process_status(process_status, common_data)

            multi_allocate_params.append(
                {
                    "process_status": process_status,
                    "host": host,
                    "plugin_control": package.proc_control,
                    "subscription_instance": subscription_instance,
                    "job_instance_id": job_sub_map.job_instance_id,
                    "step_instance_id": step_instance_id,
                }
            )
        request_multi_thread(self.allocate_port_to_process_status, multi_allocate_params)
        job_sub_map.status = job_status
        job_sub_map.save()

    def _schedule(self, data, parent_data, callback_data=None):
        # 查询未完成的作业, 批量查询作业状态并更新DB
        multi_params = [
            {"job_sub_map": job_sub_map, "common_data": self.get_common_data(data)}
            for job_sub_map in models.JobSubscriptionInstanceMap.objects.filter(
                node_id=self.id, status=constants.BkJobStatus.PENDING
            )
        ]
        request_multi_thread(self.get_job_instance_status, multi_params)

        # 判断 JobSubscriptionInstanceMap 中对应的 job_instance_id 都执行完成的，把成功的 subscription_instance_ids 向下传递
        if not models.JobSubscriptionInstanceMap.objects.filter(
            node_id=self.id, status=constants.BkJobStatus.PENDING
        ).exists():
            self.finish_schedule()


class RenderAndPushConfigService(PluginBaseService, JobV3BaseService):
    """
    渲染配置文件并调用作业平台进行下发
    """

    def _execute(self, data, parent_data, common_data: PluginCommonData):
        subscription_step_id = data.get_one_of_inputs("subscription_step_id")
        process_statuses = common_data.process_statuses
        policy_step_adapter = common_data.policy_step_adapter
        group_id_instance_map = common_data.group_id_instance_map
        host_id_obj_map = common_data.host_id_obj_map

        # 此处 subscription_step 一定有值，否则前置流程已出现异常
        subscription_step = models.SubscriptionStep.objects.get(id=subscription_step_id)

        # 组装调用作业平台的参数
        multi_job_params_map = {}
        for process_status in process_statuses:
            target_bk_host_id = process_status.bk_host_id
            subscription_instance = group_id_instance_map.get(process_status.group_id)
            target_host = host_id_obj_map.get(target_bk_host_id)
            package = self.get_package_by_process_status(process_status, common_data)
            agent_config = self.get_agent_config_by_process_status(process_status, common_data)
            # 获取订阅的上下文变量
            context = get_all_subscription_steps_context(
                subscription_step, subscription_instance.instance_info, target_host, process_status.name, agent_config
            )

            # 根据配置模板和上下文变量渲染配置文件
            rendered_configs = render_config_files_by_config_templates(
                policy_step_adapter.get_matching_config_tmpl_objs(target_host.os_type, target_host.cpu_arch),
                process_status,
                context,
                package_obj=package,
            )
            process_status.configs = rendered_configs
            process_status.save()

            path_handler = PathHandler(target_host.os_type)
            plugin_root = self.get_plugin_root_by_process_status(process_status, common_data)
            for config in rendered_configs:
                file_target_path = path_handler.join(plugin_root, config["file_path"])
                file_name = config["name"]
                file_content = config["content"]
                file_md5 = self.get_md5(file_content)
                key = f"{file_target_path}-{file_name}-{file_md5}"
                # 路径、文件名、文件内容一致，则认为是同一个文件，合并到一个作业中，提高执行效率
                if key in multi_job_params_map:
                    multi_job_params_map[key]["subscription_instance_id"].append(subscription_instance.id)
                    multi_job_params_map[key]["job_params"]["target_server"]["ip_list"].append(
                        {"bk_cloud_id": target_host.bk_cloud_id, "ip": target_host.inner_ip}
                    )
                else:
                    multi_job_params_map[key] = {
                        "job_func": JobApi.push_config_file,
                        "subscription_instance_id": [subscription_instance.id],
                        "subscription_id": common_data.subscription.id,
                        "job_params": {
                            "os_type": target_host.os_type,
                            "target_server": {
                                "ip_list": [{"bk_cloud_id": target_host.bk_cloud_id, "ip": target_host.inner_ip}]
                            },
                            "file_target_path": file_target_path,
                            "file_list": [{"file_name": file_name, "content": process_parms(file_content)}],
                        },
                    }

        if not multi_job_params_map:
            subscription_instance_ids = common_data.subscription_instance_ids
            self.log_info(
                sub_inst_ids=subscription_instance_ids,
                log_content=_(
                    "无需渲染配置，直接进入下一步骤，subscription_instance_ids -> {subscription_instance_ids}".format(
                        subscription_instance_ids=subscription_instance_ids
                    )
                ),
            )
            self.finish_schedule()
            return True

        request_multi_thread(self.request_single_job_and_create_map, multi_job_params_map.values())
        return True


class GseOperateProcService(PluginBaseService):
    """调用GSE接口操作插件进程"""

    __need_schedule__ = True
    interval = StaticIntervalGenerator(POLLING_INTERVAL)

    @staticmethod
    def get_plugin_meta_name(plugin: models.GsePluginDesc, process_status: models.ProcessStatus) -> str:
        """
        获取插件的元数据名称，这个值将结合 namespace 作为 GSE 托管插件的唯一表示
        第三方插件由于在一台机器上可以存在多个，因此需加上 group_id 加以区分
        :param plugin: 插件对象
        :param process_status: 进程状态对象
        :return: 插件元数据名称
        """
        if plugin.category == constants.CategoryType.external and process_status.group_id:
            proc_name = f"{process_status.group_id}_{plugin.name}"
        else:
            proc_name = plugin.name
        return proc_name

    @staticmethod
    def get_gse_control(
        os_type: str, package_control: models.ProcControl, process_status: models.ProcessStatus
    ) -> Dict:
        """
        获取GSE控制命令，windows机器需要补全路径
        :param os_type: 操作系统类型
        :param package_control: 插件包进程控制对象
        :param process_status: 进程状态对象
        :return: GSE控制命令
        """

        gse_control = {
            "start_cmd": package_control.start_cmd,
            "stop_cmd": package_control.stop_cmd,
            "restart_cmd": package_control.restart_cmd,
            "reload_cmd": package_control.reload_cmd or package_control.restart_cmd,
            "kill_cmd": package_control.kill_cmd,
            "version_cmd": package_control.version_cmd,
            "health_cmd": package_control.health_cmd,
        }
        # 操作系统为Windows的，需要补充完整路径，如 C:/gse/plugins/bin/start.bat basereport
        if os_type == constants.OsType.WINDOWS:
            gse_control = {
                "start_cmd": f"{process_status.setup_path}/{package_control.start_cmd}",
                "stop_cmd": f"{process_status.setup_path}/{package_control.stop_cmd}",
                "restart_cmd": f"{process_status.setup_path}/{package_control.restart_cmd}",
                "reload_cmd": f"{process_status.setup_path}/{package_control.reload_cmd}"
                or f"{process_status.setup_path}/{package_control.restart_cmd}",
                "kill_cmd": f"{process_status.setup_path}/{package_control.kill_cmd}",
                "version_cmd": f"{process_status.setup_path}/{package_control.version_cmd}",
                "health_cmd": f"{process_status.setup_path}/{package_control.health_cmd}",
            }
        return gse_control

    def request_gse_or_finish_schedule(self, proc_operate_req: List, data):
        """批量请求GSE接口"""
        # 当请求参数为空时，代表无需请求，直接 finish_schedule 跳过即可
        if proc_operate_req:
            task_id = GseApi.operate_proc_multi({"proc_operate_req": proc_operate_req})["task_id"]
            self.log_info(log_content=f"GSE TASK ID: [{task_id}]")
            data.outputs.task_id = task_id
        else:
            self.finish_schedule()

    def _execute(self, data, parent_data, common_data: PluginCommonData):
        op_type = data.get_one_of_inputs("op_type")
        policy_step_adapter = common_data.policy_step_adapter
        process_statuses = common_data.process_statuses
        plugin = policy_step_adapter.plugin_desc
        group_id_instance_map = common_data.group_id_instance_map
        host_id_obj_map = common_data.host_id_obj_map

        proc_operate_req = []
        for process_status in process_statuses:
            bk_host_id = process_status.bk_host_id
            host = host_id_obj_map.get(bk_host_id)
            subscription_instance = group_id_instance_map.get(process_status.group_id)
            package = self.get_package_by_process_status(process_status, common_data)
            package_control = package.proc_control

            if not package_control.need_delegate:
                continue

            meta_name = self.get_plugin_meta_name(plugin, process_status)
            gse_control = self.get_gse_control(host.os_type, package_control, process_status)

            gse_op_params = {
                "meta": {"namespace": constants.GSE_NAMESPACE, "name": meta_name},
                "op_type": op_type,
                "hosts": [{"ip": host.inner_ip, "bk_cloud_id": host.bk_cloud_id}],
                # 此字段是节点管理自用，仅用于标识，不会被GSE使用
                "nodeman_spec": {
                    "process_status_id": process_status.id,
                    "subscription_instance_id": subscription_instance.id,
                },
                "spec": {
                    "identity": {
                        "index_key": "",
                        # 注意这里的 proc_name 是进程名，比如 java
                        "proc_name": package_control.process_name or plugin.name,
                        "setup_path": process_status.setup_path,
                        "pid_path": process_status.pid_path,
                        "user": constants.ACCOUNT_MAP.get(host.os_type, "root"),
                    },
                    "control": gse_control,
                    "resource": {
                        "mem": 10,
                        # 日志采集器需要更高的CPU，TODO 后续通过资源配额来解决
                        "cpu": 30 if plugin.name == "bkunifylogbeat" else 10,
                    },
                    "alive_monitor_policy": {
                        # 托管类型，0为周期执行进程，1为常驻进程，2为单次执行进程，这里仅需使用常驻进程
                        "auto_type": 1,
                        "start_check_secs": 9,
                    },
                },
            }
            self.log_info(subscription_instance.id, json.dumps(gse_op_params, indent=2))
            proc_operate_req.append(gse_op_params)

        self.request_gse_or_finish_schedule(proc_operate_req, data)
        data.outputs.polling_time = 0
        return True

    def handle_error_code(
        self,
        error_code: int,
        error_msg: str,
        op_type: str,
        polling_time: int,
        subscription_instance: models.SubscriptionInstanceRecord,
        is_finished: bool,
    ) -> bool:
        """
        处理GSE返回的错误码，针对部分操作类型，
        :param error_code: GSE接口返回的错误码
        :param error_msg: GSE接口返回的错误信息
        :param op_type: 操作类型
        :param polling_time:
        :param subscription_instance:
        :param is_finished:
        :return:
        """
        success_conditions = (
            # 停止插件时，若插件本身未运行，也认为是成功
            op_type == constants.GseOpType.STOP
            and error_code == GseDataErrCode.NON_EXIST
        ) or (
            # 启动插件时，若插件本身已运行，也认为是成功
            op_type == constants.GseOpType.START
            and error_code == GseDataErrCode.PROC_RUNNING
        )
        if error_code == GseDataErrCode.RUNNING:
            # 只要有运行中的任务，则认为未完成，标记 is_finished
            is_finished = False
            if polling_time + POLLING_INTERVAL > POLLING_TIMEOUT:
                self.move_insts_to_failed([subscription_instance.id], _("GSE任务轮询超时"))
        elif success_conditions:
            # 状态码非 SUCCESS 的，但满足成功的特殊条件，认为是成功的，无需做任何处理
            pass
        elif error_code != GseDataErrCode.SUCCESS:
            # 其它状态码非 SUCCESS 的任务则认为是失败的
            self.move_insts_to_failed([subscription_instance.id], error_msg)
        return is_finished

    def _schedule(self, data, parent_data, callback_data=None):
        op_type = data.get_one_of_inputs("op_type")
        task_id = data.get_one_of_outputs("task_id")
        polling_time = data.get_one_of_outputs("polling_time")
        common_data = self.get_common_data(data)
        process_statuses = common_data.process_statuses
        policy_step_adapter = common_data.policy_step_adapter
        plugin = policy_step_adapter.plugin_desc
        group_id_instance_map = common_data.group_id_instance_map

        result = GseApi.get_proc_operate_result({"task_id": task_id}, raw=True)
        api_code = result.get("code")
        if api_code == GSE_RUNNING_TASK_CODE:
            # GSE_RUNNING_TASK_CODE(1000115) 表示查询的任务等待执行中，还未入到 redis（需继续轮询进行查询）
            data.outputs.polling_time = polling_time + POLLING_INTERVAL
            return True

        polling_time = data.get_one_of_outputs("polling_time")
        is_finished = True
        for process_status in process_statuses:
            host = self.get_host_by_process_status(process_status, common_data)
            subscription_instance = group_id_instance_map.get(process_status.group_id)

            proc_name = self.get_plugin_meta_name(plugin, process_status)
            gse_proc_key = f"{host.bk_cloud_id}:{host.inner_ip}:{constants.GSE_NAMESPACE}:{proc_name}"
            proc_operate_result = result["data"].get(gse_proc_key)
            if not proc_operate_result:
                self.move_insts_to_failed(
                    [subscription_instance.id],
                    _("GSE任务查无结果, {task_id}, {key}").format(task_id=task_id, key=gse_proc_key),
                )
                continue

            error_code = proc_operate_result["error_code"]
            error_msg = proc_operate_result["error_msg"]
            is_finished = self.handle_error_code(
                error_code, error_msg, op_type, polling_time, subscription_instance, is_finished
            )

        if is_finished:
            self.finish_schedule()
        data.outputs.polling_time = polling_time + POLLING_INTERVAL
        return True

    def outputs_format(self):
        return [
            Service.OutputItem(name="task_id", key="task_id", type="int"),
            Service.OutputItem(name="polling_time", key="polling_time", type="int"),
            Service.OutputItem(name="task_result", key="task_result", type="dict"),
            Service.OutputItem(name="result", key="result", type="dict"),
        ]


class ResetRetryTimesService(PluginBaseService):
    """
    重置重试次数，放到流程的最后一个原子，当前置原子都成功执行后，重置任务的重试次数以便后续任务的自动执行
    """

    def inputs_format(self):
        return [
            Service.InputItem(name="host_status_id", key="host_status_id", type="int", required=True),
        ]

    def _execute(self, data, parent_data, common_data: PluginCommonData):
        plugin_name = data.get_one_of_inputs("plugin_name")
        group_id_instance_map = common_data.group_id_instance_map
        models.ProcessStatus.objects.filter(name=plugin_name, group_id__in=group_id_instance_map.keys()).update(
            retry_times=0
        )


class DebugService(PluginExecuteScriptService):
    """
    调用作业平台接口调试插件
    """

    # debug的最长时间，单位：秒
    MAX_DEBUG_POLLING_TIME = 250

    @property
    def script_name(self):
        return "operate_plugin"

    def generate_script_params_by_process_status(
        self, process_status: models.ProcessStatus, common_data: PluginCommonData
    ) -> str:
        policy_step_adapter = common_data.policy_step_adapter
        package = self.get_package_by_process_status(process_status, common_data)
        plugin = policy_step_adapter.plugin_desc
        control = package.proc_control
        return "-t {category} -p {install_path} -n {name} -c {command} -g {group_id}".format(
            category=plugin.category,
            install_path=control.install_path,
            name=plugin.name,
            command=control.debug_cmd,
            group_id=process_status.group_id,
        )

    def _schedule(self, data, parent_data, callback_data=None):
        job_sub_inst_map = models.JobSubscriptionInstanceMap.objects.filter(node_id=self.id).first()
        subscription_instance_id = job_sub_inst_map.subscription_instance_ids[0]
        job_instance_id = job_sub_inst_map.job_instance_id

        result = JobApi.get_job_instance_status(
            {"bk_biz_id": settings.BLUEKING_BIZ_ID, "job_instance_id": job_instance_id, "return_ip_result": True}
        )
        # 调试插件时仅有一个IP，以下取值方式与作业平台API文档一致，不会抛出 IndexError/KeyError 的异常
        step_instance_id = result["step_instance_list"][0]["step_instance_id"]
        ip = result["step_instance_list"][0]["step_ip_result_list"][0]["ip"]
        bk_cloud_id = result["step_instance_list"][0]["step_ip_result_list"][0]["bk_cloud_id"]

        params = {
            "job_instance_id": job_instance_id,
            "bk_biz_id": settings.BLUEKING_BIZ_ID,
            "bk_username": settings.BACKEND_JOB_OPERATOR,
            "step_instance_id": step_instance_id,
            "ip": ip,
            "bk_cloud_id": bk_cloud_id,
        }
        task_result = JobApi.get_job_instance_ip_log(params)

        # 只写入新的日志，保证轮询过程中不会重复写入job的日志
        last_logs = data.get_one_of_outputs("last_logs", "")
        # job在任务pending的情况下，返回的log_content为None，new_logs.replace(last_logs, "") 需要保证字符串类型
        new_logs = task_result.get("log_content") or ""
        self.log_info([subscription_instance_id], new_logs.replace(last_logs, ""))
        data.outputs.last_logs = new_logs

        # debug 时间超过250秒，自动完成并流转到下一个原子进行stop debug
        polling_time = data.get_one_of_outputs("polling_time") or 0
        if polling_time > self.MAX_DEBUG_POLLING_TIME:
            self.finish_schedule()
            return True
        data.outputs.polling_time = polling_time + POLLING_INTERVAL


class StopDebugService(PluginExecuteScriptService):
    """
    调用作业平台接口停止调试插件
    """

    @property
    def script_name(self):
        return "stop_debug"

    def generate_script_params_by_process_status(
        self, process_status: models.ProcessStatus, common_data: PluginCommonData
    ) -> str:
        policy_step_adapter = common_data.policy_step_adapter
        package = self.get_package_by_process_status(process_status, common_data)
        plugin = policy_step_adapter.plugin_desc
        control = package.proc_control
        return "-p {install_path} -n {name}  -g {group_id}".format(
            install_path=control.install_path, name=plugin.name, group_id=process_status.group_id
        )


class DeleteSubscriptionService(PluginBaseService):
    def _execute(self, data, parent_data, common_data: PluginCommonData):
        subscription = common_data.subscription
        subscription_instance_ids = common_data.subscription_instance_ids

        sub_alias = _("策略") if subscription.category == models.Subscription.CategoryType.POLICY else _("订阅")

        if subscription.enable:
            self.move_insts_to_failed(
                sub_inst_ids=subscription_instance_ids,
                log_content=_("{sub_alias} -> {id}「{name}」 已启用，删除失败").format(
                    sub_alias=sub_alias, id=subscription.id, name=subscription.name
                ),
            )

        proc_count = models.ProcessStatus.objects.filter(
            source_type=models.ProcessStatus.SourceType.DEFAULT, is_latest=True, source_id=subscription.id
        ).count()

        self.log_info(
            log_content=_("{sub_alias} -> {id}「{name}」，已部署节点数 -> {proc_count}").format(
                sub_alias=sub_alias, id=subscription.id, name=subscription.name, proc_count=proc_count
            )
        )

        if proc_count:
            # 情况1：单批执行，到达删除流程前已有主机失败，此时整体执行失败，策略删除失败
            # 情况2：主机数量多分批执行，由最后一个批次执行删除
            self.log_info(
                log_content=_("{sub_alias} -> {id}「{name}」 已部署节点数不为 0，跳过").format(
                    sub_alias=sub_alias, id=subscription.id, name=subscription.name
                )
            )
            return
        else:
            subscription.delete()

        self.log_info(
            log_content=_("{sub_alias} -> {id}「{name}」删除成功").format(
                sub_alias=sub_alias, id=subscription.id, name=subscription.name
            )
        )


class SwitchSubscriptionEnableService(PluginBaseService):
    def inputs_format(self):
        return [
            Service.InputItem(name="enable", key="enable", type="bool", required=True),
        ]

    def _execute(self, data, parent_data, common_data: PluginCommonData):
        enable = data.get_one_of_inputs("enable")
        subscription = common_data.subscription

        sub_alias = models.Subscription.CATEGORY_ALIAS_MAP.get(subscription.category, _("订阅"))

        if subscription.category in [models.Subscription.CategoryType.ONCE]:
            self.log_info(
                log_content=_("{sub_alias} -> {id} 仅提供单次执行能力，保持{enable_alias}状态").format(
                    sub_alias=sub_alias,
                    id=subscription.id,
                    enable_alias=_("启用") if subscription.enable else _("停用"),
                )
            )
            return

        # 分批聚合场景下，更新逻辑可能被执行多次，若状态已变更，直接跳过
        if subscription.enable != enable:
            subscription.enable = enable
            subscription.save(update_fields=["enable", "update_time"])

        self.log_info(
            log_content=_("{sub_alias} -> {id}「{name}」切换为：{enable_alias}").format(
                sub_alias=sub_alias,
                id=subscription.id,
                name=subscription.name,
                enable_alias=_("启用") if subscription.enable else _("停用"),
            )
        )


class InitProcessStatusComponent(Component):
    name = "InitProcessStatus"
    code = "init_process_status"
    bound_service = InitProcessStatusService


class TransferPackageComponent(Component):
    name = "TransferPackage"
    code = "transfer_package"
    bound_service = TransferPackageService


class InstallPackageComponent(Component):
    name = "InstallPackage"
    code = "install_package"
    bound_service = InstallPackageService


class UnInstallPackageComponent(Component):
    name = "UnInstallPackage"
    code = "uninstall_package"
    bound_service = UnInstallPackageService


class CheckAgentStatusComponent(Component):
    name = "CheckAgentStatus"
    code = "check_agent_status"
    bound_service = CheckAgentStatusService


class RenderAndPushConfigComponent(Component):
    name = "RenderAndPushConfig"
    code = "render_and_push_config"
    bound_service = RenderAndPushConfigService


class GseOperateProcComponent(Component):
    name = "GseOperateProc"
    code = "gse_operate_proc"
    bound_service = GseOperateProcService


class RemoveConfigComponent(Component):
    name = "RemoveConfig"
    code = "remove_config"
    bound_service = RemoveConfigService


class ResetRetryTimesComponent(Component):
    name = "ResetRetryTimes"
    code = "reset_retry_times"
    bound_service = ResetRetryTimesService


class UpdateHostProcessStatusComponent(Component):
    name = "UpdateHostProcessStatus"
    code = "update_host_process_status"
    bound_service = UpdateHostProcessStatusService


class DebugComponent(Component):
    name = "DebugComponent"
    code = "DEBUG_PROCESS"  # 此ID监控需要使用，请勿随意修改
    bound_service = DebugService


class StopDebugComponent(Component):
    name = "StopDebugComponent"
    code = "STOP_DEBUG_PROCESS"  # 此ID监控需要使用，请勿随意修改
    bound_service = StopDebugService


class JobAllocatePortComponent(Component):
    name = "JobAllocatePortComponent"
    code = "job_allocate_port"
    bound_service = JobAllocatePortService


class DeleteSubscriptionComponent(Component):
    name = "DeleteSubscriptionComponent"
    code = "delete_subscription"
    bound_service = DeleteSubscriptionService


class SwitchSubscriptionEnableComponent(Component):
    name = "SwitchSubscriptionEnableComponent"
    code = "switch_subscription_enable"
    bound_service = SwitchSubscriptionEnableService
