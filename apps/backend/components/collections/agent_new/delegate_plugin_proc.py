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
import json
import ntpath
import posixpath
from collections import defaultdict
from typing import Any, Dict, List, Set, Union

from django.db.models import Max
from django.utils.translation import ugettext_lazy as _

from apps.backend.api.constants import (
    GSE_RUNNING_TASK_CODE,
    POLLING_INTERVAL,
    POLLING_TIMEOUT,
    GseDataErrCode,
)
from apps.node_man import constants, models
from apps.utils import concurrent
from common.api import GseApi
from pipeline.core.flow import Service, StaticIntervalGenerator

from .base import AgentBaseService, AgentCommonData


class DelegatePluginProcService(AgentBaseService):

    __need_schedule__ = True
    interval = StaticIntervalGenerator(POLLING_INTERVAL)

    def inputs_format(self):
        return super().inputs_format() + [
            Service.InputItem(name="plugin_name", key="plugin_name", type="str", required=True)
        ]

    def outputs_format(self):
        return super().outputs_format() + [
            Service.InputItem(name="task_id", key="task_id", type="str", required=True),
            Service.InputItem(name="proc_name", key="proc_name", type="str", required=True),
            Service.InputItem(name="polling_time", key="polling_time", type="int", required=True),
        ]

    def update_proc_infos(
        self, sub_insts: List[models.SubscriptionInstanceRecord], host_objs: List[models.Host], package: models.Packages
    ) -> List[int]:
        """
        更新插件进程信息
        :param sub_insts: 订阅实例列表
        :param host_objs: 主机对象列表
        :param package: 插件包
        :return: 成功更新进程信息的主机ID列表
        """
        proc_name = package.project
        proc_control: models.ProcControl = package.proc_control
        if package.os == constants.PluginOsType.windows:
            path_handler = ntpath
        else:
            path_handler = posixpath
        setup_path = path_handler.join(
            package.proc_control.install_path, constants.PluginChildDir.OFFICIAL.value, "bin"
        )
        pid_path = package.proc_control.pid_path
        update_proc_info_params = {
            "meta": {"labels": {"proc_name": proc_name}, "namespace": constants.GSE_NAMESPACE, "name": proc_name},
            "spec": {
                "control": {
                    "start_cmd": proc_control.start_cmd,
                    "stop_cmd": proc_control.stop_cmd,
                    "restart_cmd": proc_control.restart_cmd,
                    "reload_cmd": proc_control.reload_cmd or proc_control.restart_cmd,
                    "kill_cmd": proc_control.kill_cmd,
                    "version_cmd": proc_control.version_cmd,
                    "health_cmd": proc_control.health_cmd,
                },
                "monitor_policy": {"auto_type": 1},
                "resource": {"mem": 10, "cpu": 10},
                "identity": {
                    "user": constants.ACCOUNT_MAP.get(package.os, "root"),
                    "proc_name": proc_name,
                    "setup_path": setup_path,
                    "pid_path": pid_path,
                },
            },
        }

        sub_inst_ids: List[int] = [sub_inst.id for sub_inst in sub_insts]
        self.log_info(
            sub_inst_ids=sub_inst_ids,
            log_content=_(
                "更新 {proc_name} 进程信息：call GSE api -> update_proc_info with params: \n {query_params})"
            ).format(proc_name=proc_name, query_params=json.dumps(update_proc_info_params, indent=2)),
        )
        update_proc_info_params["hosts"] = [
            {
                "ip": host_obj.inner_ip,
                "bk_cloud_id": host_obj.bk_cloud_id,
                "bk_supplier_id": constants.DEFAULT_SUPPLIER_ID,
            }
            for host_obj in host_objs
        ]

        gse_proc_key__proc_result_map: Dict[str, Dict[str, Any]] = GseApi.update_proc_info(update_proc_info_params)

        success_host_ids: List[int] = []
        success_sub_inst_ids: List[int] = []
        host_id__sub_inst_id_map: Dict[int, int] = {
            sub_inst.instance_info["host"]["bk_host_id"]: sub_inst.id for sub_inst in sub_insts
        }
        for host_obj in host_objs:
            sub_inst_id = host_id__sub_inst_id_map[host_obj.bk_host_id]
            gse_proc_key = (
                f"{host_obj.bk_cloud_id}:{constants.DEFAULT_SUPPLIER_ID}:{host_obj.inner_ip}:"
                f"{constants.GSE_NAMESPACE}:{proc_name}"
            )
            proc_result = gse_proc_key__proc_result_map.get(gse_proc_key)
            if not proc_result:
                self.move_insts_to_failed(
                    [sub_inst_id],
                    log_content=_("未能查询到进程更新结果，gse_proc_key -> {gse_proc_key}".format(gse_proc_key=gse_proc_key)),
                )
                continue

            error_code = proc_result.get("error_code")
            if error_code != GseDataErrCode.SUCCESS:
                self.move_insts_to_failed(
                    [sub_inst_id],
                    log_content=_(
                        "GSE 更新 {proc_name} 进程信息失败，gse_proc_key -> {gse_proc_key}, "
                        "error_code -> {error_code}, error_msg -> {error_msg}"
                    ).format(
                        proc_name=proc_name,
                        gse_proc_key=gse_proc_key,
                        error_code=error_code,
                        error_msg=proc_result.get("error_msg"),
                    ),
                )
                continue

            success_host_ids.append(host_obj.bk_host_id)
            success_sub_inst_ids.append(host_id__sub_inst_id_map[host_obj.bk_host_id])

        self.log_info(
            sub_inst_ids=success_sub_inst_ids, log_content=_("已成功更新 {proc_name} 进程信息").format(proc_name=proc_name)
        )
        return success_host_ids

    def _execute(self, data, parent_data, common_data: AgentCommonData):
        host_id_obj_map = common_data.host_id_obj_map
        plugin_name = data.get_one_of_inputs("plugin_name")
        latest_pkg_ids_of_each_os: List[int] = (
            models.Packages.objects.filter(project=plugin_name, cpu_arch=constants.CpuType.x86_64)
            .values("os")
            .annotate(id=Max("id"))
            .values_list("id", flat=True)
        )
        packages = models.Packages.objects.filter(id__in=latest_pkg_ids_of_each_os)
        os__package_map: Dict[str, models.Packages] = {package.os: package for package in packages}

        skipped_host_ids: Set[int] = set()
        bk_host_id__sub_inst_id_map: Dict[int, int] = {}
        # 按操作系统类型对订阅实例进行聚合，仅取匹配插件包成功的实例
        host_objs_gby_host_os: Dict[str, List[models.Host]] = defaultdict(list)
        sub_insts_gby_host_os: Dict[str, List[models.SubscriptionInstanceRecord]] = defaultdict(list)
        for sub_inst in common_data.subscription_instances:
            host_obj: models.Host = host_id_obj_map[sub_inst.instance_info["host"]["bk_host_id"]]
            # 处理插件包不适配的场景
            if host_obj.os_type.lower() not in os__package_map:
                skipped_host_ids.add(host_obj.bk_host_id)
                # 考虑这种情况较少且为了简化逻辑，暂不聚合相同日志内容再打印
                self.log_warning(
                    [sub_inst.id],
                    log_content=_("「{plugin_name}」不支持操作系统 -> {os_type}，跳过该步骤").format(
                        plugin_name=plugin_name, os_type=host_obj.os_type
                    ),
                )
                continue

            bk_host_id__sub_inst_id_map[host_obj.bk_host_id] = sub_inst.id
            sub_insts_gby_host_os[host_obj.os_type].append(sub_inst)
            host_objs_gby_host_os[host_obj.os_type].append(host_obj)

        # 根据操作系统，多线程请求 update_proc_infos
        update_proc_infos_params_list: List[Dict] = []
        for os_upper, sub_insts in sub_insts_gby_host_os.items():
            package = os__package_map[os_upper.lower()]
            update_proc_infos_params_list.append(
                {"sub_insts": sub_insts, "host_objs": host_objs_gby_host_os[os_upper], "package": package}
            )

        # 并发请求GSE，更新进程信息
        host_ids_to_be_delegate_proc = concurrent.batch_call(
            func=self.update_proc_infos,
            params_list=update_proc_infos_params_list,
            get_data=lambda x: x,
            extend_result=True,
        )

        # 没有需要托管进程的主机，直接结束调度并返回
        if not host_ids_to_be_delegate_proc:
            self.finish_schedule()
            return

        # 构造需要托管进程的主机信息
        sub_insts_ids_to_be_delegate_proc: List[int] = []
        hosts_need_delegate_proc: List[Dict[str, Union[str, int]]] = []
        for bk_host_id in host_ids_to_be_delegate_proc:
            host_obj = host_id_obj_map[bk_host_id]
            sub_insts_ids_to_be_delegate_proc.append(bk_host_id__sub_inst_id_map[host_obj.bk_host_id])
            hosts_need_delegate_proc.append({"ip": host_obj.inner_ip, "bk_cloud_id": host_obj.bk_cloud_id})

        # 构造托管进程参数
        delegate_proc_base_params = {
            "meta": {"labels": {"proc_name": plugin_name}, "namespace": constants.GSE_NAMESPACE, "name": plugin_name},
            "op_type": constants.GseOpType.DELEGATE,
        }
        self.log_info(
            sub_insts_ids_to_be_delegate_proc,
            log_content=(
                _("托管 {proc_name} 进程：call GSE api -> operate_proc_v2 with params: \n {query_params}").format(
                    proc_name=plugin_name, query_params=json.dumps(delegate_proc_base_params, indent=2)
                )
            ),
        )
        task_id = GseApi.operate_proc({**delegate_proc_base_params, "hosts": hosts_need_delegate_proc})["task_id"]
        self.log_info(sub_insts_ids_to_be_delegate_proc, f"GSE TASK ID: [{task_id}]")

        data.outputs.polling_time = 0
        data.outputs.task_id = task_id
        data.outputs.proc_name = plugin_name
        data.outputs.skipped_host_ids = skipped_host_ids

    def _schedule(self, data, parent_data, callback_data=None):
        task_id = data.get_one_of_outputs("task_id")
        polling_time = data.get_one_of_outputs("polling_time")
        skipped_host_ids: Set[int] = data.get_one_of_outputs("skipped_host_ids")

        # 查询进程操作结果，raw=True，返回接口完整响应数据
        procs_operate_result = GseApi.get_proc_operate_result({"task_id": task_id}, raw=True)

        api_code = procs_operate_result.get("code")
        if api_code == GSE_RUNNING_TASK_CODE:
            # GSE_RUNNING_TASK_CODE(1000115) 表示查询的任务等待执行中，还未入到 redis（需继续轮询进行查询）
            data.outputs.polling_time = polling_time + POLLING_INTERVAL
            return True

        is_finished = True
        common_data = self.get_common_data(data)
        proc_name = data.get_one_of_outputs("proc_name")
        for sub_inst in common_data.subscription_instances:
            host_obj = common_data.host_id_obj_map[sub_inst.instance_info["host"]["bk_host_id"]]
            gse_proc_key = f"{host_obj.bk_cloud_id}:{host_obj.inner_ip}:{constants.GSE_NAMESPACE}:{proc_name}"

            if host_obj.bk_host_id in skipped_host_ids:
                continue

            proc_operate_result = procs_operate_result["data"].get(gse_proc_key)
            if not proc_operate_result:
                self.move_insts_to_failed(
                    [sub_inst.id],
                    log_content=_("未能查询到进程操作结果, task_id -> {task_id}, gse_proc_key -> {key}").format(
                        task_id=task_id, key=gse_proc_key
                    ),
                )
                continue

            error_msg = proc_operate_result["error_msg"]
            error_code = proc_operate_result["error_code"]
            if error_code == GseDataErrCode.RUNNING:
                # 只要有运行中的任务，则认为未完成，标记 is_finished
                is_finished = False
                if polling_time + POLLING_INTERVAL > POLLING_TIMEOUT:
                    self.move_insts_to_failed([sub_inst.id], _("GSE任务轮询超时"))
            elif error_code != GseDataErrCode.SUCCESS:
                # 其它状态码非 SUCCESS 的任务则认为是失败的
                self.move_insts_to_failed(
                    [sub_inst.id],
                    log_content=_("调用 GSE 接口异常：错误码 -> {error_code}「{error_code_alias}」, 错误信息 -> {error_msg}").format(
                        error_code_alias=GseDataErrCode.ERROR_CODE__ALIAS_MAP.get(error_code, error_code),
                        error_msg=error_msg,
                        error_code=error_code,
                    ),
                )

        if is_finished:
            self.finish_schedule()
            return True
        data.outputs.polling_time = polling_time + POLLING_INTERVAL
