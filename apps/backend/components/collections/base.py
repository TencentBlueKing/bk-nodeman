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
import logging
import os
import traceback
import typing
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)

from django.conf import settings
from django.db.models import Value
from django.db.models.functions import Concat
from django.utils import timezone
from django.utils.translation import ugettext as _

from apps.adapters.api.gse import GseApiBaseHelper, get_gse_api_helper
from apps.backend.api.constants import POLLING_TIMEOUT
from apps.backend.subscription import errors
from apps.core.files.storage import get_storage
from apps.exceptions import parse_exception
from apps.node_man import constants, models
from apps.prometheus import metrics
from apps.prometheus.helper import SetupObserve
from apps.utils import cache, time_handler, translation
from apps.utils.exc import ExceptionHandler
from pipeline.core.flow import Service

logger = logging.getLogger("celery")


class ActivityType:
    HEAD = 0
    TAIL = 1
    HEAD_TAIL = 2


class LogLevel:
    INFO = 0
    WARNING = 1
    ERROR = 2
    DEBUG = 3

    LEVEL_PREFIX_MAP = {INFO: "INFO", WARNING: "WARNING", ERROR: "ERROR", DEBUG: "DEBUG"}


class LogMaker:
    @staticmethod
    def get_log_content(level: int, content: str) -> str:
        return (
            f"[{time_handler.strftime_local(timezone.now())} "
            f"{LogLevel.LEVEL_PREFIX_MAP.get(level, LogLevel.LEVEL_PREFIX_MAP[LogLevel.INFO])}] {content}"
        )

    def error_log(self, content: str) -> str:
        return self.get_log_content(LogLevel.ERROR, content)

    def info_log(self, content: str):
        return self.get_log_content(LogLevel.INFO, content)

    def warning_log(self, content: str):
        return self.get_log_content(LogLevel.WARNING, content)

    def debug_log(self, content: str):
        return self.get_log_content(LogLevel.DEBUG, content)


def service_run_exc_handler(
    wrapped: Callable, instance: "BaseService", args: Tuple[Any], kwargs: Dict[str, Any], exc: Exception
) -> bool:
    if args:
        data = args[0]
    else:
        data = kwargs["data"]

    act_name = data.get_one_of_inputs("act_name")
    sub_inst_ids = instance.get_subscription_instance_ids(data)
    code = instance.__class__.__name__

    metrics.app_task_engine_service_run_exceptions_total.labels(code=code, **parse_exception(exc)).inc()

    logger.exception(f"[task_engine][service_run_exc_handler:{code}] act_name -> {act_name}, exc -> {str(exc)}")

    error_msg = _("{act_name} 失败: {exc}，请先尝试查看错误日志进行处理，若无法解决，请联系管理员处理").format(act_name=act_name, exc=str(exc))
    instance.bulk_set_sub_inst_act_status(
        data=data,
        sub_inst_ids=sub_inst_ids,
        status=constants.JobStatusType.FAILED,
        common_log=instance.log_maker.error_log(error_msg),
    )

    # traceback日志进行折叠
    instance.log_debug(sub_inst_ids=sub_inst_ids, log_content=traceback.format_exc(), fold=True)

    if instance.schedule == wrapped:
        instance.finish_schedule()
    return False


def get_language_func(
    wrapped: Callable, instance: "BaseService", args: Tuple[Any], kwargs: Dict[str, Any]
) -> typing.Optional[str]:
    if args:
        data = args[0]
    else:
        data = kwargs["data"]
    return data.get_one_of_inputs("blueking_language")


def get_labels_func(
    wrapped: Callable, instance: "BaseService", args: Tuple[Any], kwargs: Dict[str, Any]
) -> typing.Dict[str, str]:
    return {"code": instance.__class__.__name__}


class LogMixin:

    # 日志类
    log_maker_class: Type[LogMaker] = LogMaker

    def get_log_maker(self):
        return self.log_maker_class()

    def log_base(
        self, sub_inst_ids: Union[int, List[int], None] = None, log_content: str = None, level: int = LogLevel.INFO
    ):
        """
        记录日志
        :param sub_inst_ids:
        :param log_content:
        :param level:
        :return:
        """
        filters = {"node_id": self.id}
        if sub_inst_ids is None:
            pass
        elif isinstance(sub_inst_ids, int):
            filters["subscription_instance_record_id"] = sub_inst_ids
        else:
            filters["subscription_instance_record_id__in"] = sub_inst_ids

        models.SubscriptionInstanceStatusDetail.objects.filter(**filters).update(
            log=Concat("log", Value(f"\n{self.log_maker.get_log_content(level, log_content)}")),
            update_time=timezone.now(),
        )

    def log_info(self, sub_inst_ids: Union[int, Iterable[int], None] = None, log_content: str = None):
        self.log_base(sub_inst_ids, log_content, level=LogLevel.INFO)

    def log_warning(self, sub_inst_ids: Union[int, Iterable[int], None] = None, log_content: str = None):
        self.log_base(sub_inst_ids, log_content, level=LogLevel.WARNING)

    def log_error(self, sub_inst_ids: Union[int, Iterable[int], None] = None, log_content: str = None):
        self.log_base(sub_inst_ids, log_content, level=LogLevel.ERROR)

    def log_debug(
        self, sub_inst_ids: Union[int, Iterable[int], None] = None, log_content: str = None, fold: bool = False
    ):
        if fold:
            # 背景：前端会识别该模式并折叠文本
            log_content = "{debug_begin}\n{content}\n{debug_end}".format(
                debug_begin=" Begin of collected logs: ".center(40, "*"),
                content=log_content,
                debug_end=" End of collected logs ".center(40, "*"),
            )
        self.log_base(sub_inst_ids, log_content, level=LogLevel.DEBUG)


class DBHelperMixin:
    @property
    @cache.class_member_cache()
    def batch_size(self) -> int:
        """
        获取 update / create 每批次操作数
        批量创建或更新进程状态表，受限于部分MySQL配置的原因，这里 BATCH_SIZE 支持可配置，默认为100
        :return:
        """
        batch_size = models.GlobalSettings.get_config(models.GlobalSettings.KeyEnum.BATCH_SIZE.value, default=100)
        return batch_size

    @property
    @cache.class_member_cache()
    def add_host_cloud_blacklist(self) -> typing.List[int]:
        """
         管控区域新增主机黑名单，用于限制指定管控区域通过安装 Agent 新增主机
        :return:
        """
        add_host_cloud_blacklist: typing.List[int] = models.GlobalSettings.get_config(
            models.GlobalSettings.KeyEnum.ADD_HOST_CLOUD_BLACKLIST.value, default=[]
        )
        return add_host_cloud_blacklist or []

    @property
    @cache.class_member_cache()
    def setup_pagent_file_content(self) -> bytes:
        """
        获取 setup_pagent 文件内容
        :return:
        """
        setup_pagent_filename: str = models.GlobalSettings.get_config(
            models.GlobalSettings.KeyEnum.SETUP_PAGENT_SCRIPT_FILENAME.value,
            constants.SetupScriptFileName.SETUP_PAGENT_PY.value,
        )

        try:
            # 动态从 storage 取，便于进行热修复
            with get_storage().open(os.path.join(settings.DOWNLOAD_PATH, setup_pagent_filename)) as fs:
                return fs.read()
        except Exception:
            # 兜底读取本地文件
            path = os.path.join(settings.BK_SCRIPTS_PATH, setup_pagent_filename)
            with open(path, encoding="utf-8") as fh:
                return fh.read().encode()


class PollingTimeoutMixin:
    @property
    def service_polling_timeout(self) -> int:
        service_name = self.__class__.__name__
        all_service_polling_timeout: dict = models.GlobalSettings.get_config(
            key=models.GlobalSettings.KeyEnum.BACKEND_SERVICE_POLLING_TIMEOUT.value,
            default={},
        )

        service_polling_timeout = all_service_polling_timeout.get(service_name, POLLING_TIMEOUT)
        return service_polling_timeout


@dataclass
class CommonData:
    """
    抽象出通用数据结构体，同于原子执行时常用数据，避免重复编写
    同时这里对类的实例变量进行类型注解，也能避免在调用处重复定义，提高代码编写效率
    """

    bk_host_ids: Set[int]
    host_id_obj_map: Dict[int, models.Host]
    sub_inst_id__host_id_map: Dict[int, int]
    host_id__sub_inst_id_map: Dict[int, int]
    ap_id_obj_map: Dict[int, models.AccessPoint]
    sub_inst_id__sub_inst_obj_map: Dict[int, models.SubscriptionInstanceRecord]
    gse_api_helper: GseApiBaseHelper
    subscription: models.Subscription
    subscription_step: models.SubscriptionStep
    subscription_instances: List[models.SubscriptionInstanceRecord]
    subscription_instance_ids: Set[int]


class BaseService(Service, LogMixin, DBHelperMixin, PollingTimeoutMixin):

    # 失败订阅实例ID - 失败原因 映射关系
    failed_subscription_instance_id_reason_map: Optional[Dict[int, Any]] = None
    # 日志制作类实例
    log_maker: Optional[LogMaker] = None

    def __init__(self, *args, **kwargs):
        self.failed_subscription_instance_id_reason_map: Dict = {}
        self.log_maker = self.get_log_maker()
        super().__init__(*args, **kwargs)

    def move_insts_to_failed(self, sub_inst_ids: Union[List[int], Set[int]], log_content: str = None):
        """
        将实例移动至failed_subscription_instance_id_reason_map，用于子类原子移除异常实例
        :param sub_inst_ids: 订阅实例ID列表/集合
        :param log_content: 异常日志
        """
        for inst_id in sub_inst_ids:
            self.failed_subscription_instance_id_reason_map[inst_id] = log_content
        if log_content:
            self.log_error(sub_inst_ids=sub_inst_ids, log_content=log_content)

    def sub_inst_failed_handler(self, sub_inst_ids: Union[List[int], Set[int]]):
        """
        订阅实例失败处理器
        :param sub_inst_ids: 订阅实例ID列表/集合
        """
        raise NotImplementedError()

    @SetupObserve(histogram=metrics.app_task_engine_set_sub_inst_statuses_duration_seconds)
    def bulk_set_sub_inst_status(self, data, status: str, sub_inst_ids: Union[List[int], Set[int]]):
        """批量设置实例状态，对于实例及原子的状态更新只应该在base内部使用"""
        models.SubscriptionInstanceRecord.objects.filter(id__in=sub_inst_ids).update(
            status=status, update_time=timezone.now()
        )
        # status -> PENDING -> RUNNING -> FAILED | SUCCESS
        metrics.app_task_engine_sub_inst_statuses_total.labels(status=status).inc(len(sub_inst_ids))

        meta: Dict[str, Any] = self.get_meta(data)
        steps: List[Dict] = meta.get("STEPS") or []
        gse_version: str = meta.get("GSE_VERSION") or "unknown"
        for step in steps:
            metrics.app_task_engine_sub_inst_step_statuses_total.labels(
                step_id=step.get("id") or "unknown",
                step_type=step.get("type") or "unknown",
                step_num=len(steps),
                step_index=step.get("index") or 0,
                gse_version=gse_version,
                action=step.get("action") or "unknown",
                code=self.__class__.__name__,
                status=status,
            ).inc(amount=len(sub_inst_ids))

        if status in [constants.JobStatusType.FAILED]:
            self.sub_inst_failed_handler(sub_inst_ids)

    @SetupObserve(histogram=metrics.app_task_engine_set_sub_inst_act_statuses_duration_seconds)
    def bulk_set_sub_inst_act_status(
        self, data, sub_inst_ids: Union[List[int], Set[int]], status: str, common_log: str = None
    ):
        """
        批量设置实例状态
        :param data:
        :param sub_inst_ids:
        :param status:
        :param common_log: 全局日志，用于需要全局暴露的异常
        :return:
        """
        if not sub_inst_ids:
            return
        update_fields = {"status": status}
        if common_log:
            update_fields["log"] = Concat("log", Value(f"\n{common_log}"))
        models.SubscriptionInstanceStatusDetail.objects.filter(
            subscription_instance_record_id__in=sub_inst_ids, node_id=self.id
        ).update(**{**update_fields, "update_time": timezone.now()})

        # 失败的实例需要更新汇总状态
        if status in [constants.JobStatusType.FAILED]:
            self.bulk_set_sub_inst_status(data, constants.JobStatusType.FAILED, sub_inst_ids)

    @staticmethod
    def get_subscription_instance_ids(data):
        subscription_instance_ids = data.get_one_of_inputs("subscription_instance_ids")
        # 优先取上个节点执行成功的订阅实例ID作为要执行的实例
        succeeded_subscription_instance_ids = data.get_one_of_inputs("succeeded_subscription_instance_ids")
        #  "${" 代表该变量未被渲染，直接取 subscription_instance_ids 作为要执行的实例
        if succeeded_subscription_instance_ids and "${" not in succeeded_subscription_instance_ids:
            subscription_instance_ids = succeeded_subscription_instance_ids
        return subscription_instance_ids

    @staticmethod
    def get_meta(data) -> Dict[str, Any]:
        meta: Dict[str, Any] = data.get_one_of_inputs("meta", {})
        if "STEPS" not in meta:
            meta["STEPS"] = []
        return meta

    @staticmethod
    def get_job_meta(data) -> Dict[str, Any]:
        meta: Dict[str, Any] = data.get_one_of_inputs("meta", {})
        scope_id = meta.get("SCOPE_ID", settings.BLUEKING_BIZ_ID)
        scope_type = meta.get("SCOPE_TYPE", constants.BkJobScopeType.BIZ_SET.value)
        return {"bk_biz_id": scope_id, "bk_scope_type": scope_type, "bk_scope_id": scope_id}

    @classmethod
    def get_common_data(cls, data):
        """
        初始化常用数据，注意这些数据不能放在 self 属性里，否则会产生较大的 process snap shot，
        另外也尽量不要在 schedule 中使用，否则多次回调可能引起性能问题
        """
        subscription_instance_ids = BaseService.get_subscription_instance_ids(data)
        subscription_instances = list(
            models.SubscriptionInstanceRecord.objects.filter(id__in=subscription_instance_ids)
        )
        # 同一批执行的任务都源于同一个订阅任务
        subscription = models.Subscription.get_subscription(
            subscription_instances[0].subscription_id, show_deleted=True
        )
        subscription_step_id = data.get_one_of_inputs("subscription_step_id")
        try:
            subscription_step = models.SubscriptionStep.objects.get(id=subscription_step_id)
        except models.SubscriptionStep.DoesNotExist:
            raise errors.SubscriptionStepNotExist({"step_id": subscription_step_id})

        bk_host_ids = set()
        subscription_instance_ids = set()
        sub_inst_id__host_id_map = {}
        host_id__sub_inst_id_map = {}
        sub_inst_id__sub_inst_obj_map = {}
        for subscription_instance in subscription_instances:
            subscription_instance_ids.add(subscription_instance.id)
            # 兼容新安装Agent主机无bk_host_id的场景
            if "bk_host_id" in subscription_instance.instance_info["host"]:
                bk_host_id = subscription_instance.instance_info["host"]["bk_host_id"]
                bk_host_ids.add(bk_host_id)
                sub_inst_id__host_id_map[subscription_instance.id] = bk_host_id
                host_id__sub_inst_id_map[bk_host_id] = subscription_instance.id
                sub_inst_id__sub_inst_obj_map[subscription_instance.id] = subscription_instance

        host_id_obj_map: Dict[int, models.Host] = models.Host.host_id_obj_map(bk_host_id__in=bk_host_ids)
        ap_id_obj_map = models.AccessPoint.ap_id_obj_map()
        return CommonData(
            bk_host_ids=bk_host_ids,
            host_id_obj_map=host_id_obj_map,
            sub_inst_id__host_id_map=sub_inst_id__host_id_map,
            host_id__sub_inst_id_map=host_id__sub_inst_id_map,
            sub_inst_id__sub_inst_obj_map=sub_inst_id__sub_inst_obj_map,
            ap_id_obj_map=ap_id_obj_map,
            gse_api_helper=get_gse_api_helper(gse_version=cls.get_meta(data).get("GSE_VERSION")),
            subscription=subscription,
            subscription_step=subscription_step,
            subscription_instances=subscription_instances,
            subscription_instance_ids=subscription_instance_ids,
        )

    def set_current_id(self, subscription_instance_ids: List[int]):
        # 更新当前实例的pipeline id
        # TODO 偶发死锁
        models.SubscriptionInstanceRecord.objects.filter(id__in=subscription_instance_ids).update(pipeline_id=self.id)

    def set_outputs_data(self, data, common_data: CommonData) -> bool:
        data.outputs.succeeded_subscription_instance_ids = [
            sub_inst_id
            for sub_inst_id in common_data.subscription_instance_ids
            if sub_inst_id not in self.failed_subscription_instance_id_reason_map.keys()
        ]
        # 只要有成功的实例，则认为流程可以继续往下走
        return bool(data.outputs.succeeded_subscription_instance_ids)

    def _execute(self, data, parent_data, common_data: CommonData):
        raise NotImplementedError()

    def _schedule(self, data, parent_data, callback_data=None):
        pass

    def run(self, service_func, data, parent_data, **kwargs) -> bool:

        subscription_instance_ids = BaseService.get_subscription_instance_ids(data)
        act_name = data.get_one_of_inputs("act_name")
        act_type = data.get_one_of_inputs("act_type")
        # 流程起始设置RUNNING
        if service_func == self._execute and act_type in [ActivityType.HEAD, ActivityType.HEAD_TAIL]:
            self.bulk_set_sub_inst_status(data, constants.JobStatusType.RUNNING, subscription_instance_ids)

        service_func(data, parent_data, **kwargs)

        failed_subscription_instance_id_set = set(self.failed_subscription_instance_id_reason_map.keys())
        succeeded_subscription_instance_id_set = set(subscription_instance_ids) - failed_subscription_instance_id_set

        # 处理提前终止的情况
        revoked_subscription_instance_ids = list(
            models.SubscriptionInstanceRecord.objects.filter(
                id__in=succeeded_subscription_instance_id_set, status=constants.JobStatusType.FAILED
            ).values_list("id", flat=True)
        )

        # 更新成功 or 失败的实例状态
        succeeded_subscription_instance_ids = list(
            succeeded_subscription_instance_id_set - set(revoked_subscription_instance_ids)
        )

        self.bulk_set_sub_inst_act_status(
            data=data,
            sub_inst_ids=revoked_subscription_instance_ids,
            status=constants.JobStatusType.FAILED,
            common_log=self.log_maker.warning_log(
                _("{act_name} 已终止，可整体重试/重试。（details: {revoke_sub_inst_id_set}）").format(
                    act_name=act_name, revoke_sub_inst_id_set=revoked_subscription_instance_ids
                )
            ),
        )

        data.inputs.succeeded_subscription_instance_ids = succeeded_subscription_instance_ids
        data.outputs.succeeded_subscription_instance_ids = succeeded_subscription_instance_ids

        # 过滤之前已设置为失败的订阅实例ID
        previous_failed_subscription_instance_id_set = set(
            models.SubscriptionInstanceStatusDetail.objects.filter(
                node_id=self.id,
                status=constants.JobStatusType.FAILED,
                subscription_instance_record_id__in=failed_subscription_instance_id_set,
            ).values_list("subscription_instance_record_id", flat=True)
        )

        # failed_subscription_instance_id_set - sub_inst_ids_previous_failed_set 取差集，仅更新本轮失败的订阅实例详情
        self.bulk_set_sub_inst_act_status(
            data=data,
            sub_inst_ids=failed_subscription_instance_id_set - previous_failed_subscription_instance_id_set,
            status=constants.JobStatusType.FAILED,
            common_log=self.log_maker.error_log(
                _("{act_name} 失败，请先尝试查看日志并处理，若无法解决，请联系管理员处理。").format(act_name=act_name)
            ),
        )

        # 需要进入调度逻辑
        if self.need_schedule() and not self.is_schedule_finished():
            return bool(succeeded_subscription_instance_ids)

        self.bulk_set_sub_inst_act_status(
            data=data,
            sub_inst_ids=succeeded_subscription_instance_ids,
            status=constants.JobStatusType.SUCCESS,
            common_log=self.log_maker.info_log(_("{act_name} 成功").format(act_name=act_name)),
        )

        # 流程结束设置成功的实例
        if act_type in [ActivityType.TAIL, ActivityType.HEAD_TAIL]:
            self.bulk_set_sub_inst_status(
                data, constants.JobStatusType.SUCCESS, sub_inst_ids=succeeded_subscription_instance_ids
            )

        return bool(succeeded_subscription_instance_ids)

    @translation.RespectsLanguage(get_language_func=get_language_func)
    @SetupObserve(
        gauge=metrics.app_task_engine_running_executes_info,
        histogram=metrics.app_task_engine_execute_duration_seconds,
        get_labels_func=get_labels_func,
    )
    @ExceptionHandler(exc_handler=service_run_exc_handler)
    def execute(self, data, parent_data):
        common_data = self.get_common_data(data)
        act_name = data.get_one_of_inputs("act_name")
        act_type = data.get_one_of_inputs("act_type")
        if act_type in [ActivityType.HEAD, ActivityType.HEAD_TAIL]:
            logger.info(
                "[sub_lifecycle<sub(%s), task(%s)>][engine] enter",
                common_data.subscription.id,
                common_data.subscription_instances[0].task_id,
            )

        subscription_instance_ids = self.get_subscription_instance_ids(data)
        to_be_created_sub_statuses = [
            models.SubscriptionInstanceStatusDetail(
                subscription_instance_record_id=sub_inst_id,
                node_id=self.id,
                status=constants.JobStatusType.RUNNING,
                log=self.log_maker.info_log(_("开始 {act_name}.").format(act_name=act_name)),
            )
            for sub_inst_id in subscription_instance_ids
        ]
        models.SubscriptionInstanceStatusDetail.objects.bulk_create(to_be_created_sub_statuses)

        # TODO 鸡肋逻辑，待确认干掉无影响后完全删除
        # self.set_current_id(subscription_instance_ids)
        return self.run(self._execute, data, parent_data, common_data=common_data)

    @translation.RespectsLanguage(get_language_func=get_language_func)
    @SetupObserve(
        gauge=metrics.app_task_engine_running_schedules_info,
        histogram=metrics.app_task_engine_schedule_duration_seconds,
        get_labels_func=get_labels_func,
    )
    @ExceptionHandler(exc_handler=service_run_exc_handler)
    def schedule(self, data, parent_data, callback_data=None):
        return self.run(self._schedule, data, parent_data, callback_data=callback_data)

    def inputs_format(self):
        return [
            Service.InputItem(
                name="subscription_instance_ids", key="subscription_instance_ids", type="list", required=True
            ),
            Service.InputItem(name="subscription_step_id", key="subscription_step_id", type="int", required=True),
            Service.InputItem(name="blueking_language", key="blueking_language", type="str", required=True),
        ]

    def outputs_format(self):
        return [
            Service.OutputItem(
                name="succeeded_subscription_instance_ids",
                key="succeeded_subscription_instance_ids",
                type="list",
                required=True,
            )
        ]
