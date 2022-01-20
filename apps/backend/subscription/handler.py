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
from __future__ import absolute_import, unicode_literals

import logging
from collections import Counter
from copy import deepcopy
from typing import Any, Dict, List

from django.db.models import Max, QuerySet
from django.utils.translation import ugettext as _

from apps.backend.subscription import errors, task_tools, tasks, tools
from apps.backend.subscription.errors import InstanceTaskIsRunning
from apps.backend.utils.pipeline_parser import PipelineParser
from apps.node_man import constants, models
from apps.utils.basic import filter_values
from pipeline.engine.models import PipelineProcess
from pipeline.service import task_service

logger = logging.getLogger("app")


class SubscriptionTools:
    @classmethod
    def fetch_latest_record_ids_in_same_inst_id(cls, instance_record_qs: QuerySet) -> List[int]:
        """
        筛选当前筛选范围下，同instance_id的最新记录的id列表
        该查询语句的SQL如下：
        SELECT MAX(`id`) AS `id` FROM `node_man_subscriptioninstancerecord` GROUP BY `instance_id`
        last record in each group 问题， 查找最新记录需要联表或子查询，考虑多个地方仅用到id列表，在此仅返回id列表
        不要试图在.values("instance_id").annotate(id=Max("id"))后添加任何查询，查询其他字段值不一定属于max(id)
        参考：https://stackoverflow.com/questions/1313120/retrieving-the-last-record-in-each-group-mysql
        :param instance_record_qs:
        :return:
        """
        return list(instance_record_qs.values("instance_id").annotate(id=Max("id")).values_list("id", flat=True))


class SubscriptionHandler(object):
    def __init__(self, subscription_id: int):
        self.subscription_id = subscription_id

    def task_result(
        self,
        task_id_list: List = None,
        statuses: List = None,
        instance_id_list: List = None,
        need_detail: bool = False,
        page: int = None,
        pagesize: int = -1,
        return_all: bool = False,
    ):
        """
        查询任务执行结果
        :param task_id_list: 任务ID列表
        :param instance_id_list: 需过滤的实例ID列表
        :param statuses: 过滤的状态列表
        :param need_detail: 是否需要详情
        :param page: 页数
        :param pagesize: 页码
        :param return_all: 是否返回全量（用于兼容老接口）
        :return:
        """

        if task_id_list:
            # 如果有task_id_list则查出订阅下的这些任务，新任务的instance记录会覆盖旧的
            task_id_list = set(task_id_list)
            subscription_tasks = models.SubscriptionTask.objects.filter(
                subscription_id=self.subscription_id, id__in=task_id_list
            ).values("id", "pipeline_id")

            current_task_id_list = {task["id"] for task in subscription_tasks}
            if current_task_id_list != task_id_list:
                raise errors.SubscriptionTaskNotExist({"task_id": list(task_id_list - current_task_id_list)})
        else:
            # 如果没传task_id则查询最近一次任务
            subscription_tasks = models.SubscriptionTask.objects.filter(subscription_id=self.subscription_id)[
                0:1
            ].values("id", "pipeline_id")

            if not subscription_tasks:
                raise errors.SubscriptionTaskNotExist(
                    _("订阅[{subscription_id}] 不存在关联的任务".format(subscription_id=self.subscription_id))
                )
            task_id_list = [subscription_tasks[0]["id"]]

        id__task_map = {task["id"]: task for task in subscription_tasks}

        # 检查任务是否已准备就绪
        is_ready = self.check_task_ready(task_id_list)
        if not is_ready:
            raise errors.SubscriptionTaskNotReadyError(task_id_list=task_id_list)

        begin, end = None, None
        if pagesize != -1:
            begin = (page - 1) * pagesize
            end = page * pagesize

        # 先行兼容SaaS跨页全选并返回页结构
        if return_all:
            begin, end = None, None

        base_kwargs = {"subscription_id": self.subscription_id, "task_id__in": task_id_list}
        filter_kwargs = deepcopy(base_kwargs)
        is_query_change = False

        if instance_id_list is not None:
            is_query_change = True
            filter_kwargs["instance_id__in"] = instance_id_list
        if statuses is not None:
            is_query_change = True
            filter_kwargs["status__in"] = statuses

        all_instance_record_ids = SubscriptionTools.fetch_latest_record_ids_in_same_inst_id(
            models.SubscriptionInstanceRecord.objects.filter(**base_kwargs)
        )

        if is_query_change:
            # 附加搜索条件要在聚合之后进行搜索否则会导致搜索结果不正确，聚合之后才是实例的最新记录，需要在最新的记录之上进行搜索
            filter_kwargs["id__in"] = all_instance_record_ids
            filtered_instance_record_ids = list(
                models.SubscriptionInstanceRecord.objects.filter(**filter_kwargs).values_list("id", flat=True)
            )
        else:
            filtered_instance_record_ids = all_instance_record_ids

        # 查询这些任务下的全部最新instance记录
        instance_records = models.SubscriptionInstanceRecord.objects.filter(
            id__in=sorted(filtered_instance_record_ids)[begin:end]
        )
        instance_records = sorted(instance_records, key=lambda record: -record.id)

        if not instance_records and (pagesize == -1 and not return_all):
            return []

        if not instance_records:
            instance_status_list = []
        else:
            # 用 subscription_task 是否有pipeline_id字段作为新老记录的区别，要么是新的要么是旧的，不存在混合的情况
            is_new_task = id__task_map[instance_records[0].task_id]["pipeline_id"]
            if is_new_task:
                instance_status_list = task_tools.TaskResultTools.list_subscription_task_instance_status(
                    instance_records, need_detail=need_detail
                )
            else:
                instance_status_list = []
                inst_infos_parse_error = []
                pipeline_parser = PipelineParser([r.pipeline_id for r in instance_records])
                for instance_record in instance_records:
                    try:
                        instance_status_list.append(
                            tools.get_subscription_task_instance_status(instance_record, pipeline_parser, need_detail)
                        )
                    except errors.PipelineTreeParseError:
                        inst_infos_parse_error.append(
                            {"id": instance_record.id, "pipeline_id": instance_record.pipeline_id}
                        )
                if inst_infos_parse_error:
                    logger.error(
                        f"subscription_id -> {self.subscription_id}, inst_infos_parse_error -> {inst_infos_parse_error}"
                    )

        # 兼容第三方平台全部拉取，无需返回状态统计
        if pagesize == -1 and not return_all:
            return instance_status_list

        # 显示订阅全局的状态统计
        status_counter = dict(
            Counter(
                models.SubscriptionInstanceRecord.objects.filter(
                    subscription_id=self.subscription_id, id__in=all_instance_record_ids
                ).values_list("status", flat=True)
            )
        )
        status_counter["total"] = sum(list(status_counter.values()))
        return {
            "total": len(filtered_instance_record_ids),
            "list": instance_status_list,
            "status_counter": status_counter,
        }

    def check_task_ready(self, task_id_list) -> bool:
        """检查任务是否已经准备好"""
        for task in models.SubscriptionTask.objects.filter(
            subscription_id=self.subscription_id, id__in=task_id_list
        ).only("is_ready", "err_msg"):
            if not task.is_ready:
                # 任务未就绪且已写入错误日志，认为任务已创建失败，需抛出异常
                if task.err_msg:
                    raise errors.CreateSubscriptionTaskError(err_msg=task.err_msg)
                return False
        return True

    def get_running_instance_records(self, instance_id_list):
        # 如果不传终止范围，则查询正在执行中的任务
        if not instance_id_list:
            instance_records = models.SubscriptionInstanceRecord.objects.filter(
                subscription_id=self.subscription_id,
                status__in=[constants.JobStatusType.PENDING, constants.JobStatusType.RUNNING],
                is_latest=True,
            ).values("pipeline_id", "id")
        else:
            instance_records = models.SubscriptionInstanceRecord.objects.filter(
                subscription_id=self.subscription_id, instance_id__in=instance_id_list, is_latest=True
            ).values("pipeline_id", "id")

        if instance_records:
            return instance_records
        else:
            # 没有运行中的记录
            raise errors.NoRunningInstanceRecordError(subscription_id=self.subscription_id)

    @staticmethod
    def force_fail_and_revoke_pipeline(pipeline_ids: List[str]):
        """强制失败或撤回pipeline"""
        for process in PipelineProcess.objects.filter(root_pipeline_id__in=pipeline_ids):
            task_service.forced_fail(process.current_node_id)
        for pipeline_id in pipeline_ids:
            task_service.revoke_pipeline(pipeline_id)

    def revoke(self, instance_id_list: List = None):
        instance_records = self.get_running_instance_records(instance_id_list)

        subscription_task: models.SubscriptionTask = (
            models.SubscriptionTask.objects.filter(subscription_id=self.subscription_id).order_by("-id").first()
        )

        if not subscription_task:
            raise errors.SubscriptionTaskNotExist(f"订阅[{self.subscription_id}]不存在订阅任务")

        # pipeline_id为空视为旧任务或Agent安装任务
        if not subscription_task.pipeline_id:
            pipeline_ids = [instance_record["pipeline_id"] for instance_record in instance_records]
            self.force_fail_and_revoke_pipeline(pipeline_ids)
            return

        # 提前失败
        instance_record_ids = [instance_record["id"] for instance_record in instance_records]
        models.SubscriptionInstanceRecord.objects.filter(id__in=instance_record_ids).update(
            status=constants.JobStatusType.FAILED
        )
        # 延迟双更，避免终止前订阅实例状态被base覆盖
        tasks.set_record_status.delay(
            instance_record_ids=instance_record_ids, status=constants.JobStatusType.FAILED, delay_seconds=1
        )

    def retry(
        self, task_id_list: List[int] = None, instance_id_list: List[str] = None, actions: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        重试任务
        :param task_id_list: 任务ID列表，在SaaS侧该值必传
            - 用于保证巡检后is_latest=False的实例可以重试
            - 指定重试范围，隔离同策略(订阅)不同Job的重试功能，例如job1用于停用，job2用于部署，通过task_id_list可以有效隔离actions
        :param instance_id_list: 实例ID列表
        :param actions: 插件-动作映射, eg: {"bkmonitorlog": "INSTALL"}
        :return:
        """

        try:
            subscription = models.Subscription.objects.get(id=self.subscription_id)
        except models.Subscription.DoesNotExist:
            raise errors.SubscriptionNotExist({"subscription_id": self.subscription_id})

        base_filter_kwargs = filter_values(
            {"subscription_id": self.subscription_id, "task_id__in": task_id_list, "instance_id__in": instance_id_list},
            filter_empty=True,
        )

        # 如果不传重试范围，则查询已失败的任务
        if not instance_id_list:
            instance_record_qs = models.SubscriptionInstanceRecord.objects.filter(
                **{"status": constants.JobStatusType.FAILED, **base_filter_kwargs}
            )
        else:
            instance_record_qs = models.SubscriptionInstanceRecord.objects.filter(**base_filter_kwargs)

        instance_record_ids = SubscriptionTools.fetch_latest_record_ids_in_same_inst_id(instance_record_qs)
        instance_records = models.SubscriptionInstanceRecord.objects.filter(id__in=instance_record_ids).values(
            "id", "instance_id", "instance_info"
        )

        if not instance_records:
            raise errors.SubscriptionInstanceRecordNotExist(f"订阅任务 -> {self.subscription_id} 不存在失败任务")

        # 一批任务中object_type / node_type 一致
        first_node = tools.parse_node_id(instance_records[0]["instance_id"])
        scope = deepcopy(subscription.scope)
        scope.update({"object_type": first_node["object_type"], "node_type": first_node["node_type"], "nodes": []})

        # 以HOST or SERVICE 为单位重试
        instances = {}
        for instance_record in instance_records:
            instances[instance_record["instance_id"]] = instance_record["instance_info"]
        if not actions:
            # 如果没有传入actions，则以最近一次任务的action执行
            instance_actions_list = (
                models.SubscriptionTask.objects.filter(
                    **filter_values(
                        {"subscription_id": self.subscription_id, "id__in": task_id_list}, filter_empty=True
                    )
                )
                .order_by("id")
                .values_list("actions", flat=True)
            )

            instance_actions = {}
            for task_instance_actions in instance_actions_list:
                # task_instance_actions以task_id升序进行遍历，不断覆盖同instance_id下旧task的action，从而得到最新
                instance_actions.update(task_instance_actions)
            if not instance_actions:
                raise errors.SubscriptionTaskNotExist("无法获取订阅任务最新的instance_actions，请尝试显式传入actions")
        else:
            instance_actions = {instance_record["instance_id"]: actions for instance_record in instance_records}

        logger.info(f"[/subscription/retry/] retry instances={instances}")

        instance_actions = {
            instance_id: instance_actions[instance_id] for instance_id in instances if instance_id in instance_actions
        }

        subscription_task = models.SubscriptionTask.objects.create(
            subscription_id=subscription.id, scope=subscription.scope, actions={}
        )
        tasks.create_task.delay(subscription, subscription_task, instances, instance_actions)
        return {"task_id": subscription_task.id}

    def task_result_detail(self, instance_id: str, task_id_list: List[int] = None) -> Dict:

        filter_kwargs = filter_values(
            {"subscription_id": self.subscription_id, "task_id__in": task_id_list, "instance_id": instance_id},
            filter_empty=True,
        )

        # 选取指定 subscription_id & task_id_list范围下最新的instance_record
        instance_record = models.SubscriptionInstanceRecord.objects.filter(**filter_kwargs).order_by("-id").first()

        if not instance_record:
            raise errors.SubscriptionInstanceRecordNotExist()

        # 兼容Agent任务通过改造前逻辑获取任务状态
        if not instance_record.subscription_task.pipeline_id:
            pipeline_parser = PipelineParser([instance_record.pipeline_id])
            instance_status = tools.get_subscription_task_instance_status(
                instance_record, pipeline_parser, need_detail=True
            )
            return instance_status

        instance_status_list = task_tools.TaskResultTools.list_subscription_task_instance_status(
            [instance_record], need_detail=True
        )
        if not instance_status_list:
            raise errors.SubscriptionInstanceRecordNotExist()

        return instance_status_list[0]

    def run(self, scope: Dict = None, actions: Dict[str, str] = None) -> Dict[str, int]:
        try:
            subscription = models.Subscription.objects.get(id=self.subscription_id)
        except models.Subscription.DoesNotExist:
            raise errors.SubscriptionNotExist({"subscription_id": self.subscription_id})

        if subscription.is_running():
            raise InstanceTaskIsRunning()
        subscription_task = models.SubscriptionTask.objects.create(
            subscription_id=subscription.id, scope=subscription.scope, actions={}
        )
        if not scope and not actions:
            # 如果不传范围和动作，则自动判断变更
            tasks.run_subscription_task_and_create_instance.delay(subscription, subscription_task)
        else:
            # 如果传了scope，那么必须有action
            if not actions:
                raise errors.ActionCanNotBeNone()
            tasks.run_subscription_task_and_create_instance.delay(
                subscription, subscription_task, scope=scope, actions=actions
            )

        return {"task_id": subscription_task.id, "subscription_id": subscription.id}
