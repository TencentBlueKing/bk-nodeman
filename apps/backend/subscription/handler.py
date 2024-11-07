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

import json
import logging
import random
from collections import Counter, defaultdict
from copy import deepcopy
from typing import Any, Dict, List, Optional, Set, Union

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Max, Q, QuerySet, Value
from django.utils.translation import get_language
from django.utils.translation import ugettext as _

from apps.backend import constants as backend_constants
from apps.backend.subscription import errors, task_tools, tasks, tools
from apps.backend.utils.pipeline_parser import PipelineParser
from apps.backend.utils.redis import REDIS_INST
from apps.core.concurrent import controller
from apps.node_man import constants, models
from apps.utils import concurrent
from apps.utils.basic import filter_values
from apps.utils.redis import RedisDict
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
        need_aggregate_all_tasks: bool = False,
        need_out_of_scope_snapshots: bool = True,
        page: int = None,
        pagesize: int = -1,
        start: int = None,
        exclude_instance_ids: List = [],
        return_all: bool = False,
    ):
        """
        查询任务执行结果
        :param task_id_list: 任务ID列表
        :param instance_id_list: 需过滤的实例ID列表
        :param statuses: 过滤的状态列表
        :param need_detail: 是否需要详情
        :param need_aggregate_all_tasks: 是否需要聚合全部任务查询最后一次视图
        :param need_out_of_scope_snapshots: 是否需要已不在范围内的快照信息
        :param page: 页数
        :param pagesize: 页码
        :param start: 开始位置优先于page使用
        :param exclude_instance_ids: 排除的实例列表
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

        # 如果不需要聚合全部 task，这里需要检查任务是否就绪
        if not need_aggregate_all_tasks:
            # 检查任务是否已准备就绪
            is_ready = self.check_task_ready(task_id_list)
            if not is_ready:
                raise errors.SubscriptionTaskNotReadyError(task_id_list=task_id_list)

        begin, end = None, None
        if pagesize != -1:
            # start参数优先于page作为分页参数
            begin = start - 1 if start is not None else (page - 1) * pagesize
            end = begin + pagesize if start is not None else page * pagesize

        # 先行兼容SaaS跨页全选并返回页结构
        if return_all:
            begin, end = None, None

        base_kwargs: Dict[str, Any] = {"subscription_id": self.subscription_id, "task_id__in": task_id_list}
        if need_aggregate_all_tasks:
            # 如果需要聚合全部业务，这里需要取消过滤任务ID列表
            base_kwargs.pop("task_id__in")

        if not need_out_of_scope_snapshots:
            # 如果不需要已不在订阅范围内的执行快照，查询订阅范围过滤掉移除的实例 ID
            subscription = models.Subscription.objects.get(id=self.subscription_id)
            data_backend = (
                constants.DataBackend.REDIS.value
                if subscription.is_multi_paralle_gateway
                else constants.DataBackend.MEM.value
            )
            scope_instance_id_list: Set[str] = set(
                tools.get_instances_by_scope_with_checker(
                    subscription.scope,
                    subscription.steps,
                    get_cache=True,
                    source="task_result",
                    data_backend=data_backend,
                ).keys()
            )
            base_kwargs["instance_id__in"] = scope_instance_id_list

        is_query_change = False
        filter_kwargs = deepcopy(base_kwargs)

        if instance_id_list is not None:
            is_query_change = True
            if filter_kwargs.get("instance_id__in"):
                filter_kwargs["instance_id__in"] = set(filter_kwargs["instance_id__in"]) & set(instance_id_list)
            else:
                filter_kwargs["instance_id__in"] = instance_id_list

        if statuses is not None:
            is_query_change = True
            filter_kwargs["status__in"] = statuses

        if exclude_instance_ids:
            is_query_change = True

        all_instance_record_ids = SubscriptionTools.fetch_latest_record_ids_in_same_inst_id(
            models.SubscriptionInstanceRecord.objects.filter(**base_kwargs)
        )

        if is_query_change:
            # 附加搜索条件要在聚合之后进行搜索否则会导致搜索结果不正确，聚合之后才是实例的最新记录，需要在最新的记录之上进行搜索
            filter_kwargs["id__in"] = all_instance_record_ids
            filtered_instance_record_ids = list(
                models.SubscriptionInstanceRecord.objects.filter(**filter_kwargs)
                .exclude(instance_id__in=exclude_instance_ids)
                .values_list("id", flat=True)
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
            instance_status_list = task_tools.TaskResultTools.list_subscription_task_instance_status(
                instance_records=instance_records, need_detail=need_detail
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

    def check_task_ready(self, task_id_list: List[int]) -> bool:
        """检查任务是否已经准备好"""
        if not task_id_list:
            latest_task_obj: Optional[models.SubscriptionTask] = (
                models.SubscriptionTask.objects.filter(subscription_id=self.subscription_id)
                .only("id", "is_ready", "err_msg")
                .order_by("-id")
                .first()
            )
            if latest_task_obj:
                task_objs: List[models.SubscriptionTask] = [latest_task_obj]
            else:
                task_objs: List[models.SubscriptionTask] = []
        else:
            task_objs: List[models.SubscriptionTask] = models.SubscriptionTask.objects.filter(
                subscription_id=self.subscription_id, id__in=task_id_list
            ).only("is_ready", "err_msg")

        if not task_objs:
            raise errors.SubscriptionTaskNotExist(
                _(
                    "订阅 -> [{subscription_id}] 对应的订阅任务 -> [{task_id_list}] 不存在".format(
                        subscription_id=self.subscription_id, task_id_list=task_id_list
                    )
                )
            )

        for task in task_objs:
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

        if tools.check_subscription_is_disabled(
            subscription_identity=f"subscription -> [{subscription.id}]",
            scope=subscription.scope,
            steps=subscription.steps,
        ):
            raise errors.SubscriptionIncludeGrayBizError()

        base_filter_kwargs = filter_values(
            {"subscription_id": self.subscription_id, "task_id__in": task_id_list, "instance_id__in": instance_id_list},
            filter_empty=True,
        )

        # 需要排除执行中/执行成功订阅实例 ID
        # 对于指定 task_id_list 的情况，确保需要重试的实例在范围内没有成功过
        exclude_instance_record_qs = models.SubscriptionInstanceRecord.objects.filter(
            **base_filter_kwargs,
            status__in=[
                constants.JobStatusType.RUNNING,
                constants.JobStatusType.PENDING,
                constants.JobStatusType.SUCCESS,
            ],
        )
        # 如果没有按 task_id_list 隔离，并不能简单排除非失败状态，因为在订阅巡检周期内实例存在多次结果不同的快照
        # 在上述情况下，仅需保证需要重试的实例在最新快照没有成功即可
        if not task_id_list:
            exclude_instance_record_qs = exclude_instance_record_qs.filter(is_latest=Value(1))

        exclude_instance_ids: Set[int] = set(exclude_instance_record_qs.values_list("instance_id", flat=True))
        instance_record_qs = models.SubscriptionInstanceRecord.objects.filter(
            Q(**base_filter_kwargs) & ~Q(instance_id__in=exclude_instance_ids)
        )

        # 如果不传重试范围，则查询已失败的任务
        if not instance_id_list:
            instance_record_qs = instance_record_qs.filter(status=constants.JobStatusType.FAILED)

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

        # 以 HOST or SERVICE 为单位重试
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
        tasks.create_task.delay(subscription, subscription_task, instances, instance_actions, language=get_language())
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
            instance_records=[instance_record], need_detail=True
        )
        if not instance_status_list:
            raise errors.SubscriptionInstanceRecordNotExist()

        return instance_status_list[0]

    def run(self, scope: Dict = None, actions: Dict[str, str] = None) -> Dict[str, int]:
        try:
            subscription = models.Subscription.objects.get(id=self.subscription_id)
        except models.Subscription.DoesNotExist:
            raise errors.SubscriptionNotExist({"subscription_id": self.subscription_id})
        if tools.check_subscription_is_disabled(
            subscription_identity=f"subscription -> [{subscription.id}]",
            scope=subscription.scope,
            steps=subscription.steps,
        ):
            raise errors.SubscriptionIncludeGrayBizError()

        if subscription.is_running():
            # 这里仍使用lpush的原因在于订阅任务可能执行的动作不一样，不能使用更新
            name = backend_constants.RUN_SUBSCRIPTION_REDIS_KEY_TPL
            if REDIS_INST.llen(name) > backend_constants.MAX_STORE_SUBSCRIPTION_TASK_COUNT:
                logger.info("redis list store params is full")
                return {
                    "subscription_id": subscription.id,
                    "message": _("该订阅ID下有正在RUNNING的订阅任务，且任务编排数量已达阈值，请稍后再试，如造成不便，请联系管理员处理"),
                }
            params = json.dumps({"subscription_id": subscription.id, "scope": scope, "actions": actions})
            REDIS_INST.lpush(name, params)
            logger.info(f"run subscription[{subscription.id}] store params into redis: {params}")
            return {"subscription_id": subscription.id, "message": _("该订阅ID下有正在RUNNING的订阅任务，已进入任务编排")}

        subscription_task = models.SubscriptionTask.objects.create(
            subscription_id=subscription.id, scope=subscription.scope, actions={}
        )
        if not scope and not actions:
            # 如果不传范围和动作，则自动判断变更
            tasks.run_subscription_task_and_create_instance.delay(
                subscription, subscription_task, language=get_language()
            )
        else:
            # 如果传了scope，那么必须有action
            if not actions:
                raise errors.ActionCanNotBeNone()
            tasks.run_subscription_task_and_create_instance.delay(
                subscription, subscription_task, scope=scope, actions=actions, language=get_language()
            )

        return {"task_id": subscription_task.id, "subscription_id": subscription.id}

    @staticmethod
    def statistic(subscription_id_list: List[int]) -> List[Dict]:
        """
        订阅任务状态统计
        :param subscription_id_list:
        :return:
        """

        cache_keys: List[str] = []
        cache_key_tmpl = settings.CACHE_KEY_TMPL.format(scope="subscription:statistic", body="sub_id:{sub_id}")
        for subscription_id in subscription_id_list:
            cache_keys.append(cache_key_tmpl.format(sub_id=subscription_id))

        # 尝试从缓存中获取统计结果
        hit_sub_statistic_list: List[Dict] = list(cache.get_many(cache_keys).values())
        hit_sub_ids: Set[int] = {hit_sub_statistic["subscription_id"] for hit_sub_statistic in hit_sub_statistic_list}

        logger.info(f"cache_keys -> {cache_keys}, hit_sub_ids -> {hit_sub_ids}")

        miss_sub_ids: Set[int] = set(subscription_id_list) - hit_sub_ids
        if not miss_sub_ids:
            logger.info("All cache hits, return the result directly")
            return hit_sub_statistic_list

        logger.info(f"miss_sub_ids -> {miss_sub_ids}")
        subscriptions = models.Subscription.objects.filter(id__in=miss_sub_ids)

        host_statuses = models.ProcessStatus.objects.filter(
            source_id__in=subscription_id_list, source_type=models.ProcessStatus.SourceType.SUBSCRIPTION
        ).values("version", "group_id", "name", "id")

        instance_host_statuses = defaultdict(dict)
        for host_status in host_statuses:
            instance_host_statuses[host_status["group_id"]][host_status["id"]] = host_status

        subscription_instances = list(
            models.SubscriptionInstanceRecord.objects.filter(
                subscription_id__in=subscription_id_list, is_latest=True
            ).values("subscription_id", "instance_id", "status")
        )
        subscription_instance_status_map = defaultdict(dict)
        for sub_inst in subscription_instances:
            subscription_instance_status_map[sub_inst["subscription_id"]][sub_inst["instance_id"]] = {
                "status": sub_inst["status"]
            }

        sub_statistic_list: List[Dict] = []
        for subscription in subscriptions:
            sub_statistic = {"subscription_id": subscription.id, "status": []}
            data_backend = (
                constants.DataBackend.REDIS.value
                if subscription.is_multi_paralle_gateway
                else constants.DataBackend.MEM.value
            )
            current_instances: Union[RedisDict, dict] = tools.get_instances_by_scope_with_checker(
                subscription.scope, subscription.steps, get_cache=True, source="statistic", data_backend=data_backend
            )

            status_statistic = {"SUCCESS": 0, "PENDING": 0, "FAILED": 0, "RUNNING": 0}
            plugin_versions = defaultdict(lambda: defaultdict(int))
            for instance_id, instance_info in current_instances.items():
                try:
                    group_id = tools.create_group_id(subscription, instance_info)
                except KeyError:
                    # 在订阅变更 node_type & 缓存不一致时可能会发生，极小概率事件，记录堆栈并忽略
                    logger.exception(
                        f"create group id failed: subscription -> {subscription.id}, instance_info -> {instance_info}"
                    )
                    continue

                if group_id not in instance_host_statuses:
                    continue

                if instance_id not in subscription_instance_status_map.get(subscription.id, {}):
                    continue

                sub_instance_status = subscription_instance_status_map[subscription.id][instance_id]

                # 订阅实例任务状态统计
                status_statistic[sub_instance_status["status"]] += 1
                # 版本统计
                host_statuses = instance_host_statuses.get(group_id, {}).values()
                for host_status in host_statuses:
                    plugin_versions[host_status["name"]][host_status["version"]] += 1

            sub_statistic["versions"] = [
                {"version": version, "count": count, "name": name}
                for name, versions in plugin_versions.items()
                for version, count in versions.items()
            ]
            sub_statistic["instances"] = sum(status_statistic.values())
            for status, count in status_statistic.items():
                sub_statistic["status"].append({"status": status, "count": count})

            cache_key = cache_key_tmpl.format(sub_id=subscription.id)
            # 缓存时间范围： 16s ~ 35s
            # 根据数据规模，每增加 1k 缓存增加 1s，最多 15s
            cache_expires: int = 15 * constants.TimeUnit.SECOND + random.randint(
                constants.TimeUnit.SECOND,
                5 * constants.TimeUnit.SECOND
                + min(15 * constants.TimeUnit.SECOND, int(sub_statistic["instances"] / 1000)),
            )
            logger.info(
                f"sub_statistic will be cached: cache_key -> {cache_key}, sub_statistic -> {sub_statistic}, "
                f"instances -> {sub_statistic['instances']}, expires -> {cache_expires}s"
            )
            cache.set(cache_key, sub_statistic, cache_expires)

            sub_statistic_list.append(sub_statistic)

        return sub_statistic_list + hit_sub_statistic_list

    @staticmethod
    @controller.ConcurrentController(
        data_list_name="subscription_id_list",
        batch_call_func=concurrent.batch_call,
        extend_result=True,
        get_config_dict_func=lambda: {"limit": 5},
    )
    def instance_status(subscription_id_list: List[int], show_task_detail: bool) -> List[Dict[str, Any]]:

        subscriptions = models.Subscription.objects.filter(id__in=subscription_id_list)

        # 查出所有HostStatus
        instance_host_statuses = defaultdict(list)
        for host_status in models.ProcessStatus.objects.filter(source_id__in=subscription_id_list).only(
            "name", "status", "version", "group_id"
        ):
            instance_host_statuses[host_status.group_id].append(host_status)

        # 查出所有InstanceRecord
        subscription_instance_record: Dict[int, Dict[str, models.SubscriptionInstanceRecord]] = defaultdict(dict)
        instance_records = []
        for instance_record in models.SubscriptionInstanceRecord.objects.filter(
            subscription_id__in=subscription_id_list, is_latest=Value(1)
        ):
            subscription_instance_record[instance_record.subscription_id][instance_record.instance_id] = instance_record
            instance_records.append(instance_record)

        instance_status_list = task_tools.TaskResultTools.list_subscription_task_instance_status(
            instance_records=instance_records
        )
        instance_status_map = {
            instance_status["instance_id"]: instance_status for instance_status in instance_status_list
        }
        running_records = {}
        # 更新每条record的status字段
        for subscription_id, id_record_map in subscription_instance_record.items():
            for instance_id, record in id_record_map.items():
                # 注入 status 属性。查不到执行记录的，默认设为 PENDING
                record.status = instance_status_map.get(instance_id, {"status": "PENDING"})["status"]
                if record.status in ["PENDING", "RUNNING"]:
                    # 如果实例正在执行，则记下它对应的ID
                    running_records[record.task_id] = record

        # 查出正在运行实例对应的订阅任务，并建立record到task的映射关系
        subscription_tasks = models.SubscriptionTask.objects.filter(id__in=list(running_records.keys())).only(
            "id", "is_auto_trigger"
        )

        record_tasks = {}
        for task in subscription_tasks:
            record = running_records[task.id]
            record_tasks[record.id] = task

        result = []
        for subscription in subscriptions:
            subscription_result = []
            data_backend = (
                constants.DataBackend.REDIS.value
                if subscription.is_multi_paralle_gateway
                else constants.DataBackend.MEM.value
            )
            current_instances: Union[RedisDict, dict] = tools.get_instances_by_scope_with_checker(
                subscription.scope,
                subscription.steps,
                get_cache=True,
                source="instance_status",
                data_backend=data_backend,
            )

            # 对于每个instance，通过group_id找到其对应的host_status
            for instance_id in current_instances:
                if instance_id in subscription_instance_record[subscription.id]:
                    instance_record = subscription_instance_record[subscription.id][instance_id]
                    group_id = tools.create_group_id(subscription, instance_record.instance_info)

                    # 检查该实例是否有正在执行的任务
                    try:
                        related_task = record_tasks[instance_record.id]
                        running_task = {
                            "id": related_task.id,
                            "is_auto_trigger": related_task.is_auto_trigger,
                        }
                    except KeyError:
                        running_task = None

                    instance_result = {
                        "instance_id": instance_id,
                        "status": instance_record.status,
                        "create_time": instance_record.create_time,
                        "host_statuses": [],
                        "instance_info": instance_record.simple_instance_info(),
                        "running_task": running_task,
                        "last_task": {"id": instance_record.task_id},
                    }

                    if show_task_detail:
                        # 展示任务详情
                        instance_status = instance_status_map[instance_id]
                        instance_status.pop("instance_info", None)
                        instance_status.pop("task_id", None)
                        instance_status.pop("instance_id", None)
                        instance_result["last_task"].update(instance_status)

                    for host_status in instance_host_statuses[group_id]:
                        instance_result["host_statuses"].append(
                            {"name": host_status.name, "status": host_status.status, "version": host_status.version}
                        )
                    subscription_result.append(instance_result)
            result.append({"subscription_id": subscription.id, "instances": subscription_result})

        return result

    def clean_subscription(self, execute_actions: Dict[str, str]):
        """
        :param execute_actions: {"bk-beat": "STOP", "exporter": "STOP"}
        """
        try:
            # 3.调用执行订阅的方法
            result = self.run(actions=execute_actions)
        except Exception as e:
            result = {"result": False, "message": str(e)}
        # 4.删除订阅,使用delete()方法才会记录删除时间
        models.Subscription.objects.filter(id=self.subscription_id).delete()
        return result

    @staticmethod
    def update_subscription(params: Dict[str, Any]):
        scope = params["scope"]
        try:
            subscription = models.Subscription.objects.get(id=params["subscription_id"], is_deleted=False)
        except models.Subscription.DoesNotExist:
            raise errors.SubscriptionNotExist({"subscription_id": params["subscription_id"]})
        # 更新订阅不在序列化器中做校验，因为获取更新订阅的类型 step 需要查一次表
        if tools.check_subscription_is_disabled(
            subscription_identity=f"subscription -> [{subscription.id}]",
            steps=subscription.steps,
            scope=scope,
        ):
            raise errors.SubscriptionIncludeGrayBizError()
        if subscription.is_running():
            name = backend_constants.UPDATE_SUBSCRIPTION_REDIS_KEY_TPL
            if REDIS_INST.hlen(name=name) > backend_constants.MAX_STORE_SUBSCRIPTION_TASK_COUNT:
                logger.info("redis hashset store params is full")
                return {
                    "subscription_id": subscription.id,
                    "message": _("该订阅ID下有正在RUNNING的订阅任务，且任务编排数量已达阈值，请稍后再试，如造成不便，请联系管理员处理"),
                }
            REDIS_INST.hset(name, key=f"subscription_id_{subscription.id}", value=json.dumps(params))
            logger.info(f"update subscription[{subscription.id}] store or update params into redis: {params}")
            return {"subscription_id": subscription.id, "message": _("该订阅ID下有正在RUNNING的订阅任务，已进入任务编排")}

        with transaction.atomic():
            subscription.name = params.get("name", "")
            subscription.node_type = scope["node_type"]
            subscription.nodes = scope["nodes"]
            subscription.bk_biz_id = scope.get("bk_biz_id")
            # 避免空列表误判
            if scope.get("instance_selector") is not None:
                subscription.instance_selector = scope["instance_selector"]
            # 策略部署新增
            subscription.plugin_name = params.get("plugin_name")
            subscription.bk_biz_scope = params.get("bk_biz_scope")
            # 指定操作进程用户新增
            if params.get("system_account"):
                params["operate_info"].insert(0, params["system_account"])
            subscription.operate_info = params["operate_info"]
            subscription.save()

            step_ids: Set[str] = set()
            step_id__obj_map: Dict[str, models.SubscriptionStep] = {
                step_obj.step_id: step_obj for step_obj in subscription.steps
            }
            step_objs_to_be_created: List[models.SubscriptionStep] = []
            step_objs_to_be_updated: List[models.SubscriptionStep] = []

            for index, step_info in enumerate(params["steps"]):

                if step_info["id"] in step_id__obj_map:
                    # 存在则更新
                    step_obj: models.SubscriptionStep = step_id__obj_map[step_info["id"]]
                    step_obj.params = step_info["params"]
                    if "config" in step_info:
                        step_obj.config = step_info["config"]
                    step_obj.index = index
                    step_objs_to_be_updated.append(step_obj)
                else:
                    # 新增场景
                    try:
                        step_obj_to_be_created: models.SubscriptionStep = models.SubscriptionStep(
                            subscription_id=subscription.id,
                            index=index,
                            step_id=step_info["id"],
                            type=step_info["type"],
                            config=step_info["config"],
                            params=step_info["params"],
                        )
                    except KeyError as e:
                        logger.warning(
                            f"update subscription[{subscription.id}] to add step[{step_info['id']}] error: "
                            f"err_msg -> {e}"
                        )
                        raise errors.SubscriptionUpdateError(
                            {
                                "subscription_id": subscription.id,
                                "msg": _("新增订阅步骤[{step_id}] 需要提供 type & config，错误信息 -> {err_msg}").format(
                                    step_id=step_info["id"], err_msg=e
                                ),
                            }
                        )
                    step_objs_to_be_created.append(step_obj_to_be_created)
                step_ids.add(step_info["id"])

            # 删除更新后不存在的 step
            models.SubscriptionStep.objects.filter(
                subscription_id=subscription.id, step_id__in=set(step_id__obj_map.keys()) - step_ids
            ).delete()
            models.SubscriptionStep.objects.bulk_update(step_objs_to_be_updated, fields=["config", "params", "index"])
            models.SubscriptionStep.objects.bulk_create(step_objs_to_be_created)
            # 更新 steps 需要移除缓存
            if hasattr(subscription, "_steps"):
                delattr(subscription, "_steps")

        result = {"subscription_id": subscription.id}

        run_immediately = params["run_immediately"]
        if run_immediately:
            subscription_task = models.SubscriptionTask.objects.create(
                subscription_id=subscription.id, scope=subscription.scope, actions={}
            )
            tasks.run_subscription_task_and_create_instance.delay(
                subscription, subscription_task, language=get_language()
            )
            result["task_id"] = subscription_task.id

        return result
