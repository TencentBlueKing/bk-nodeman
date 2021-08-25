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
import copy
import hashlib
import logging
from collections import defaultdict

import six
import ujson as json
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from apps.backend.api.constants import POLLING_INTERVAL, POLLING_TIMEOUT
from apps.backend.api.job import JobClient, process_parms
from apps.backend.components.collections.base import BaseService
from apps.core.files.storage import get_storage
from apps.exceptions import AppBaseException
from apps.node_man import constants
from apps.node_man.models import (
    Host,
    JobSubscriptionInstanceMap,
    SubscriptionInstanceRecord,
)
from apps.utils.batch_request import request_multi_thread
from common.api import JobApi
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service, StaticIntervalGenerator

logger = logging.getLogger("app")


class JobBaseService(six.with_metaclass(abc.ABCMeta, Service)):
    """
    JOB Service 基类
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(POLLING_INTERVAL)

    def _append_log_context(self, msg, log_context):
        prefix = ""
        if isinstance(log_context, dict):
            prefix = ", ".join("{}({})".format(key, value) for key, value in log_context.items())
            prefix += " "
        return prefix + msg

    def log_info(self, msg, log_context=None):
        logger.info(self._append_log_context(msg, log_context))
        self.logger.info(msg)

    def log_error(self, msg, log_context=None):
        logger.error(self._append_log_context(msg, log_context))
        self.logger.error(msg)

    def log_warning(self, msg, log_context=None):
        logger.warning(self._append_log_context(msg, log_context))
        self.logger.warning(msg)

    def log_debug(self, msg, log_context=None):
        logger.debug(self._append_log_context(msg, log_context))
        # self.logger.debug(msg)

    def log_by_task_result(self, job_instance_id, task_result, log_context=None):
        for res in task_result.get("success", []):
            # self.log_info("JOB(task_id: [{}], ip: [{}]) get schedule finished with task result:\n[{}].".format(
            #     job_instance_id,
            #     res['ip'],
            #     res['log_content']),
            #     log_context
            # )
            self.log_info(
                "JOB(task_id: [{}], ip: [{}]) get schedule finished.".format(job_instance_id, res["ip"]),
                log_context,
            )
        for res in task_result.get("failed", []) + task_result.get("pending", []):
            self.log_error(
                "JOB(task_id: [{}], ip: [{}]) get schedule failed with task result:\n[{}].".format(
                    job_instance_id, res["ip"], res["log_content"]
                ),
                log_context,
            )

    @abc.abstractmethod
    def execute(self, data, parent_data):
        raise NotImplementedError()

    def schedule(self, data, parent_data, callback_data=None):
        job_instance_id = data.get_one_of_outputs("job_instance_id")
        job_client = JobClient(**data.get_one_of_inputs("job_client"))
        polling_time = data.get_one_of_outputs("polling_time")
        log_context = data.get_one_of_inputs("context")
        is_finished, task_result = job_client.get_task_result(job_instance_id)
        data.outputs.task_result = task_result
        self.log_debug(
            "JOB(task_id: [{}]) get schedule task result:\n[{}].".format(job_instance_id, json.dumps(task_result)),
            log_context,
        )
        if is_finished:
            self.log_by_task_result(job_instance_id, task_result, log_context)
            self.finish_schedule()
            if task_result["failed"]:
                data.outputs.ex_data = "以下主机JOB任务执行失败：{}".format(
                    ",".join([host["ip"] for host in task_result["failed"]])
                )
                return False
            else:
                return True
        elif polling_time + POLLING_INTERVAL > POLLING_TIMEOUT:
            self.log_error(
                "JOB(job_instance_id: [{}]) schedule timeout.".format(job_instance_id),
                log_context,
            )
            data.outputs.ex_data = "任务轮询超时"
            self.finish_schedule()
            return False

        data.outputs.polling_time = polling_time + POLLING_INTERVAL
        return True


class JobV3BaseService(six.with_metaclass(abc.ABCMeta, BaseService)):
    """
    作业平台V3，基于subscription instance record流转，注意 execute 方法中需要写入 JobSubscriptionInstanceMap
    # 当前 pipeline 引擎中，multi callback schedule 只能串行运行，高并发时存在性能问题
    # TODO 因此这里暂时使用主动查询的方式，后续切换新引擎时可以考虑使用 callback 回调的模式
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(POLLING_INTERVAL)

    @staticmethod
    def get_md5(content):
        md5 = hashlib.md5()
        md5.update(content.encode("utf-8"))
        return md5.hexdigest()

    def request_single_job_and_create_map(
        self, job_func, subscription_instance_id: [int, list], subscription_id, job_params: dict
    ):
        """请求作业平台并创建与订阅实例的映射"""
        if not job_params["target_server"]["ip_list"]:
            # 没有IP列表时，不发起请求
            return []
        # 补充作业平台通用参数
        os_type = constants.OsType.LINUX
        if job_params.get("os_type"):
            os_type = job_params.get("os_type")
        account_alias = (
            settings.BACKEND_WINDOWS_ACCOUNT if os_type == constants.OsType.WINDOWS else settings.BACKEND_UNIX_ACCOUNT
        )
        job_params.update(
            {
                "bk_biz_id": settings.BLUEKING_BIZ_ID,
                "script_language": 2 if os_type == constants.OsType.WINDOWS else 1,
                "script_content": process_parms(job_params.get("script_content", "")),
                "script_param": process_parms(job_params.get("script_param", "")),
                "task_name": f"NODE_MAN_{subscription_id}_{self.__class__.__name__}",
                "account_alias": account_alias,
            }
        )

        if "timeout" not in job_params:
            # 设置默认超时时间
            job_params["timeout"] = 300

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
            JobSubscriptionInstanceMap.objects.create(
                job_instance_id=job_instance_id,
                subscription_instance_ids=subscription_instance_id,
                node_id=self.id,
            )
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
                log = f"快速执行脚本{getattr(self, 'script_name', '')}"
            else:
                log = "调用作业平台"

            self.log_info(
                subscription_instance_id,
                _('{log}，作业任务ID为[{job_instance_id}]，点击跳转到<a href="{link}" target="_blank">[作业平台]</a>').format(
                    log=log,
                    job_instance_id=job_instance_id,
                    link=f"{settings.BK_JOB_HOST}/{settings.BLUEKING_BIZ_ID}/execute/step/{job_instance_id}",
                ),
            )
        return []

    def handler_job_result(self, job_sub_map, cloud_ip_status_map):
        subscription_instances = SubscriptionInstanceRecord.objects.filter(id__in=job_sub_map.subscription_instance_ids)

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
            err_msg = "{ip_status_msg}, {err_msg}".format(
                ip_status_msg=constants.BkJobErrorCode.BK_JOB_ERROR_CODE_MAP.get(ip_status),
                err_msg=constants.BkJobErrorCode.BK_JOB_ERROR_CODE_MAP.get(err_code),
            )
            if ip_status != constants.BkJobIpStatus.SUCCEEDED:
                self.move_insts_to_failed([sub_inst.id], _("作业平台执行失败: {err_msg}").format(err_msg=err_msg))

    def request_get_job_instance_status(self, job_sub_map: JobSubscriptionInstanceMap):
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

    def _schedule(self, data, parent_data, callback_data=None):
        polling_time = data.get_one_of_outputs("polling_time") or 0
        # 查询未完成的作业, 批量查询作业状态并更新DB
        multi_params = [
            {"job_sub_map": job_sub_map}
            for job_sub_map in JobSubscriptionInstanceMap.objects.filter(
                node_id=self.id, status=constants.BkJobStatus.PENDING
            )
        ]
        request_multi_thread(self.request_get_job_instance_status, multi_params)

        # 判断 JobSubscriptionInstanceMap 中对应的 job_instance_id 都执行完成的，把成功的 subscription_instance_ids 向下传递
        is_finished = not JobSubscriptionInstanceMap.objects.filter(
            node_id=self.id, status=constants.BkJobStatus.PENDING
        ).exists()
        if is_finished:
            self.finish_schedule()
        elif polling_time + POLLING_INTERVAL > POLLING_TIMEOUT:
            # 由于JOB的超时机制可能会失效，因此这里节点管理自己需要有超时机制进行兜底
            JobSubscriptionInstanceMap.objects.filter(node_id=self.id, status=constants.BkJobStatus.PENDING).update(
                status=constants.BkJobStatus.FAILED
            )

        data.outputs.polling_time = polling_time + POLLING_INTERVAL


class JobPushConfigFileService(JobBaseService):
    """
    JOB Service 上传配置文件
    """

    def execute(self, data, parent_data):
        job_client = JobClient(**data.get_one_of_inputs("job_client"))
        ip_list = data.get_one_of_inputs("ip_list")
        file_target_path = data.get_one_of_inputs("file_target_path")
        file_list = data.get_one_of_inputs("file_list")
        log_context = data.get_one_of_inputs("context")
        self.log_info(
            "JobPushConfigFileService called with params:\n {}, {}, {}.".format(
                json.dumps(ip_list), file_target_path, json.dumps(file_list)
            ),
            log_context,
        )
        if not all(
            [isinstance(ip_list, list), isinstance(file_target_path, six.string_types), isinstance(file_list, list)]
        ):
            self.log_error("JobPushConfigFileService params checked failed.", log_context)
            data.outputs.ex_data = "参数校验失败"
            return False
        job_instance_id = job_client.push_config_file(ip_list, file_target_path, file_list)
        data.outputs.job_instance_id = job_instance_id
        data.outputs.polling_time = 0
        return True

    def inputs_format(self):
        return [
            Service.InputItem(name="job_client", key="job_client", type="dict", required=True),
            Service.InputItem(name="ip_list", key="ip_list", type="list", required=True),
            Service.InputItem(name="file_target_path", key="file_target_path", type="str", required=True),
            Service.InputItem(name="file_list", key="file_list", type="list", required=True),
        ]

    def outputs_format(self):
        return [
            Service.OutputItem(name="job_instance_id", key="job_instance_id", type="int"),
            Service.OutputItem(name="polling_time", key="polling_time", type="int"),
            Service.OutputItem(name="task_result", key="task_result", type="dict"),
        ]


class JobFastExecuteScriptService(JobBaseService):
    """
    JOB Service 快速执行脚本
    """

    ACTION_NAME = "EXECUTE_SCRIPT"
    ACTION_DESCRIPTION = "执行脚本"

    def execute(self, data, parent_data):
        job_client = JobClient(**data.get_one_of_inputs("job_client"))
        task_id = data.get_one_of_inputs("task_id")
        ip_list = data.get_one_of_inputs("ip_list")
        script_timeout = data.get_one_of_inputs("script_timeout")
        script_content = data.get_one_of_inputs("script_content")
        script_param = data.get_one_of_inputs("script_param")
        log_context = data.get_one_of_inputs("context")
        self.log_info(
            "JobFastExecuteScriptService called for {} with script_params:\n {}.".format(
                json.dumps(ip_list), script_param
            ),
            log_context,
        )
        if not all(
            [
                isinstance(ip_list, list),
                isinstance(script_content, six.string_types),
                isinstance(script_timeout, int),
                isinstance(script_param, six.string_types),
            ]
        ):
            self.log_error("JobFastExecuteScriptService params checked failed.", log_context)
            data.outputs.ex_data = "参数校验失败"
            return False
        job_instance_id = job_client.fast_execute_script(
            ip_list=ip_list,
            script_content=script_content,
            script_param=script_param,
            task_name=f"NODE_MAN_{self.ACTION_NAME}_{task_id}",
            script_timeout=script_timeout,
        )
        data.outputs.job_instance_id = job_instance_id
        data.outputs.polling_time = 0
        return True

    def inputs_format(self):
        return [
            Service.InputItem(name="task_id", key="task_id", type="int", required=False),
            Service.InputItem(name="job_client", key="job_client", type="dict", required=True),
            Service.InputItem(name="ip_list", key="ip_list", type="list", required=True),
            Service.InputItem(name="script_content", key="script_content", type="str", required=True),
            Service.InputItem(name="script_param", key="script_param", type="str", required=True),
            Service.InputItem(name="script_timeout", key="script_timeout", type="int", required=True),
        ]

    def outputs_format(self):
        return [
            Service.OutputItem(name="job_instance_id", key="job_instance_id", type="int"),
            Service.OutputItem(name="polling_time", key="polling_time", type="int"),
            Service.OutputItem(name="task_result", key="task_result", type="dict"),
        ]


class JobFastPushFileService(JobBaseService):
    """
    JOB Service 快速分发文件
    """

    ACTION_NAME = "PUSH_FILE"
    ACTION_DESCRIPTION = "分发文件"

    def execute(self, data, parent_data):
        job_client = JobClient(**data.get_one_of_inputs("job_client"))
        task_id = data.get_one_of_inputs("task_id")
        ip_list = data.get_one_of_inputs("ip_list")
        file_target_path = data.get_one_of_inputs("file_target_path")
        file_source = data.get_one_of_inputs("file_source")
        log_context = data.get_one_of_inputs("context")
        self.log_info(
            "JobFastPushFileService called with params:\n ip_list:{}, file_target_path:{}, file_source:{}.".format(
                json.dumps(ip_list, indent=2), file_target_path, json.dumps(file_source, indent=2)
            ),
            log_context,
        )
        if not all(
            [isinstance(ip_list, list), isinstance(file_target_path, six.string_types), isinstance(file_source, list)]
        ):
            self.log_error("JobFastPushFileService params checked failed.", log_context)
            data.outputs.ex_data = "参数校验失败"
            return False
        job_instance_id = job_client.fast_push_file(
            ip_list=ip_list,
            file_target_path=file_target_path,
            file_source=file_source,
            task_name=f"NODE_MAN_{self.ACTION_NAME}_{task_id}",
        )
        data.outputs.job_instance_id = job_instance_id
        data.outputs.polling_time = 0
        return True

    def inputs_format(self):
        return [
            Service.InputItem(name="task_id", key="task_id", type="int", required=False),
            Service.InputItem(name="job_client", key="job_client", type="dict", required=True),
            Service.InputItem(name="ip_list", key="ip_list", type="list", required=True),
            Service.InputItem(name="file_target_path", key="file_target_path", type="str", required=True),
            Service.InputItem(name="file_source", key="file_source", type="list", required=True),
        ]

    def outputs_format(self):
        return [
            Service.OutputItem(name="job_instance_id", key="job_instance_id", type="int"),
            Service.OutputItem(name="polling_time", key="polling_time", type="int"),
            Service.OutputItem(name="task_result", key="task_result", type="dict"),
        ]


class JobPushMultipleConfigFileService(JobBaseService):
    """
    JOB Service 上传多个配置文件
    """

    def schedule(self, data, parent_data, callback_data=None):
        unfinished_job_instance_ids = data.get_one_of_outputs("unfinished_job_instance_ids")
        job_client = JobClient(**data.get_one_of_inputs("job_client"))
        polling_time = data.get_one_of_outputs("polling_time")
        log_context = data.get_one_of_inputs("context")
        old_task_result = data.get_one_of_outputs("task_result", defaultdict(list))
        finished = set()
        for job_instance_id in unfinished_job_instance_ids:
            is_finished, task_result = job_client.get_task_result(job_instance_id)
            self.log_debug(
                "JOB(job_instance_id: [{}]) get task result: [{}].".format(job_instance_id, json.dumps(task_result)),
                log_context,
            )
            if is_finished:
                self.log_by_task_result(job_instance_id, task_result, log_context)
                finished.add(job_instance_id)
                for k in ("success", "failed", "pending"):
                    old_task_result[k].extend(task_result[k])
                data.outputs.task_result = old_task_result
        unfinished_job_instance_ids -= finished
        if not unfinished_job_instance_ids:
            self.finish_schedule()
            if old_task_result["failed"]:
                return False
            return True
        elif polling_time + POLLING_INTERVAL > POLLING_TIMEOUT:
            self.log_error(
                "JOB(job_instance_ids: [{}]) schedule timeout.".format(json.dumps(unfinished_job_instance_ids)),
                log_context,
            )
            data.outputs.ex_data = "任务轮询超时"
            return False
        data.outputs.unfinished_job_instance_ids = unfinished_job_instance_ids
        data.outputs.polling_time = polling_time + POLLING_INTERVAL
        return True

    def execute(self, data, parent_data):
        job_client = JobClient(**data.get_one_of_inputs("job_client"))
        task_id = data.get_one_of_inputs("task_id")
        ip_list = data.get_one_of_inputs("ip_list")
        file_params = data.get_one_of_inputs("file_params")
        log_context = data.get_one_of_inputs("context")
        if not all([isinstance(ip_list, list), isinstance(file_params, list)]):
            self.log_error("JobPushMultipleConfigFileService params checked failed.", log_context)
            data.outputs.ex_data = "参数校验失败"
            return False
        self.log_info(
            "JobPushMultipleConfigFileService called with params:\n {}, {}.".format(
                json.dumps(ip_list), json.dumps(file_params)
            ),
            log_context,
        )
        job_instance_ids = set()
        for file_param in file_params:
            file_target_path = file_param.get("file_target_path")
            file_list = file_param.get("file_list")
            job_instance_id = job_client.push_config_file(
                ip_list=ip_list,
                file_target_path=file_target_path,
                file_list=file_list,
                task_name=f"NODE_MAN_PUSH_MULTI_CONFIG_FILE_{task_id}",
            )
            job_instance_ids.add(job_instance_id)
        data.outputs.job_instance_ids = job_instance_ids
        data.outputs.unfinished_job_instance_ids = copy.copy(job_instance_ids)
        data.outputs.polling_time = 0
        return True

    def inputs_format(self):
        return [
            Service.InputItem(name="task_id", key="task_id", type="int", required=False),
            Service.InputItem(name="job_client", key="job_client", type="dict", required=True),
            Service.InputItem(name="ip_list", key="ip_list", type="list", required=True),
            Service.InputItem(name="file_params", key="file_params", type="str", required=True),
        ]

    def outputs_format(self):
        return [
            Service.OutputItem(name="job_instance_ids", key="job_instance_id", type="set"),
            Service.OutputItem(name="unfinished_job_instance_ids", key="unfinished_job_instance_ids", type="set"),
            Service.OutputItem(name="polling_time", key="polling_time", type="int"),
            Service.OutputItem(name="task_result", key="task_result", type="dict"),
        ]


class PushFileToProxyService(JobFastPushFileService):
    """
    上传文件到Proxy
    """

    def execute(self, data, parent_data):
        bk_host_id = data.get_one_of_inputs("bk_host_id")
        files = data.get_one_of_inputs("files")
        from_type = data.get_one_of_inputs("from_type")
        self.log_info("正在分发文件到proxy，若长时间未响应，请检查数据传输IP是否正确或网络策略是否开通。")
        if from_type == constants.ProxyFileFromType.AP_CONFIG.value:
            host = Host.get_by_host_info({"bk_host_id": bk_host_id})
            files = host.ap.proxy_package
            if not files:
                self.logger.error(_("上传至Proxy的文件列表为空，请联系节点管理管理员配置接入点信息"))
                return False

        data.inputs.file_source = [{"files": [f"{settings.DOWNLOAD_PATH}/{file}" for file in files]}]

        return super(PushFileToProxyService, self).execute(data, parent_data)

    def inputs_format(self):
        return [
            Service.InputItem(name="task_id", key="task_id", type="int", required=False),
            Service.InputItem(name="job_client", key="job_client", type="dict", required=True),
            Service.InputItem(name="ip_list", key="ip_list", type="list", required=True),
            Service.InputItem(name="file_target_path", key="file_target_path", type="str", required=True),
            Service.InputItem(name="files", key="files", type="list", required=True),
            Service.InputItem(name="from_type", key="from_type", type="str", required=True),
            Service.InputItem(name="bk_host_id", key="bk_host_id", type="int", required=True),
        ]


class JobPushConfigFileComponent(Component):
    name = "JobPushConfigFileComponent"
    code = "job_push_config_file"
    bound_service = JobPushConfigFileService


class JobFastExecuteScriptComponent(Component):
    name = "JobFastExecuteScriptComponent"
    code = "job_fast_execute_script"
    bound_service = JobFastExecuteScriptService


class JobFastPushFileComponent(Component):
    name = "JobFastPushFileComponent"
    code = "job_fast_push_file"
    bound_service = JobFastPushFileService


class JobPushMultipleConfigFileComponent(Component):
    name = "JobPushMultipleConfigFileComponent"
    code = "job_push_multiple_config_file"
    bound_service = JobPushMultipleConfigFileService


class PushFileToProxyComponent(Component):
    name = "PushFileToProxyComponent"
    code = "push_file_to_proxy"
    bound_service = PushFileToProxyService
