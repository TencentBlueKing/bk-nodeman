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
import traceback
from functools import wraps
from typing import Dict, List, Set, Union

from django.db.models import F, Value
from django.db.models.functions import Concat
from django.utils import timezone
from django.utils.translation import ugettext as _

from apps.backend.subscription.tools import create_group_id
from apps.node_man import constants, models
from apps.utils.time_handler import strftime_local
from common.log import logger
from pipeline.core.flow import Service


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
            f"[{strftime_local(timezone.now())} "
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


def exception_handler(service_func):
    # 原子执行逻辑最外层异常兜底
    @wraps(service_func)
    def wrapper(self, data, parent_data, *args, **kwargs):
        act_name = data.get_one_of_inputs("act_name")
        sub_inst_ids = self.get_subscription_instance_ids(data)
        try:
            return service_func(self, data, parent_data, *args, **kwargs)
        except Exception as error:
            error_msg = _("{act_name} 失败: {err}，请先尝试查看错误日志进行处理，若无法解决，请联系管理员处理").format(
                act_name=act_name, err=str(error), msg=traceback.format_exc()
            )
            logger.exception(error_msg)
            # 尝试更新实例状态
            self.bulk_set_sub_inst_act_status(
                sub_inst_ids=sub_inst_ids,
                status=constants.JobStatusType.FAILED,
                common_log=self.log_maker.error_log(error_msg),
            )
            # traceback日志进行折叠
            self.log_debug(
                sub_inst_ids=sub_inst_ids,
                log_content="{debug_begin}\n{traceback}\n{debug_end}".format(
                    debug_begin=" Begin of collected logs: ".center(40, "*"),
                    traceback=traceback.format_exc(),
                    debug_end=" End of collected logs ".center(40, "*"),
                ),
            )
            if self.schedule == service_func:
                self.finish_schedule()
            return False

    return wrapper


class LogMixin:
    log_maker_class = LogMaker

    def get_log_maker(self):
        return self.log_maker_class()

    def log_base(
        self, sub_inst_ids: [int, List[int], None] = None, log_content: str = None, level: int = LogLevel.INFO
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

    def log_info(self, sub_inst_ids: [int, List[int], None] = None, log_content: str = None):
        self.log_base(sub_inst_ids, log_content, level=LogLevel.INFO)

    def log_warning(self, sub_inst_ids: [int, List[int], None] = None, log_content: str = None):
        self.log_base(sub_inst_ids, log_content, level=LogLevel.WARNING)

    def log_error(self, sub_inst_ids: [int, List[int], None] = None, log_content: str = None):
        self.log_base(sub_inst_ids, log_content, level=LogLevel.ERROR)

    def log_debug(self, sub_inst_ids: [int, List[int], None] = None, log_content: str = None):
        self.log_base(sub_inst_ids, log_content, level=LogLevel.DEBUG)


class CommonData:
    """
    抽象出通用数据结构体，同于原子执行时常用数据，避免重复编写
    同时这里对类的实例变量进行类型注解，也能避免在调用处重复定义，提高代码编写效率
    """

    def __init__(
        self,
        bk_host_ids: Set[int],
        host_id_obj_map: Dict[int, models.Host],
        ap_id_obj_map: Dict[int, models.AccessPoint],
        subscription: models.Subscription,
        subscription_instances: List[models.SubscriptionInstanceRecord],
        subscription_instance_ids: Set[int],
    ):
        self.bk_host_ids = bk_host_ids
        self.host_id_obj_map = host_id_obj_map
        self.ap_id_obj_map = ap_id_obj_map
        self.subscription = subscription
        self.subscription_instances = subscription_instances
        self.subscription_instance_ids = subscription_instance_ids


class BaseService(Service, LogMixin):
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
        订阅实例失败处理器，主要用于记录日志并把自增重试次数
        :param sub_inst_ids: 订阅实例ID列表/集合
        """
        instance_record_objs = list(models.SubscriptionInstanceRecord.objects.filter(id__in=sub_inst_ids))
        # 同一批实例来自同一订阅
        subscription = models.Subscription.get_subscription(instance_record_objs[0].subscription_id, show_deleted=True)
        group_ids = [
            create_group_id(subscription, inst_record_obj.instance_info) for inst_record_obj in instance_record_objs
        ]
        models.ProcessStatus.objects.filter(source_id=subscription.id, group_id__in=group_ids).update(
            retry_times=F("retry_times") + 1
        )

        logger.info(
            f"subscription_id -> [{subscription.id}], subscription_instance_ids -> {sub_inst_ids}, "
            f"act_id -> {self.id}: 插件部署失败，重试次数 +1"
        )
        self.log_warning(sub_inst_ids=sub_inst_ids, log_content=_("插件部署失败，重试次数 +1"))

    def bulk_set_sub_inst_status(self, status: str, sub_inst_ids: Union[List[int], Set[int]]):
        """批量设置实例状态，对于实例及原子的状态更新只应该在base内部使用"""
        models.SubscriptionInstanceRecord.objects.filter(id__in=sub_inst_ids).update(
            status=status, update_time=timezone.now()
        )
        if status in [constants.JobStatusType.FAILED]:
            self.sub_inst_failed_handler(sub_inst_ids)

    def bulk_set_sub_inst_act_status(
        self, sub_inst_ids: Union[List[int], Set[int]], status: str, common_log: str = None
    ):
        """
        批量设置实例状态
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
            self.bulk_set_sub_inst_status(constants.JobStatusType.FAILED, sub_inst_ids)

    @staticmethod
    def get_subscription_instance_ids(data):
        subscription_instance_ids = data.get_one_of_inputs("subscription_instance_ids")
        # 优先取上个节点执行成功的订阅实例ID作为要执行的实例
        succeeded_subscription_instance_ids = data.get_one_of_inputs("succeeded_subscription_instance_ids")
        #  "${" 代表该变量未被渲染，直接取 subscription_instance_ids 作为要执行的实例
        if succeeded_subscription_instance_ids and "${" not in succeeded_subscription_instance_ids:
            subscription_instance_ids = succeeded_subscription_instance_ids
        return subscription_instance_ids

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
        bk_host_ids = set()
        subscription_instance_ids = set()
        for subscription_instance in subscription_instances:
            bk_host_ids.add(subscription_instance.instance_info["host"]["bk_host_id"])
            subscription_instance_ids.add(subscription_instance.id)

        host_id_obj_map: Dict[int, models.Host] = models.Host.host_id_obj_map(bk_host_id__in=bk_host_ids)
        ap_id_obj_map = models.AccessPoint.ap_id_obj_map()

        return CommonData(
            bk_host_ids, host_id_obj_map, ap_id_obj_map, subscription, subscription_instances, subscription_instance_ids
        )

    def set_current_id(self, subscription_instance_ids: List[int]):
        # 更新当前实例的pipeline id
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
        raise NotImplementedError

    def _schedule(self, data, parent_data, callback_data=None):
        pass

    def run(self, service_func, data, parent_data, **kwargs) -> bool:

        subscription_instance_ids = BaseService.get_subscription_instance_ids(data)
        act_name = data.get_one_of_inputs("act_name")
        act_type = data.get_one_of_inputs("act_type")
        # 流程起始设置RUNNING
        if service_func == self._execute and act_type in [ActivityType.HEAD, ActivityType.HEAD_TAIL]:
            self.bulk_set_sub_inst_status(constants.JobStatusType.RUNNING, subscription_instance_ids)

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
            sub_inst_ids=revoked_subscription_instance_ids,
            status=constants.JobStatusType.FAILED,
            common_log=self.log_maker.warning_log(
                _("{act_name} 已终止，可整体重试/重试。（details: {revoke_sub_inst_id_set}）").format(
                    act_name=act_name, revoke_sub_inst_id_set=revoked_subscription_instance_ids
                )
            ),
        )

        data.outputs.succeeded_subscription_instance_ids = succeeded_subscription_instance_ids

        self.bulk_set_sub_inst_act_status(
            sub_inst_ids=failed_subscription_instance_id_set,
            status=constants.JobStatusType.FAILED,
            common_log=self.log_maker.error_log(
                _("{act_name} 失败，请先尝试查看日志并处理，若无法解决，请联系管理员处理。").format(act_name=act_name)
            ),
        )

        # 需要进入调度逻辑
        if self.need_schedule() and not self.is_schedule_finished():
            return bool(succeeded_subscription_instance_ids)

        self.bulk_set_sub_inst_act_status(
            sub_inst_ids=succeeded_subscription_instance_ids,
            status=constants.JobStatusType.SUCCESS,
            common_log=self.log_maker.info_log(_("{act_name} 成功").format(act_name=act_name)),
        )

        # 流程结束设置成功的实例
        if act_type in [ActivityType.TAIL, ActivityType.HEAD_TAIL]:
            self.bulk_set_sub_inst_status(
                constants.JobStatusType.SUCCESS, sub_inst_ids=succeeded_subscription_instance_ids
            )

        return bool(succeeded_subscription_instance_ids)

    @exception_handler
    def execute(self, data, parent_data):
        common_data = self.get_common_data(data)
        act_name = data.get_one_of_inputs("act_name")
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

        self.set_current_id(subscription_instance_ids)
        return self.run(self._execute, data, parent_data, common_data=common_data)

    @exception_handler
    def schedule(self, data, parent_data, callback_data=None):
        return self.run(self._schedule, data, parent_data, callback_data=callback_data)

    def inputs_format(self):
        return [
            Service.InputItem(
                name="subscription_instance_ids", key="subscription_instance_ids", type="list", required=True
            ),
            Service.InputItem(name="subscription_step_id", key="subscription_step_id", type="int", required=True),
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
