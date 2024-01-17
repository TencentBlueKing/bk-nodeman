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
import operator
from collections import defaultdict
from dataclasses import asdict
from functools import cmp_to_key, reduce
from typing import Any, Dict, List, Set

from django.core.cache import caches
from django.db import transaction
from django.db.models import Q
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.backend.agent.tasks import collect_log
from apps.backend.agent.tools import gen_commands
from apps.backend.constants import SubscriptionSwithBizAction
from apps.backend.serializers import response
from apps.backend.subscription import errors, serializers, task_tools, tasks, tools
from apps.backend.subscription.errors import InstanceTaskIsRunning
from apps.backend.subscription.handler import SubscriptionHandler
from apps.backend.subscription.steps.agent_adapter.adapter import AgentStepAdapter
from apps.backend.subscription.steps.agent_adapter.base import AgentSetupInfo
from apps.backend.utils.pipeline_parser import PipelineParser
from apps.core.script_manage.handlers import ScriptManageHandler
from apps.generic import APIViewSet
from apps.node_man import constants, models
from apps.utils import basic

logger = logging.getLogger("app")
cache = caches["db"]

SUBSCRIPTION_VIEW_TAGS = ["subscription"]


class SubscriptionViewSet(APIViewSet):
    queryset = ""
    # permission_classes = (BackendBasePermission,)

    @swagger_auto_schema(
        operation_summary="创建订阅",
        responses={status.HTTP_200_OK: response.CreateResponseSerializer()},
        tags=SUBSCRIPTION_VIEW_TAGS,
    )
    @action(
        detail=False, methods=["POST"], url_path="create", serializer_class=serializers.CreateSubscriptionSerializer
    )
    def create_subscription(self, request):
        """
        @api {POST} /subscription/create/ 创建订阅
        @apiName create_subscription
        @apiGroup subscription
        """
        params = self.validated_data
        scope = params["scope"]
        run_immediately = params["run_immediately"]

        category = params.get("category")
        enable = params.get("enable") or False
        if category == models.Subscription.CategoryType.POLICY:
            # 策略类型订阅默认开启
            enable = True

        with transaction.atomic():
            # 创建订阅
            subscription = models.Subscription.objects.create(
                name=params.get("name", ""),
                bk_biz_id=scope["bk_biz_id"],
                object_type=scope["object_type"],
                node_type=scope["node_type"],
                nodes=scope["nodes"],
                instance_selector=scope.get("instance_selector"),
                target_hosts=params.get("target_hosts"),
                from_system=params["bk_app_code"] or "blueking",
                enable=enable,
                is_main=params.get("is_main", False),
                creator=params["bk_username"],
                # 策略部署新增
                bk_biz_scope=params.get("bk_biz_scope", []),
                category=params.get("category"),
                plugin_name=params.get("plugin_name"),
                pid=params.get("pid", models.Subscription.ROOT),
            )

            # 创建订阅步骤
            steps = params["steps"]
            for index, step in enumerate(steps):
                models.SubscriptionStep.objects.create(
                    subscription_id=subscription.id,
                    index=index,
                    step_id=step["id"],
                    type=step["type"],
                    config=step["config"],
                    params=step["params"],
                )

            result = {
                "subscription_id": subscription.id,
            }

        if run_immediately:
            if subscription.is_running():
                raise InstanceTaskIsRunning()

            subscription_task = models.SubscriptionTask.objects.create(
                subscription_id=subscription.id, scope=subscription.scope, actions={}
            )
            tasks.run_subscription_task_and_create_instance.delay(
                subscription, subscription_task, language=get_language()
            )
            result["task_id"] = subscription_task.id

        return Response(result)

    @swagger_auto_schema(
        operation_summary="订阅详情",
        responses={status.HTTP_200_OK: response.InfoResponseSerializer()},
        tags=SUBSCRIPTION_VIEW_TAGS,
    )
    @action(detail=False, methods=["POST"], serializer_class=serializers.GetSubscriptionSerializer)
    def info(self, request):
        """
        @api {POST} /subscription/info/ 订阅详情
        @apiName subscription_info
        @apiGroup subscription
        """
        params = self.validated_data
        ids = params["subscription_id_list"]
        subscriptions = models.Subscription.get_subscriptions(ids, show_deleted=params["show_deleted"])

        result = []
        for subscription in subscriptions:
            info = {
                "id": subscription.id,
                "name": subscription.name,
                "enable": subscription.enable,
                "category": subscription.category,
                "plugin_name": subscription.plugin_name,
                "bk_biz_scope": subscription.bk_biz_scope,
                "scope": {
                    "bk_biz_id": subscription.bk_biz_id,
                    "object_type": subscription.object_type,
                    "node_type": subscription.node_type,
                    "nodes": subscription.nodes,
                },
                "pid": subscription.pid,
                "target_hosts": subscription.target_hosts,
                "steps": [],
            }

            for step in subscription.steps:
                info["steps"].append(
                    {"id": step.step_id, "type": step.type, "config": step.config, "params": step.params}
                )

            result.append(info)

        return Response(result)

    @swagger_auto_schema(
        operation_summary="更新订阅",
        responses={status.HTTP_200_OK: response.UpdateResponseSerializer()},
        tags=SUBSCRIPTION_VIEW_TAGS,
    )
    @action(
        detail=False, methods=["POST"], url_path="update", serializer_class=serializers.UpdateSubscriptionSerializer
    )
    def update_subscription(self, request):
        """
        @api {POST} /subscription/update/ 更新订阅
        @apiName update_subscription
        @apiGroup subscription
        """
        params = self.validated_data
        scope = params["scope"]
        run_immediately = params["run_immediately"]
        with transaction.atomic():
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

        if run_immediately:
            if subscription.is_running():
                raise InstanceTaskIsRunning()

            subscription_task = models.SubscriptionTask.objects.create(
                subscription_id=subscription.id, scope=subscription.scope, actions={}
            )
            tasks.run_subscription_task_and_create_instance.delay(
                subscription, subscription_task, language=get_language()
            )
            result["task_id"] = subscription_task.id

        return Response(result)

    @swagger_auto_schema(
        operation_summary="删除订阅",
        responses={status.HTTP_200_OK: response.DeleteResponseSerializer()},
        tags=SUBSCRIPTION_VIEW_TAGS,
    )
    @action(
        detail=False, methods=["POST"], url_path="delete", serializer_class=serializers.DeleteSubscriptionSerializer
    )
    def delete_subscription(self, request):
        """
        @api {POST} /subscription/delete/ 删除订阅
        @apiName delete_subscription
        @apiGroup subscription
        """
        params = self.validated_data
        try:
            subscription = models.Subscription.objects.get(id=params["subscription_id"], is_deleted=False)
        except models.Subscription.DoesNotExist:
            raise errors.SubscriptionNotExist({"subscription_id": params["subscription_id"]})
        subscription.is_deleted = True
        subscription.save()
        return Response()

    @swagger_auto_schema(
        operation_summary="执行订阅",
        responses={status.HTTP_200_OK: response.RunResponseSerializer()},
        tags=SUBSCRIPTION_VIEW_TAGS,
    )
    @action(detail=False, methods=["POST"], serializer_class=serializers.RunSubscriptionSerializer)
    def run(self, request):
        """
        @api {POST} /subscription/run/ 执行订阅
        @apiName run_subscription
        @apiGroup subscription
        """
        params = self.validated_data

        return Response(
            SubscriptionHandler(params["subscription_id"]).run(scope=params.get("scope"), actions=params.get("actions"))
        )

    @swagger_auto_schema(operation_summary="查询任务是否已准备完成", tags=SUBSCRIPTION_VIEW_TAGS, methods=["GET", "POST"])
    @action(detail=False, methods=["GET", "POST"], serializer_class=serializers.CheckTaskReadySerializer)
    def check_task_ready(self, request):
        """
        @api {POST} /subscription/check_task_ready/ 查询任务是否已准备完成
        @apiName subscription_check_task_ready
        @apiGroup subscription
        """
        params = self.validated_data
        subscription_id = params["subscription_id"]
        task_result = SubscriptionHandler(subscription_id=subscription_id).check_task_ready(
            task_id_list=params.get("task_id_list", [])
        )
        return Response(task_result)

    @swagger_auto_schema(
        operation_summary="任务执行结果",
        responses={status.HTTP_200_OK: response.TaskResultResponseSerializer()},
        tags=SUBSCRIPTION_VIEW_TAGS,
        methods=["GET", "POST"],
    )
    @action(detail=False, methods=["GET", "POST"], serializer_class=serializers.TaskResultSerializer)
    def task_result(self, request):
        """
        @api {POST} /subscription/task_result/ 任务执行结果
        @apiName subscription_task_result
        @apiGroup subscription
        """
        params = self.validated_data
        subscription_id = params["subscription_id"]
        task_result = SubscriptionHandler(subscription_id=subscription_id).task_result(
            task_id_list=params.get("task_id_list"),
            statuses=params.get("statuses"),
            instance_id_list=params.get("instance_id_list"),
            need_detail=params["need_detail"],
            need_aggregate_all_tasks=params["need_aggregate_all_tasks"],
            need_out_of_scope_snapshots=params["need_out_of_scope_snapshots"],
            page=params["page"],
            pagesize=params["pagesize"],
            start=params.get("start"),
            exclude_instance_ids=params["exclude_instance_ids"],
            return_all=params["return_all"],
        )
        return Response(task_result)

    @swagger_auto_schema(
        operation_summary="任务执行详细结果",
        tags=SUBSCRIPTION_VIEW_TAGS,
        methods=["GET", "POST"],
    )
    @action(detail=False, methods=["GET", "POST"], serializer_class=serializers.TaskResultDetailSerializer)
    def task_result_detail(self, request):
        """
        @api {POST} /subscription/task_result_detail/ 任务执行详细结果
        @apiName subscription_task_result_detail
        @apiGroup subscription
        """
        params = self.validated_data

        task_id_list = params.get("task_id_list", [])
        task_id = params.get("task_id")
        if task_id:
            task_id_list.append(task_id)

        return Response(
            SubscriptionHandler(params["subscription_id"]).task_result_detail(params["instance_id"], task_id_list)
        )

    @swagger_auto_schema(operation_summary="采集任务执行详细结果", tags=SUBSCRIPTION_VIEW_TAGS)
    @action(detail=False, methods=["POST"])
    def collect_task_result_detail(self, request):
        """
        @api {POST} /subscription/collect_task_result_detail/ 采集任务执行详细结果
        @apiName collect_subscription_task_result_detail
        @apiGroup subscription
        """
        job_id = self.request.data.get("job_id")
        instance_id = self.request.data.get("instance_id")
        try:
            job_task = models.JobTask.objects.get(job_id=job_id, instance_id=instance_id)
        except models.JobTask.DoesNotExist:
            return Response({"celery_id": -1})
        res = collect_log.delay(job_task.bk_host_id, job_task.pipeline_id)
        return Response({"celery_id": res.id})

    @swagger_auto_schema(operation_summary="统计订阅任务数据", tags=SUBSCRIPTION_VIEW_TAGS)
    @action(detail=False, methods=["POST"], serializer_class=serializers.SubscriptionStatisticSerializer)
    def statistic(self, request):
        """
        @api {POST} /subscription/statistic/ 统计订阅任务数据
        @apiName statistic
        @apiGroup subscription
        """
        params = self.validated_data
        subscription_id_list = params["subscription_id_list"]
        return Response(SubscriptionHandler.statistic(subscription_id_list))

    @swagger_auto_schema(
        operation_summary="查询订阅运行状态",
        responses={status.HTTP_200_OK: response.InstanceStatusResponseSerializer()},
        tags=SUBSCRIPTION_VIEW_TAGS,
        methods=["GET", "POST"],
    )
    @action(detail=False, methods=["GET", "POST"], serializer_class=serializers.InstanceHostStatusSerializer)
    def instance_status(self, request):
        """
        @api {POST} /subscription/instance_status/ 查询订阅运行状态
        @apiName query_instance_status
        @apiGroup subscription
        """
        params = self.validated_data

        subscriptions = models.Subscription.objects.filter(id__in=params["subscription_id_list"])

        # 查出所有HostStatus
        instance_host_statuses = defaultdict(list)
        for host_status in models.ProcessStatus.objects.filter(source_id__in=params["subscription_id_list"]).only(
            "name", "status", "version", "group_id"
        ):
            instance_host_statuses[host_status.group_id].append(host_status)

        # 查出所有InstanceRecord
        subscription_instance_record: Dict[int, Dict[str, models.SubscriptionInstanceRecord]] = defaultdict(dict)
        instance_records = []
        for instance_record in models.SubscriptionInstanceRecord.objects.filter(
            subscription_id__in=params["subscription_id_list"], is_latest=True
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
            current_instances = tools.get_instances_by_scope(
                subscription.scope, get_cache=True, source="instance_status"
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

                    if params["show_task_detail"]:
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
        return Response(result)

    @swagger_auto_schema(operation_summary="订阅启停", tags=SUBSCRIPTION_VIEW_TAGS)
    @action(detail=False, methods=["POST"], serializer_class=serializers.SwitchSubscriptionSerializer)
    def switch(self, request):
        """
        @api {POST} /subscription/switch/ 订阅启停
        @apiName subscription_switch
        @apiGroup subscription
        """
        params = self.validated_data
        try:
            subscription = models.Subscription.objects.get(id=params["subscription_id"], is_deleted=False)
        except models.Subscription.DoesNotExist:
            raise errors.SubscriptionNotExist({"subscription_id": params["subscription_id"]})

        if params["action"] == "enable":
            subscription.enable = True
        elif params["action"] == "disable":
            subscription.enable = False

        subscription.save()

        return Response()

    @swagger_auto_schema(operation_summary="终止正在执行的任务", tags=SUBSCRIPTION_VIEW_TAGS)
    @action(detail=False, methods=["POST"], serializer_class=serializers.RevokeSubscriptionSerializer)
    def revoke(self, request):
        """
        @api {POST} /subscription/revoke/ 终止正在执行的任务
        @apiName revoke_subscription
        @apiGroup subscription
        """
        params = self.validated_data
        instance_id_list = params.get("instance_id_list", [])
        subscription_id = params["subscription_id"]
        SubscriptionHandler(subscription_id=subscription_id).revoke(instance_id_list)
        return Response()

    @swagger_auto_schema(
        operation_summary="重试失败的任务",
        responses={status.HTTP_200_OK: response.RetryResponseSerializer()},
        tags=SUBSCRIPTION_VIEW_TAGS,
    )
    @action(detail=False, methods=["POST"], serializer_class=serializers.RetrySubscriptionSerializer)
    def retry(self, request):
        """
        @api {POST} /subscription/retry/ 重试失败的任务
        @apiName retry_subscription
        @apiGroup subscription
        """
        params = self.validated_data

        retry_result = SubscriptionHandler(subscription_id=params["subscription_id"]).retry(
            task_id_list=params.get("task_id_list"),
            instance_id_list=params.get("instance_id_list"),
            actions=params.get("actions"),
        )
        return Response(retry_result)

    @swagger_auto_schema(operation_summary="重试原子", tags=SUBSCRIPTION_VIEW_TAGS)
    @action(detail=False, methods=["POST"], serializer_class=serializers.RetryNodeSerializer)
    def retry_node(self, request):
        """
        @api {POST} /subscription/retry_node/ 重试原子
        @apiName retry_node
        @apiGroup subscription
        @apiParam {String} instance_id 实例id
        @apiParam {Number} subscription_id 订阅id
        @apiParamExample {Json} 重试时请求参数
        {
            "instance_id": host|instance|host|127.0.0.1-0-0
            "subscription_id": 123
        }
        @apiSuccessExample {json} 成功返回:
        {
            "retry_node_id": "6f48169ed1193574961757a57d03a778",
            "retry_node_name": "安装"
        }
        """
        params = self.validated_data
        subscription_id = params["subscription_id"]
        instance_id = params["instance_id"]

        instance_record_qs = models.SubscriptionInstanceRecord.objects.filter(
            subscription_id=subscription_id, instance_id=instance_id
        )
        if not instance_record_qs.exists():
            raise errors.SubscriptionInstanceRecordNotExist()

        instance_record = instance_record_qs.latest("create_time")
        pipeline_parser = PipelineParser([instance_record.pipeline_id])
        instance_status = tools.get_subscription_task_instance_status(
            instance_record, pipeline_parser, need_detail=True
        )

        if not (instance_status["steps"] and instance_status["steps"][0].get("target_hosts")):
            raise errors.SubscriptionInstanceRecordNotExist()

        # 找出第一个失败的节点
        failed_node = next(
            (
                node
                for node in instance_status["steps"][0]["target_hosts"][0].get("sub_steps")
                if node["status"] == constants.JobStatusType.FAILED
            ),
            None,
        )
        # 无法获取失败任务节点的情况：失败任务重试中，安装任务已正常完成
        if not failed_node:
            raise errors.SubscriptionInstanceRecordNotExist("无法获取失败任务节点")
        tasks.retry_node.delay(failed_node["pipeline_id"])
        return Response({"retry_node_id": failed_node["pipeline_id"], "retry_node_name": failed_node["node_name"]})

    @swagger_auto_schema(operation_summary="接收cmdb事件回调", tags=SUBSCRIPTION_VIEW_TAGS, methods=["GET", "POST"])
    @action(detail=False, methods=["GET", "POST"], serializer_class=serializers.CMDBSubscriptionSerializer)
    def cmdb_subscription(self, request):
        """
        @api {POST} /subscription/cmdb_subscription/ 接收cmdb事件回调
        @apiName cmdb_subscription
        @apiGroup subscription
        """
        params = self.validated_data

        cmdb_events = []
        for data in params["data"]:
            cmdb_events.append(
                models.CmdbEventRecord(
                    event_type=params["event_type"],
                    action=params["action"],
                    obj_type=params["obj_type"],
                    cur_data=data["cur_data"],
                    pre_data=data["pre_data"],
                )
            )
        models.CmdbEventRecord.objects.bulk_create(cmdb_events)
        return Response("ok")

    @swagger_auto_schema(operation_summary="返回安装命令", tags=SUBSCRIPTION_VIEW_TAGS)
    @action(detail=False, methods=["POST"], serializer_class=serializers.FetchCommandsSerializer)
    def fetch_commands(self, request):
        """
        @api {POST} /subscription/fetch_commands/ 返回安装命令
        @apiName fetch_commands
        @apiGroup subscription
        """

        params = self.validated_data
        sub_inst: models.SubscriptionInstanceRecord = models.SubscriptionInstanceRecord.objects.get(
            id=params["sub_inst_id"]
        )
        sub_step_obj: models.SubscriptionStep = models.SubscriptionStep.objects.filter(
            subscription_id=sub_inst.subscription_id
        ).first()
        host = models.Host.objects.get(bk_host_id=params["bk_host_id"])

        # 优先使用注入的AP_ID
        injected_ap_id = sub_inst.instance_info.get("meta", {}).get("AP_ID")
        host_ap_id: int = injected_ap_id or host.ap_id
        ap_id_obj_map: Dict[int, models.AccessPoint] = models.AccessPoint.ap_id_obj_map()
        host_ap: models.AccessPoint = ap_id_obj_map[host_ap_id]

        base_agent_setup_info_dict: Dict[str, Any] = asdict(
            AgentStepAdapter(subscription_step=sub_step_obj, gse_version=host_ap.gse_version).setup_info
        )
        agent_setup_extra_info_dict = sub_inst.instance_info["host"].get("agent_setup_extra_info") or {}
        installation_tool = gen_commands(
            agent_setup_info=AgentSetupInfo(
                **{
                    **base_agent_setup_info_dict,
                    "force_update_agent_id": agent_setup_extra_info_dict.get("force_update_agent_id", False),
                }
            ),
            host=host,
            host_ap=host_ap,
            pipeline_id=params["host_install_pipeline_id"],
            is_uninstall=params["is_uninstall"],
            sub_inst_id=params["sub_inst_id"],
            is_combine_cmd_step=True,
            script_hook_objs=ScriptManageHandler.fetch_match_script_hook_objs(
                sub_step_obj.params.get("script_hooks") or [], host.os_type
            ),
        )
        if installation_tool.is_need_jump_server:
            execution_solutions = installation_tool.type__execution_solution_map[
                constants.CommonExecutionSolutionType.SHELL.value
            ].target_host_solutions
        else:
            execution_solutions = installation_tool.type__execution_solution_map.values()

        solutions = [basic.obj_to_dict(execution_solution) for execution_solution in execution_solutions]

        return Response({"solutions": solutions})

    @swagger_auto_schema(operation_summary="查询策略列表", tags=SUBSCRIPTION_VIEW_TAGS)
    @action(detail=False, methods=["POST"], serializer_class=serializers.SearchDeployPolicySerializer)
    def search_deploy_policy(self, *args, **kwargs):
        """
        @api {POST} /subscription/search_deploy_policy/ 查询策略列表
        @apiName list_deploy_policy
        @apiGroup subscription
        @apiParam {Int[]} [bk_biz_ids] 业务ID列表, 不传取全业务
        @apiParam {Object[]} [conditions] 查询条件
        @apiParam {String} [conditions.key] 查询关键字，`query`表示多字段模糊搜索，目前仅支持`name`
        @apiParam {String} [conditions.value] 查询值，单值查询
        @apiParam {String[]} [conditions.value] 查询值，多值模糊查询
        @apiParam {object} [sort] 排序
        @apiParam {String=["name", "plugin_name", "creator", "update_time", "nodes_scope", "bk_biz_scope"]} ...
        [sort.head] 排序字段
        @apiParam {String=["ASC", "DEC"]} [sort.sort_type] 排序类型
        @apiParam {Int} [page] 当前页数
        @apiParam {Int} [pagesize] 分页大小
        @apiSuccessExample {json} 成功返回:
        {
            "total": 10,
            "list": [
                {
                    "id": 1,
                    "name": "日志采集",
                    "plugin_name": "basereport",
                    "nodes_scope": {
                        "host_count": 99,
                        "node_count": 123,
                    }
                    "bk_biz_scope": [1, 2, 3]
                    "operator": "admin",
                    "updated_at": "2020-07-26 19:17:56"
                },
                {
                    "id": 2,
                    "name": "日志采集2",
                    "plugin_name": "basereport",
                    "nodes_scope": {
                        "host_count": 80,
                        "node_count": 123,
                    }
                    "bk_biz_scope": [1, 2]
                    "operator": "admin",
                    "updated_at": "2020-07-26 19:17:56"
                }
            ]
        }
        """

        params = self.validated_data
        begin, end = None, None
        if params["pagesize"] != -1:
            begin = (params["page"] - 1) * params["pagesize"]
            end = (params["page"]) * params["pagesize"]

        or_query = Q()
        root_query = Q()
        and_query = Q(category=models.Subscription.CategoryType.POLICY)
        # 构造查询条件
        for condition in params.get("conditions", []):
            # 1. 精确查找
            if condition["key"] in ["plugin_name", "id"]:
                if isinstance(condition["value"], list):
                    and_query = and_query & Q(**{condition["key"] + "__in": condition["value"]})
                else:
                    and_query = and_query & Q(**{condition["key"]: condition["value"]})

            # 2. 仅在父策略生效的查询条件
            elif condition["key"] in ["enable"]:
                if isinstance(condition["value"], list):
                    root_query = root_query & Q(**{condition["key"] + "__in": condition["value"]})
                else:
                    root_query = root_query & Q(**{condition["key"]: condition["value"]})

            # 3. 多字段模糊查询
            elif condition["key"] == "query":
                support_filter_fields = ["name", "plugin_name"]
                values = condition["value"] if isinstance(condition["value"], list) else [condition["value"]]
                for value in values:
                    or_query = or_query | reduce(
                        operator.or_, [Q(**{field + "__contains": value}) for field in support_filter_fields]
                    )

        ids_need_expend = set()

        if params["only_root"]:
            if params.get("conditions"):
                pids = set(
                    models.Subscription.objects.filter(
                        and_query & or_query & ~Q(pid=models.Subscription.ROOT)
                    ).values_list("pid", flat=True)
                )
                ids_need_expend = ids_need_expend | pids
                subscription_qs = (
                    models.Subscription.filter_parent_qs()
                    .filter((and_query & or_query) | Q(id__in=pids))
                    .filter(root_query)
                )
            else:
                subscription_qs = models.Subscription.filter_parent_qs().filter(and_query & or_query)
        else:
            subscription_qs = models.Subscription.objects.all().filter(and_query & or_query)
        # 增加部署节点数量字段
        subscription_qs = subscription_qs.extra(select={"bk_biz_scope_len": "JSON_LENGTH(bk_biz_scope)"})

        ordering: str = params.get("ordering")
        if ordering:
            subscription_qs = subscription_qs.order_by(*ordering.split(","))

        all_subscription = list(
            subscription_qs.values("id", "name", "plugin_name", "bk_biz_scope", "update_time", "creator", "enable")
        )

        # 指定业务查询范围筛选业务范围有交集的策略
        all_subscriptions = (
            [
                subscription
                for subscription in all_subscription
                if set(subscription["bk_biz_scope"]) & set(params["bk_biz_ids"])
            ]
            if "bk_biz_ids" in params
            else all_subscription
        )

        subscriptions = all_subscriptions[begin:end]

        for subscription in subscriptions:
            # 展示优化，当搜索命中灰度策略时，expend=True标志策略展开，显示检索的灰度
            subscription["expand"] = subscription["id"] in ids_need_expend

        return Response({"total": len(all_subscriptions), "list": subscriptions})

    @swagger_auto_schema(operation_summary="获取主机策略列表", tags=SUBSCRIPTION_VIEW_TAGS)
    @action(detail=False, methods=["GET"], serializer_class=serializers.QueryHostPolicySerializer)
    def query_host_policy(self, request):
        """
        @api {GET} /subscription/query_host_policy/ 获取主机策略列表
        @apiName query_host_policy
        @apiGroup subscription
        """
        params = self.validated_data
        bk_host_id = params["bk_host_id"]
        host = models.Host.objects.get(bk_host_id=bk_host_id)

        subscription_records = models.SubscriptionInstanceRecord.objects.filter(
            instance_id__endswith="host|{}".format(host.bk_host_id),
            is_latest=True,
        ).values("subscription_id", "update_time", "instance_id", "task_id", "status")

        sub_id__sub_record_map = {
            subscription_record["subscription_id"]: {
                "update_time": subscription_record["update_time"],
                "instance_id": subscription_record["instance_id"],
                "task_id": subscription_record["task_id"],
                "status": subscription_record["status"],
            }
            for subscription_record in subscription_records
        }

        subscriptions = models.Subscription.objects.filter(
            id__in=sub_id__sub_record_map.keys(),
            category__in=[models.Subscription.CategoryType.POLICY, models.Subscription.CategoryType.ONCE],
        ).values("id", "name", "enable", "plugin_name", "category")

        subscription_ids = [subscription["id"] for subscription in subscriptions]
        # 查询订阅任务对应的job_id
        jobs = models.Job.objects.filter(subscription_id__in=subscription_ids).values(
            "id", "task_id_list", "created_by", "job_type"
        )

        task_id__job_info_map = {}
        for job in jobs:
            for task_id in job["task_id_list"]:
                task_id__job_info_map[task_id] = job

        # 部署方式
        subscription_plugin_names = [subscription["plugin_name"] for subscription in subscriptions]
        deploy_types = models.GsePluginDesc.objects.filter(name__in=subscription_plugin_names).values(
            "name", "deploy_type"
        )
        deploy_type_map = {deploy_type["name"]: deploy_type["deploy_type"] for deploy_type in deploy_types}

        # 版本
        proc_statuses = models.ProcessStatus.objects.filter(
            bk_host_id=bk_host_id,
            source_id__in=subscription_ids,
            proc_type=constants.ProcType.PLUGIN,
            source_type=models.ProcessStatus.SourceType.DEFAULT,
        ).values("source_id", "name", "version", "setup_path", "is_latest")
        sub_id__proc_status_map = {int(proc_status["source_id"]): proc_status for proc_status in proc_statuses}

        # 配置模版
        configs = models.SubscriptionStep.objects.filter(subscription_id__in=subscription_ids).values(
            "subscription_id", "config"
        )
        config_detail_map = {
            config["subscription_id"]: config["config"]["details"]
            for config in configs
            if config["config"].get("details")
        }

        config_templates_name_map = {}
        config_templates_version_map = {}
        for subscription_id, config_details in config_detail_map.items():
            for config_detail in config_details:
                for config_template in config_detail["config_templates"]:
                    if config_template["is_main"]:
                        config_templates_name_map.update({subscription_id: config_template["name"]})
                        config_templates_version_map.update({subscription_id: config_template["version"]})

        operate_records = []
        for subscription in subscriptions:
            sub_record = sub_id__sub_record_map[subscription["id"]]
            job_info = task_id__job_info_map.get(sub_record["task_id"], {})
            proc_status = sub_id__proc_status_map.get(subscription["id"], {})

            if job_info.get("job_type") not in [
                constants.JobType.MAIN_INSTALL_PLUGIN,
                constants.JobType.MAIN_START_PLUGIN,
            ]:
                continue

            if host.os_type == constants.OsType.WINDOWS:
                install_path = proc_status.get("setup_path", "").replace("/", "\\")
            else:
                install_path = proc_status.get("setup_path")

            operate_records.append(
                {
                    "name": subscription["name"],
                    "category": subscription["category"],
                    "plugin_name": subscription["plugin_name"],
                    "auto_trigger": subscription["enable"],
                    # 填充进程信息
                    "version": proc_status.get("version"),
                    "install_path": install_path,
                    "is_latest": proc_status.get("is_latest"),
                    # 任务执行情况
                    "status": sub_record["status"],
                    "update_time": sub_record["update_time"],
                    "instance_id": sub_record["instance_id"],
                    "job_id": job_info.get("id"),
                    "job_type": job_info.get("job_type"),
                    # 订阅的更新是通过作业下发完成的，所以作业的创建账户即为订阅的更新账户
                    "updated_by": job_info.get("created_by"),
                    "deploy_type": deploy_type_map.get(subscription["plugin_name"]),
                    "config_template": config_templates_name_map.get(subscription["id"]),
                    "plugin_version": config_templates_version_map.get(subscription["id"]),
                }
            )

        def _op_record_comparator(_left: Dict, _right: Dict) -> int:
            """按策略、一次性操作排序，同类别按更新时间降序"""
            sub_category_order = [models.Subscription.CategoryType.POLICY, models.Subscription.CategoryType.ONCE]
            diff = sub_category_order.index(_left["category"]) - sub_category_order.index(_right["category"])

            if diff != 0:
                return (1, -1)[diff < 0]
            return (1, -1)[_left["update_time"] > _right["update_time"]]

        operate_records.sort(key=cmp_to_key(_op_record_comparator))
        return Response(operate_records)

    @swagger_auto_schema(operation_summary="获取主机订阅列表", tags=SUBSCRIPTION_VIEW_TAGS)
    @action(detail=False, methods=["GET"], serializer_class=serializers.QueryHostSubscriptionsSerializer)
    def query_host_subscriptions(self, request):
        """
        @api {GET} /subscription/query_host_subscriptions/ 获取主机订阅列表
        @apiName query_host_subscription_ids
        @apiGroup subscription
        @apiParam {String} [bk_host_innerip] 内网IP
        @apiParam {Number} [bk_cloud_id] 管控区域ID
        @apiParam {Number} [bk_host_id] CMDB主机ID
        @apiParam {String} [source_type] 类型，可选[default, subscription]
        @apiSuccessExample {json} 成功返回:
        [
            {
            id: 817,
            source_type: "subscription",
            source_id: "93",
            name: "bkunifylogbeat",
            version: "1.10.58",
            status: "RUNNING"
            }
        ]
        """
        params = self.validated_data
        source_type = params.get("source_type")
        bk_host_id = models.Host.get_by_host_info(params).bk_host_id
        return Response(
            models.ProcessStatus.fetch_process_statuses_by_host_id(bk_host_id=bk_host_id, source_type=source_type)
        )

    @swagger_auto_schema(operation_summary="启用/禁用业务订阅巡检", tags=SUBSCRIPTION_VIEW_TAGS)
    @action(detail=False, methods=["POST"], serializer_class=serializers.SubscriptionSwitchBizSerializer)
    def switch_biz(self, request):
        """
        @api {POST} /subscription/switch_biz/ 启用/禁用业务订阅巡检
        @apiName switch_biz
        @apiGroup subscription
        """
        data = self.validated_data
        global_config_key: str = models.GlobalSettings.KeyEnum.DISABLE_SUBSCRIPTION_SCOPE_LIST.value
        if not models.GlobalSettings.objects.filter(key=global_config_key).exists():
            models.GlobalSettings.set_config(key=global_config_key, value=[])
        disable_subscription_bk_biz_ids: List[int] = models.GlobalSettings.get_config(key=global_config_key, default=[])
        if data["action"] == SubscriptionSwithBizAction.ENABLE.value:
            # 更新禁用业务列表
            models.GlobalSettings.update_config(
                key=global_config_key,
                value=list(set(disable_subscription_bk_biz_ids) - set(data["bk_biz_ids"])),
            )
        else:

            # 更新禁用业务列表
            models.GlobalSettings.update_config(
                key=global_config_key,
                value=list(set(disable_subscription_bk_biz_ids + data["bk_biz_ids"])),
            )
        return Response(data)
