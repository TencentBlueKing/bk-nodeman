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
import copy
import hashlib
import json
import logging
from typing import Any, Callable, Dict, List, Optional

import six
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from apps.backend.api.constants import POLLING_INTERVAL, POLLING_TIMEOUT
from apps.backend.api.job import process_parms
from apps.backend.components.collections.base import BaseService, CommonData
from apps.core.files.storage import get_storage
from apps.exceptions import AppBaseException
from apps.node_man import constants, models
from apps.utils.batch_request import request_multi_thread
from common.api import JobApi
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service, StaticIntervalGenerator

logger = logging.getLogger("app")


class JobV3BaseService(six.with_metaclass(abc.ABCMeta, BaseService)):
    """
    作业平台V3，基于subscription instance record流转，注意 execute 方法中需要写入 JobSubscriptionInstanceMap
    # 当前 pipeline 引擎中，multi callback schedule 只能串行运行，高并发时存在性能问题
    # TODO 因此这里暂时使用主动查询的方式，后续切换新引擎时可以考虑使用 callback 回调的模式
    """

    # 默认操作系统类型
    DEFAULT_OS_TYPE = constants.OsType.LINUX

    # 是否打印作业平台调用参数
    PRINT_PARAMS_TO_LOG: bool = False

    __need_schedule__ = True

    interval = StaticIntervalGenerator(POLLING_INTERVAL)

    # 作业实例ID - 调用参数映射关系
    job_instance_id__call_params_map: Optional[Dict[int, Dict[str, Any]]] = None

    def inputs_format(self):
        return super().inputs_format() + [
            # 是否跳过作业平台任务结果轮训
            Service.InputItem(name="skip_polling_result", key="skip_polling_result", type="str", required=False),
        ]

    def __init__(self, *args, **kwargs):
        self.job_instance_id__call_params_map = {}
        super().__init__(*args, **kwargs)

    @staticmethod
    def get_md5(content):
        md5 = hashlib.md5()
        md5.update(content.encode("utf-8"))
        return md5.hexdigest()

    def run_job_or_finish_schedule(self, multi_job_params_map: Dict):
        """如果作业平台参数为空，代表无需执行，直接finish_schedule去执行下一个原子"""
        if multi_job_params_map:
            request_multi_thread(self.request_single_job_and_create_map, multi_job_params_map.values())
        else:
            self.finish_schedule()

    def request_single_job_and_create_map(
        self, job_func, subscription_instance_id: [int, list], subscription_id, job_params: dict
    ):
        """请求作业平台并创建与订阅实例的映射"""
        if not job_params["target_server"]["ip_list"]:
            # 没有IP列表时，不发起请求
            return []

        # 补充作业平台通用参数
        if not job_params.get("os_type"):
            job_params["os_type"] = self.DEFAULT_OS_TYPE
        os_type = job_params["os_type"]

        # Windows 执行账户问题：已确认用 administrator 注册也可以用 system 账户执行，统一使用 system 执行即可
        # Ref -> https://github.com/TencentBlueKing/bk-nodeman/pull/290#discussion_r760064447
        account_alias = (settings.BACKEND_UNIX_ACCOUNT, settings.BACKEND_WINDOWS_ACCOUNT)[
            os_type == constants.OsType.WINDOWS
        ]
        script_language = (constants.ScriptLanguageType.SHELL.value, constants.ScriptLanguageType.BAT.value)[
            os_type == constants.OsType.WINDOWS
        ]
        job_params.update(
            {
                "bk_biz_id": settings.BLUEKING_BIZ_ID,
                "bk_scope_type": constants.BkJobScopeType.BIZ_SET.value,
                "bk_scope_id": settings.BLUEKING_BIZ_ID,
                "script_language": script_language,
                "script_content": process_parms(job_params.get("script_content", "")),
                "script_param": process_parms(job_params.get("script_param", "")),
                "task_name": f"NODE_MAN_{subscription_id}_{self.__class__.__name__}",
                "account_alias": account_alias,
            }
        )

        if not job_params.get("timeout"):
            # 设置默认超时时间
            job_params["timeout"] = constants.JOB_TIMEOUT

        if isinstance(subscription_instance_id, int):
            subscription_instance_id = [subscription_instance_id]

        try:
            storage = get_storage()
            job_params = storage.process_query_params(job_func, job_params)
            # 请求作业平台
            job_instance_id = job_func(job_params)["job_instance_id"]
        except AppBaseException as err:
            self.move_insts_to_failed(subscription_instance_id, str(err))
        else:
            models.JobSubscriptionInstanceMap.objects.create(
                job_instance_id=job_instance_id,
                subscription_instance_ids=subscription_instance_id,
                node_id=self.id,
            )
            self.job_instance_id__call_params_map[job_instance_id] = {
                "subscription_id": subscription_id,
                "subscription_instance_id": subscription_instance_id,
                "job_params": job_params,
            }
            # 组装调用作业平台的日志
            file_target_path = job_params.get("file_target_path")
            if job_func == JobApi.fast_transfer_file:
                log = storage.gen_transfer_file_log(
                    file_target_path=file_target_path, file_source_list=job_params.get("file_source_list")
                )
            # 节点管理仅使用 push_config_file 下发 content，不涉及从文件源读取文件
            elif job_func == JobApi.push_config_file:
                file_names = ",".join([file["file_name"] for file in job_params.get("file_list", [])])
                log = f"下发配置文件 [{file_names}] 到目标机器路径 [{file_target_path}]，若下发失败，请检查作业平台所部署的机器是否已安装AGENT"
            elif job_func == JobApi.fast_execute_script:
                log = f"快速执行脚本 {getattr(self, 'script_name', '')}"
            else:
                log = "调用作业平台"

            # 采用拼接上文的方式添加接口请求日志，减少DB操作
            if self.PRINT_PARAMS_TO_LOG:
                api_params_log = self.generate_api_params_log(
                    subscription_instance_ids=subscription_instance_id, job_params=job_params, job_func=job_func
                )
                log = f"{log}, 请求参数为：\n {api_params_log}"

            self.log_info(
                subscription_instance_id,
                _('{log}\n作业任务ID为 [{job_instance_id}]，点击跳转到 <a href="{link}" target="_blank">[作业平台]</a>').format(
                    log=log,
                    job_instance_id=job_instance_id,
                    link=f"{settings.BK_JOB_HOST}/{settings.BLUEKING_BIZ_ID}/execute/step/{job_instance_id}",
                ),
            )
        return []

    def generate_api_params_log(
        self, subscription_instance_ids: List[int], job_params: Dict[str, Any], job_func: Callable
    ) -> str:
        """
        生成接口调用参数日志
        :param subscription_instance_ids:
        :param job_params:
        :param job_func:
        :return:
        """
        job_params = copy.deepcopy(job_params)
        # 聚合执行场景下，打印的日志忽略 ip_list，从而屏蔽差异
        job_params.pop("target_server", None)
        return json.dumps(job_params, indent=2)

    def handler_job_result(self, job_sub_map, cloud_ip_status_map):
        subscription_instances = models.SubscriptionInstanceRecord.objects.filter(
            id__in=job_sub_map.subscription_instance_ids
        )

        for sub_inst in subscription_instances:
            ip = sub_inst.instance_info["host"]["bk_host_innerip"]
            cloud_id = sub_inst.instance_info["host"]["bk_cloud_id"]
            cloud_ip = f"{cloud_id}-{ip}"
            try:
                ip_result = cloud_ip_status_map[cloud_ip]
            except KeyError:
                ip_status = constants.BkJobIpStatus.NOT_RUNNING
                err_code = constants.BkJobErrorCode.NOT_RUNNING
            else:
                ip_status = ip_result["status"]
                err_code = ip_result["error_code"]
            err_msg = "作业执行状态 -> {status}「{ip_status_msg}」, 主机任务状态码 -> {error_code}「{err_msg}」".format(
                status=ip_status,
                ip_status_msg=(
                    constants.BkJobIpStatus.BK_JOB_IP_STATUS_MAP.get(ip_status)
                    or constants.BkJobErrorCode.BK_JOB_ERROR_CODE_MAP.get(ip_status)
                ),
                error_code=err_code,
                err_msg=constants.BkJobErrorCode.BK_JOB_ERROR_CODE_MAP.get(err_code),
            )
            if ip_status != constants.BkJobIpStatus.SUCCEEDED:
                self.move_insts_to_failed([sub_inst.id], _("作业平台执行失败: {err_msg}").format(err_msg=err_msg))

    def request_get_job_instance_status(self, job_sub_map: models.JobSubscriptionInstanceMap):
        """查询作业平台执行状态"""
        result = JobApi.get_job_instance_status(
            {
                "bk_biz_id": settings.BLUEKING_BIZ_ID,
                "job_instance_id": job_sub_map.job_instance_id,
                "return_ip_result": False,
            }
        )
        job_status = result["job_instance"]["status"]

        if job_status in (constants.BkJobStatus.PENDING, constants.BkJobStatus.RUNNING):
            # 任务未完成，直接跳过，等待下次查询
            return

        if job_status == constants.BkJobStatus.SUCCEEDED:
            # 任务成功，记录状态，避免下次继续查询
            job_sub_map.status = job_status
            job_sub_map.save()
            return

        # 其它都认为存在失败的情况，需要具体查作业平台的接口查IP详情
        ip_results = JobApi.get_job_instance_status(
            {
                "bk_biz_id": settings.BLUEKING_BIZ_ID,
                "bk_scope_type": constants.BkJobScopeType.BIZ_SET.value,
                "bk_scope_id": settings.BLUEKING_BIZ_ID,
                "job_instance_id": job_sub_map.job_instance_id,
                "return_ip_result": True,
            }
        )

        # 构造主机作业状态映射表
        cloud_ip_status_map = {}
        for ip_result in ip_results["step_instance_list"][0]["step_ip_result_list"]:
            cloud_ip_status_map[f'{ip_result["bk_cloud_id"]}-{ip_result["ip"]}'] = ip_result

        self.handler_job_result(job_sub_map, cloud_ip_status_map)

        job_sub_map.status = job_status
        job_sub_map.save()

    def skip_polling_result_by_os_types(self, os_types: Optional[List[str]] = None):
        """
        跳过作业平台结果轮训
        :param os_types: 操作系统类型列表，为 None 全豁免
        :return:
        """
        sub_inst_ids = []
        skip_job_instance_ids: List[int] = []
        for job_instance_id, call_params in self.job_instance_id__call_params_map.items():
            # 通过调用参数判断 job_instance_id 是否执行的是 Windows 机器
            os_type = call_params["job_params"]["os_type"]
            if os_types is None or os_type in os_types:
                skip_job_instance_ids.append(job_instance_id)
                sub_inst_ids.extend(call_params["subscription_instance_id"])
        self.log_info(sub_inst_ids=sub_inst_ids, log_content=_("该步骤无需等待作业平台执行结果"))

        models.JobSubscriptionInstanceMap.objects.filter(
            node_id=self.id, job_instance_id__in=skip_job_instance_ids, status=constants.BkJobStatus.PENDING
        ).update(status=constants.BkJobStatus.SUCCEEDED)

    def _schedule(self, data, parent_data, callback_data=None):
        polling_time = data.get_one_of_outputs("polling_time") or 0
        skip_polling_result = data.get_one_of_inputs("skip_polling_result", default=False)
        # 查询未完成的作业, 批量查询作业状态并更新DB
        multi_params = [
            {"job_sub_map": job_sub_map}
            for job_sub_map in models.JobSubscriptionInstanceMap.objects.filter(
                node_id=self.id, status=constants.BkJobStatus.PENDING
            )
        ]

        # 处理跳过作业平台结果轮训的情况
        if skip_polling_result:
            self.skip_polling_result_by_os_types()
            self.finish_schedule()
            return

        request_multi_thread(self.request_get_job_instance_status, multi_params)

        # 判断 JobSubscriptionInstanceMap 中对应的 job_instance_id 都执行完成的，把成功的 subscription_instance_ids 向下传递
        is_finished = not models.JobSubscriptionInstanceMap.objects.filter(
            node_id=self.id, status=constants.BkJobStatus.PENDING
        ).exists()
        if is_finished:
            self.finish_schedule()
        elif polling_time + POLLING_INTERVAL > POLLING_TIMEOUT:
            # 由于JOB的超时机制可能会失效，因此这里节点管理自己需要有超时机制进行兜底
            pending_job_sub_maps = models.JobSubscriptionInstanceMap.objects.filter(
                node_id=self.id, status=constants.BkJobStatus.PENDING
            )
            pending_sub_inst_ids: List[int] = []
            for pending_job_sub_map in pending_job_sub_maps:
                pending_sub_inst_ids.extend(pending_job_sub_map.subscription_instance_ids)
            self.move_insts_to_failed(sub_inst_ids=pending_sub_inst_ids, log_content=_("作业平台执行任务超时"))
            models.JobSubscriptionInstanceMap.objects.filter(
                node_id=self.id, status=constants.BkJobStatus.PENDING
            ).update(status=constants.BkJobStatus.FAILED)
            self.finish_schedule()
        data.outputs.polling_time = polling_time + POLLING_INTERVAL


class JobExecuteScriptService(JobV3BaseService, metaclass=abc.ABCMeta):

    PRINT_PARAMS_TO_LOG = True

    def inputs_format(self):
        return super().inputs_format() + [
            Service.InputItem(name="script_content", key="script_content", type="str", required=False),
            Service.InputItem(name="script_param", key="script_param", type="str", required=False),
        ]

    @property
    def script_name(self):
        """插件需要执行的脚本文件名称，由子类继承定义"""
        return ""

    def _execute(self, data, parent_data, common_data: CommonData):

        timeout = data.get_one_of_inputs("timeout")
        # 批量请求作业平台的参数
        multi_job_params_map: Dict[str, Dict[str, Any]] = {}
        for sub_inst in common_data.subscription_instances:
            bk_host_id = sub_inst.instance_info["host"]["bk_host_id"]
            host_obj = common_data.host_id_obj_map[bk_host_id]
            script_param = self.get_script_param(data=data, common_data=common_data, host=host_obj)
            script_content = self.get_script_content(data=data, common_data=common_data, host=host_obj)

            # script_content 和 script_param md5一样的则认为是同样的脚本操作，合并到一个作业中，提高执行效率
            script_content_md5 = self.get_md5(script_content)
            script_param_md5 = self.get_md5(script_param)
            md5_key = f"{script_content_md5}-{script_param_md5}"

            if md5_key in multi_job_params_map:
                multi_job_params_map[md5_key]["subscription_instance_id"].append(sub_inst.id)
                multi_job_params_map[md5_key]["job_params"]["target_server"]["ip_list"].append(
                    {"bk_cloud_id": host_obj.bk_cloud_id, "ip": host_obj.inner_ip}
                )
            else:
                multi_job_params_map[md5_key] = {
                    "job_func": JobApi.fast_execute_script,
                    "subscription_instance_id": [sub_inst.id],
                    "subscription_id": common_data.subscription.id,
                    "job_params": {
                        "target_server": {"ip_list": [{"bk_cloud_id": host_obj.bk_cloud_id, "ip": host_obj.inner_ip}]},
                        "script_content": script_content,
                        "script_param": script_param,
                        "timeout": timeout,
                        "os_type": host_obj.os_type,
                    },
                }

        self.run_job_or_finish_schedule(multi_job_params_map)

    def get_script_content(self, data, common_data: CommonData, host: models.Host) -> str:
        """
        获取脚本内容
        :param data:
        :param common_data:
        :param host: 主机对象
        :return: 脚本内容
        """
        return data.get_one_of_inputs("script_content", default="")

    def get_script_param(self, data, common_data: CommonData, host: models.Host) -> str:
        """
        获取脚本参数
        :param data:
        :param common_data:
        :param host: 主机类型
        :return: 脚本参数
        """
        return data.get_one_of_inputs("script_param", default="")


class JobTransferFileService(JobV3BaseService, metaclass=abc.ABCMeta):
    def inputs_format(self):
        return super().inputs_format() + [
            Service.InputItem(name="file_list", key="file_list", type="list", required=False),
            Service.InputItem(name="file_target_path", key="file_target_path", type="str", required=False),
        ]

    def _execute(self, data, parent_data, common_data: CommonData):
        timeout = data.get_one_of_inputs("timeout")
        # 批量请求作业平台的参数
        multi_job_params_map: Dict[str, Dict[str, Any]] = {}
        for sub_inst in common_data.subscription_instances:
            bk_host_id = sub_inst.instance_info["host"]["bk_host_id"]
            host_obj = common_data.host_id_obj_map[bk_host_id]

            file_list = self.get_file_list(data=data, common_data=common_data, host=host_obj)
            file_target_path = self.get_file_target_path(data=data, common_data=common_data, host=host_obj)
            # 如果分发的文件列表 & 目标路径一致，合并到一个作业中，提高执行效率
            md5_key = f"{self.get_md5('|'.join(sorted(file_list)))}-{file_target_path}"

            if md5_key in multi_job_params_map:
                multi_job_params_map[md5_key]["subscription_instance_id"].append(sub_inst.id)
                multi_job_params_map[md5_key]["job_params"]["target_server"]["ip_list"].append(
                    {"bk_cloud_id": host_obj.bk_cloud_id, "ip": host_obj.inner_ip}
                )
            else:
                multi_job_params_map[md5_key] = {
                    "job_func": JobApi.fast_transfer_file,
                    "subscription_instance_id": [sub_inst.id],
                    "subscription_id": common_data.subscription.id,
                    "job_params": {
                        "target_server": {"ip_list": [{"bk_cloud_id": host_obj.bk_cloud_id, "ip": host_obj.inner_ip}]},
                        "file_target_path": file_target_path,
                        "file_source_list": [{"file_list": file_list}],
                        "timeout": timeout,
                        "os_type": host_obj.os_type,
                    },
                }

        self.run_job_or_finish_schedule(multi_job_params_map)

    def get_file_list(self, data, common_data: CommonData, host: models.Host) -> List[str]:
        """
        获取主机所需的文件路径列表
        :param data:
        :param common_data:1
        :param host: 主机对象
        :return: 文件路径列表
        """
        return data.get_one_of_inputs("file_list", default=[])

    def get_file_target_path(self, data, common_data: CommonData, host: models.Host) -> str:
        """
        获取主机所需的文件路径列表
        :param data:
        :param common_data:
        :param host: 主机对象
        :return: 文件路径列表
        """
        return data.get_one_of_inputs("file_target_path", default="")


class JobPushConfigService(JobV3BaseService, metaclass=abc.ABCMeta):
    def inputs_format(self):
        return super().inputs_format() + [
            Service.InputItem(name="config_info_list", key="config_info_list", type="list", required=False),
            Service.InputItem(name="file_target_path", key="file_target_path", type="str", required=False),
        ]

    def cal_job_unique_key(self, config_info_list: List[Dict[str, Any]], file_target_path: str):
        """
        计算分发任务的唯一标识
        如果配置文件名称、MD5、目标路径一致，认为分发内容一致，整合到一个作业中
        :param config_info_list:
        :param file_target_path:
        :return:
        """
        config_unique_keys = []
        for config_info in config_info_list:
            config_unique_keys.append(f"{config_info['file_name']}-{self.get_md5(config_info['content'])}")
        return f"{'-'.join(sorted(config_unique_keys))}-{file_target_path}"

    def _execute(self, data, parent_data, common_data: CommonData):
        timeout = data.get_one_of_inputs("timeout")
        # 批量请求作业平台的参数
        multi_job_params_map: Dict[str, Dict[str, Any]] = {}
        for sub_inst in common_data.subscription_instances:
            bk_host_id = sub_inst.instance_info["host"]["bk_host_id"]
            host_obj = common_data.host_id_obj_map[bk_host_id]

            config_info_list = self.get_config_info_list(data=data, common_data=common_data, host=host_obj)
            file_target_path = self.get_file_target_path(data=data, common_data=common_data, host=host_obj)

            job_unique_key = self.cal_job_unique_key(config_info_list, file_target_path)
            if job_unique_key in multi_job_params_map:
                multi_job_params_map[job_unique_key]["subscription_instance_id"].append(sub_inst.id)
                multi_job_params_map[job_unique_key]["job_params"]["target_server"]["ip_list"].append(
                    {"bk_cloud_id": host_obj.bk_cloud_id, "ip": host_obj.inner_ip}
                )
            else:
                file_source_list = []
                for config_info in config_info_list:
                    file_source_list.append(
                        {"file_name": config_info["file_name"], "content": process_parms(config_info["content"])}
                    )
                multi_job_params_map[job_unique_key] = {
                    "job_func": JobApi.push_config_file,
                    "subscription_instance_id": [sub_inst.id],
                    "subscription_id": common_data.subscription.id,
                    "job_params": {
                        "target_server": {"ip_list": [{"bk_cloud_id": host_obj.bk_cloud_id, "ip": host_obj.inner_ip}]},
                        "file_target_path": file_target_path,
                        "file_list": file_source_list,
                        "timeout": timeout,
                        "os_type": host_obj.os_type,
                    },
                }

        self.run_job_or_finish_schedule(multi_job_params_map)

    def get_config_info_list(self, data, common_data: CommonData, host: models.Host) -> List[Dict[str, Any]]:
        """
        获取主机所需的配置文件信息列表
        :param data:
        :param common_data:
        :param host: 主机对象
        :return: 文件路径列表
        """
        return data.get_one_of_inputs("config_info_list", default=[])

    def get_file_target_path(self, data, common_data: CommonData, host: models.Host) -> str:
        """
        获取主机所需的文件路径列表
        :param data:
        :param common_data:
        :param host: 主机对象
        :return: 文件路径列表
        """
        return data.get_one_of_inputs("", default="")


class JobPushConfigFileComponent(Component):
    name = "JobPushConfigFileComponent"
    code = "job_push_config_file"
    bound_service = JobPushConfigService


class JobFastExecuteScriptComponent(Component):
    name = "JobFastExecuteScriptComponent"
    code = "job_fast_execute_script"
    bound_service = JobExecuteScriptService


class JobFastPushFileComponent(Component):
    name = "JobFastPushFileComponent"
    code = "job_fast_push_file"
    bound_service = JobTransferFileService
