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
import traceback
from collections import defaultdict
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.backend.subscription import tools
from apps.backend.utils import pipeline_parser
from apps.core.concurrent import controller
from apps.node_man import constants, models
from apps.utils import concurrent
from apps.utils.time_handler import strftime_local

logger = logging.getLogger("app")


class TaskResultTools:
    @staticmethod
    def list_pipeline_processes(pipeline_id: str) -> Dict[str, List[Dict]]:
        pipeline = models.PipelineTree.objects.get(id=pipeline_id).tree

        # parallel_gw = next(
        #     (gw for gw in pipeline["gateways"].values() if gw["type"] == pipeline_parser.ActType.PARALLEL), None
        # )
        parallel_gws = [gw for gw in pipeline["gateways"].values() if gw["type"] == pipeline_parser.ActType.PARALLEL]

        pipeline_processes = {}
        for parallel_gw in parallel_gws:
            for outgoing in parallel_gw["outgoing"]:
                pipeline_process = []
                index = 0
                while True:
                    next_node = next(
                        (node for node in pipeline["activities"].values() if outgoing in node["incoming"]), None
                    )
                    if not next_node:
                        break
                    pipeline_process.append(
                        {
                            "node_id": next_node["id"],
                            "name": next_node["name"],
                            "step_code": next_node["component"].get("code"),
                            "index": index,
                        }
                    )
                    index = index + 1
                    outgoing = next_node["outgoing"]
                pipeline_processes[pipeline_process[0]["node_id"]] = pipeline_process

        return pipeline_processes

    @staticmethod
    def collect_status(steps: List[Dict[str, Any]], backtrace_steps=False) -> str:
        status_set = set([sub_step["status"] for sub_step in steps])
        status = constants.JobStatusType.PENDING
        if len(status_set) == 1 and list(status_set)[0] == constants.JobStatusType.SUCCESS:
            status = constants.JobStatusType.SUCCESS
        elif constants.JobStatusType.FAILED in status_set:
            status = constants.JobStatusType.FAILED
        elif constants.JobStatusType.RUNNING in status_set:
            status = constants.JobStatusType.RUNNING

        # 如果 steps 中都是 Pending 那返回的 status 也是 Pending
        if status_set != {constants.JobStatusType.PENDING} and backtrace_steps:
            # 填充 steps 中的状态
            # 1. 找到第一个 RUNNING / FAILED 的节点索引
            index: Optional[int] = next(
                (
                    i
                    for i, step in enumerate(steps)
                    if step["status"] in [constants.JobStatusType.FAILED, constants.JobStatusType.RUNNING]
                ),
                None,
            )

            # 2. 如果找到，将前面的状态都填充为成功
            if index is not None:
                for step in steps[:index]:
                    step["status"] = constants.JobStatusType.SUCCESS

        return status

    @classmethod
    def _list_subscription_task_instance_status(
        cls, instance_records: List[models.SubscriptionInstanceRecord], need_detail=False
    ) -> List[Dict[str, Any]]:
        if not instance_records:
            return []
        subscription_tasks = models.SubscriptionTask.objects.filter(
            id__in=set([inst_record.task_id for inst_record in instance_records])
        ).values("id", "pipeline_id")

        subscription_task_id_dict_map = {
            subscription_task["id"]: subscription_task for subscription_task in subscription_tasks
        }
        pipeline_processes_id_obj_map = {}
        for subscription_task in subscription_task_id_dict_map.values():
            if subscription_task["pipeline_id"] in pipeline_processes_id_obj_map:
                continue
            pipeline_processes_id_obj_map[subscription_task["pipeline_id"]] = cls.list_pipeline_processes(
                pipeline_id=subscription_task["pipeline_id"]
            )

        fields = ["id", "subscription_instance_record_id", "node_id", "status", "update_time", "create_time"]
        if need_detail:
            fields.append("log")
        node_id_inst_status_detail_map = {
            f"{status_detail['node_id']}-{status_detail['subscription_instance_record_id']}": status_detail
            for status_detail in models.SubscriptionInstanceStatusDetail.objects.filter(
                subscription_instance_record_id__in=set([inst_record.id for inst_record in instance_records])
            ).values(*fields)
        }

        instance_status_list = []
        for instance_record in instance_records:
            # 兼容订阅任务不存在的情况
            if instance_record.task_id not in subscription_task_id_dict_map:
                continue
            subscription_task_dict = subscription_task_id_dict_map[instance_record.task_id]
            instance_status_list.append(
                cls.get_subscription_task_instance_status(
                    instance_record,
                    subscription_task_dict,
                    pipeline_processes_id_obj_map[subscription_task_dict["pipeline_id"]],
                    node_id_inst_status_detail_map,
                    need_detail,
                )
            )
        return instance_status_list

    @classmethod
    def list_subscription_task_instance_status(
        cls, instance_records: List[models.SubscriptionInstanceRecord], need_detail=False
    ) -> List[Dict[str, Any]]:
        @controller.ConcurrentController(
            data_list_name="_instance_records",
            batch_call_func=concurrent.batch_call,
            extend_result=True,
            get_config_dict_func=lambda: {"limit": 500},
        )
        def _inner(
            _instance_records: List[models.SubscriptionInstanceRecord], _need_detail=False
        ) -> List[Dict[str, Any]]:
            return cls._list_subscription_task_instance_status(
                instance_records=_instance_records, need_detail=_need_detail
            )

        return _inner(_instance_records=instance_records, _need_detail=need_detail)

    @classmethod
    def get_subscription_task_instance_status(
        cls,
        instance_record_obj: models.SubscriptionInstanceRecord,
        subscription_task_dict: Dict[str, Any],
        pipeline_processes: Dict[str, List[Dict]],
        node_id_inst_status_detail_map: Dict[str, Dict],
        need_detail=False,
    ) -> Dict[str, Any]:

        instance_status = {
            "task_id": subscription_task_dict["id"],
            "record_id": instance_record_obj.id,
            "instance_id": instance_record_obj.instance_id,
            "create_time": strftime_local(instance_record_obj.create_time),
            "pipeline_id": subscription_task_dict["pipeline_id"],
            "instance_info": (
                instance_record_obj.instance_info if need_detail else instance_record_obj.simple_instance_info()
            ),
            "start_time": None,
            "finish_time": None,
            "steps": [],
        }

        host_info = instance_record_obj.instance_info.get("host", {})
        host_key = f"{host_info.get('bk_cloud_id')}:{host_info.get('bk_host_innerip')}"

        steps = instance_record_obj.get_all_step_data()

        start_node_index = 0
        all_pipeline_proc = []
        for step in steps:
            pipeline_id = step["pipeline_id"]
            if pipeline_id in pipeline_processes:
                all_pipeline_proc = pipeline_processes[pipeline_id]

        for step_index, step in enumerate(steps):
            next_node_id = None if step_index == len(steps) - 1 else steps[step_index + 1]["pipeline_id"]

            next_node_index = None
            for node in all_pipeline_proc:
                if node["node_id"] == next_node_id:
                    next_node_index = node["index"]
                    break

            if start_node_index == next_node_index:
                next_node_index = None

            step_pipeline_proc = all_pipeline_proc[start_node_index:next_node_index]

            sub_steps = []
            last_finish_sub_step = None
            for index, node in enumerate(step_pipeline_proc):
                node_inst_status_detail = node_id_inst_status_detail_map.get(
                    f"{node['node_id']}-{instance_record_obj.id}", {"status": constants.JobStatusType.PENDING}
                )
                sub_step = {
                    "index": index,
                    "node_name": node["name"],
                    "step_code": node["step_code"],
                    "pipeline_id": node["node_id"],
                    "log": node_inst_status_detail.get("log", ""),
                    "ex_data": None,
                    "status": node_inst_status_detail["status"],
                    "start_time": strftime_local(node_inst_status_detail.get("create_time")),
                    "finish_time": strftime_local(
                        None
                        if node_inst_status_detail["status"] == constants.JobStatusType.PENDING
                        else node_inst_status_detail["update_time"]
                    ),
                }
                # 兼容数据平台，数据平台使用到inputs字段
                if index == 2:
                    sub_step["inputs"] = {"instance_info": instance_record_obj.instance_info}
                sub_steps.append(sub_step)

                if sub_step["status"] in [constants.JobStatusType.SUCCESS, constants.JobStatusType.FAILED]:
                    last_finish_sub_step = sub_step

            if not sub_steps:
                continue

            # 子步骤状态聚合 并且填充失败前的子步骤节点状态
            status = cls.collect_status(steps=sub_steps, backtrace_steps=True)
            last_finish_sub_step = last_finish_sub_step or sub_steps[-1]

            finish_time = None
            # 任务已有明确执行完成（失败或成功）的标志时，记录最后一个完成节点的完成时间作为任务整体的完成时间，否则完成时间为None
            if status in [constants.JobStatusType.FAILED, constants.JobStatusType.SUCCESS]:
                finish_time = last_finish_sub_step["finish_time"]

            step.update(
                {
                    "status": status,
                    "pipeline_id": sub_steps[0]["pipeline_id"],
                    "start_time": sub_steps[0]["start_time"],
                    "finish_time": finish_time,
                    "target_hosts": [
                        {
                            "node_name": f"{step.get('node_name')} {host_key}",
                            "pipeline_id": sub_steps[0]["pipeline_id"],
                            "status": status,
                            "start_time": sub_steps[0]["start_time"],
                            "finish_time": finish_time,
                            "sub_steps": sub_steps,
                        }
                    ],
                }
            )
            instance_status["steps"].append(step)
            start_node_index = next_node_index

        if instance_status["steps"]:
            # 如果 instance_record_obj 的状态不是 PENDING，且聚合的状态是 PENDING 则从 instance_record 获取状态
            instance_record_status = instance_record_obj.status
            collect_status = cls.collect_status(instance_status["steps"])
            if (
                instance_record_status != constants.JobStatusType.PENDING
                and collect_status == constants.JobStatusType.PENDING
            ):
                status = instance_record_status
                start_time = strftime_local(instance_record_obj.create_time)
                finish_time = strftime_local(instance_record_obj.update_time)
            else:
                status = cls.collect_status(instance_status["steps"])
                start_time = instance_status["steps"][0]["start_time"]
                finish_time = instance_status["steps"][-1]["finish_time"]
            instance_status.update(status=status, start_time=start_time, finish_time=finish_time)
        else:
            # 没有执行步骤，从instance_record获取状态
            instance_status["status"] = instance_record_obj.status

        return instance_status


def update_inst_record_status(
    inst_record_queryset: QuerySet,
    subscription_task_id_obj_map: Dict[int, models.SubscriptionTask],
):
    status_set = set(inst_record_queryset.values_list("status", flat=True))
    # 任务已执行完成（有明确结果），直接返回
    if not (status_set & {constants.JobStatusType.PENDING, constants.JobStatusType.RUNNING}):
        return

    instance_records = inst_record_queryset.all()

    old_instance_records = []
    new_instance_records = []
    for instance_record in instance_records:
        if subscription_task_id_obj_map[instance_record.task_id].pipeline_id:
            new_instance_records.append(instance_record)
        else:
            old_instance_records.append(instance_record)

    instance_status_list = TaskResultTools.list_subscription_task_instance_status(instance_records=new_instance_records)

    _pipeline_parser = pipeline_parser.PipelineParser([r.pipeline_id for r in old_instance_records])
    for instance_record in old_instance_records:
        instance_status_list.append(
            tools.get_subscription_task_instance_status(instance_record, _pipeline_parser, False)
        )

    record_id_gby_status = defaultdict(list)
    for instance_status in instance_status_list:
        record_id_gby_status[instance_status["status"]].append(instance_status["record_id"])

    with transaction.atomic():
        for status, record_ids in record_id_gby_status.items():
            models.SubscriptionInstanceRecord.objects.filter(id__in=record_ids).update(
                status=status, update_time=timezone.now()
            )


def transfer_instance_record_status(subscription_ids: List[int] = None):
    if subscription_ids is None:
        subscription_ids = models.Subscription.objects.all().values_list("id", flat=True)

    success_subscription_ids = set()
    for subscription_id in subscription_ids:
        try:
            subscription_tasks = models.SubscriptionTask.objects.filter(subscription_id=subscription_id)
            subscription_task_id_obj_map = {task.id: task for task in subscription_tasks}

            if not subscription_tasks:
                continue

            base_kwargs = {"subscription_id": subscription_id, "is_latest": True}
            update_inst_record_status(
                models.SubscriptionInstanceRecord.objects.filter(**base_kwargs), subscription_task_id_obj_map
            )
        except Exception as err:
            logger.error(
                f"transfer_instance_record_status: subscription_id -> {subscription_id}, "
                f"err_msg -> {err}. \n {traceback.format_exc()}"
            )
            continue

        success_subscription_ids.add(subscription_id)

    logger.info(f"transfer_instance_record_status: success_subscription_ids -> {success_subscription_ids}")
