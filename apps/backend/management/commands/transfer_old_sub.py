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

import itertools
import json
import math
import random
import time
import traceback
import uuid
from collections import defaultdict
from typing import Any, Dict, List, Set

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.backend.management.commands import utils
from apps.backend.subscription import tools
from apps.backend.utils import pipeline_parser
from apps.node_man import constants, models
from apps.utils import concurrent
from apps.utils.time_handler import strftime_local

log_and_print = utils.get_log_and_print("transfer_old_sub")


def called_hook(result: Any, cost_time: float, call_params: Dict[str, Any]):
    subscription_id = call_params.get("subscription_id")
    log_and_print(
        f"subscription_id -> {subscription_id} " f"cost_time -> {round(cost_time)}s",
        execute_id=call_params.get("execute_id"),
    )


def create_pipeline_from_instance_status(instance_status_list: List[Dict]):
    """从instance status 反向构造pipeline(仅用于任务状态查询)"""
    pipeline = {"id": uuid.uuid4().hex, "gateways": {}, "activities": {}}

    pg_gw = {"id": uuid.uuid4().hex, "type": pipeline_parser.ActType.PARALLEL, "outgoing": []}
    pipeline["gateways"][pg_gw["id"]] = pg_gw

    act_gby_instance_action_and_steps = defaultdict(lambda: defaultdict(list))
    step_info_gby_instance_action_and_steps = defaultdict(lambda: defaultdict(list))
    for instance_status in instance_status_list:
        instance_action_str = json.dumps({step["id"]: step["action"] for step in instance_status["steps"]})

        sub_steps = list(itertools.chain(*[step["target_hosts"][0]["sub_steps"] for step in instance_status["steps"]]))
        steps_compress_str = ".".join(sub_step["node_name"] for sub_step in sub_steps)

        step_info_gby_instance_action_and_steps[instance_action_str][steps_compress_str] = [
            {
                "id": step["id"],
                "type": step["type"],
                "action": step["action"],
                "node_name": step.get("node_name"),
                "pipeline_id": step["target_hosts"][0]["sub_steps"][0]["pipeline_id"],
            }
            for step in instance_status["steps"]
        ]

        last_act = pg_gw
        for index, sub_step in enumerate(sub_steps):
            activity = {
                "id": sub_step["pipeline_id"],
                "name": sub_step["node_name"],
                "index": index,
                "component": {},
                "incoming": [last_act["id"] if last_act != pg_gw else uuid.uuid4().hex],
                "outgoing": "",
            }
            if isinstance(last_act["outgoing"], list):
                last_act["outgoing"].append(activity["incoming"][0])
            else:
                last_act["outgoing"] = activity["incoming"][0]

            last_act = activity
            pipeline["activities"][activity["id"]] = activity

            act_gby_instance_action_and_steps[instance_action_str][steps_compress_str].append(activity)

    return {
        "pipeline": pipeline,
        "act_gby_instance_action_and_steps": act_gby_instance_action_and_steps,
        "step_info_gby_instance_action_and_steps": step_info_gby_instance_action_and_steps,
    }


@utils.program_timer(called_hook=called_hook)
@transaction.atomic()
def transfer_record(execute_id: int, subscription_id: int, is_agent: bool):
    """
    迁移任务历史日志并删除冗余Pipeline数据, 大致执行时间 -> 旧订阅300个pipeline，需要2秒
    :param execute_id:
    :param is_agent:
    :param subscription_id:
    :return: 返回执行中的id
    """
    old_task_ids = []
    base_query_kwargs = {"subscription_id": subscription_id, "is_latest": True}
    inst_record_simple_infos = models.SubscriptionInstanceRecord.objects.filter(**base_query_kwargs).values(
        "task_id", "id"
    )
    for sub_task_info in models.SubscriptionTask.objects.filter(subscription_id=subscription_id).values(
        "id", "pipeline_id"
    ):
        # task-pipeline id不为空表示为优化后的任务，或已完成迁移的任务，此处保留空pipeline的task_id，用于过滤
        if not sub_task_info["pipeline_id"]:
            old_task_ids.append(sub_task_info["id"])

    # 筛选出未完成迁移的实例，一方面用于检测是否该任务已完成迁移，另一方面兼容老任务已在新版本中重试
    instance_record_ids = [r["id"] for r in inst_record_simple_infos if r["task_id"] in old_task_ids]

    if not instance_record_ids:
        log_and_print(f"任务迁移已完成，无需重复迁移: subscription_id -> {subscription_id}", execute_id=execute_id)
        return

    # 延迟全量查询到任务迁移完成判定后，减少已完成迁移任务的查询成本
    instance_records = models.SubscriptionInstanceRecord.objects.filter(**base_query_kwargs, id__in=instance_record_ids)

    pipeline_ids_to_be_deleted = [r.pipeline_id for r in instance_records]

    log_and_print(
        f"subscription_id -> {subscription_id}, pipeline's num -> {len(pipeline_ids_to_be_deleted)}",
        execute_id=execute_id,
    )

    pipeline_parser_inst = pipeline_parser.PipelineParser(pipeline_ids_to_be_deleted)
    instance_status_list = [
        tools.get_subscription_task_instance_status(
            instance_record, pipeline_parser_inst, need_detail=False, need_log=True
        )
        for instance_record in instance_records
    ]

    # agent任务只需把状态同步到InstanceRecord，新创建的任务通过tasks.calculate_statistics进行同步
    # TODO 后续agent支持和插件一样的流程后，去掉该分支
    if is_agent:
        log_and_print(f"subscription_id -> {subscription_id} 为agent任务，仅同步实例状态", execute_id=execute_id)

        record_id_gby_status = defaultdict(list)
        for instance_status in instance_status_list:
            record_id_gby_status[instance_status["status"]].append(instance_status["record_id"])

        for status, record_ids in record_id_gby_status.items():
            models.SubscriptionInstanceRecord.objects.filter(id__in=record_ids).update(
                status=status, update_time=timezone.now()
            )
            log_and_print(f"transfer_record: {status}'s num -> {len(record_ids)}", execute_id=execute_id)
        return

    # 兼容订阅更新执行的情况，仅插件任务需要删除Pipeline记录
    to_be_deleted_pipelines_key = f"sub_{subscription_id}_to_be_deleted_pipeline_id"
    last_pipeline_ids_to_be_deleted = models.GlobalSettings.get_config(to_be_deleted_pipelines_key)
    if not last_pipeline_ids_to_be_deleted:
        models.GlobalSettings.set_config(to_be_deleted_pipelines_key, pipeline_ids_to_be_deleted)
    else:
        models.GlobalSettings.update_config(
            to_be_deleted_pipelines_key, list(set(last_pipeline_ids_to_be_deleted + pipeline_ids_to_be_deleted))
        )

    log_and_print(
        f"subscription_id -> {subscription_id}, save to_be_deleted_pipelines -> {to_be_deleted_pipelines_key}",
        execute_id=execute_id,
    )

    # 统计执行中的实例
    running_record_id_set = set()
    for instance_status in instance_status_list:
        if instance_status["status"] not in {constants.JobStatusType.PENDING, constants.JobStatusType.RUNNING}:
            continue

        running_record_id_set.add(instance_status["record_id"])
        # 强制失败第一个节点
        instance_status["status"] = constants.JobStatusType.FAILED
        sub_steps = list(itertools.chain(*[step["target_hosts"][0]["sub_steps"] for step in instance_status["steps"]]))

        if not sub_steps:
            continue

        # 找出第一个PENDING or RUNNING 的步骤
        first_running_step = None
        for index, sub_step in enumerate(sub_steps):
            if sub_step["status"] in {constants.JobStatusType.PENDING, constants.JobStatusType.RUNNING}:
                first_running_step = sub_step
                break

        # 没有正在执行的节点，那最后一个节点强制失败
        if not first_running_step:
            first_running_step = sub_steps[-1]

        first_running_step["status"] = constants.JobStatusType.FAILED
        first_running_step["log"] = (
            first_running_step.get("log", " ") + f"\n[{strftime_local(timezone.now())} ERROR] 任务长时间处在执行状态，已强制失败"
        )

    if running_record_id_set:
        log_and_print(
            f"subscription_id -> {subscription_id}, record_ids -> {running_record_id_set} 任务长时间处于执行状态，已强制失败",
            execute_id=execute_id,
        )

    action_steps_inst_status_list_map = {}
    inst_status_gby_inst_action_and_steps = defaultdict(lambda: defaultdict(list))
    for instance_status in instance_status_list:
        instance_action_str = json.dumps({step["id"]: step["action"] for step in instance_status["steps"]})
        sub_steps = list(itertools.chain(*[step["target_hosts"][0]["sub_steps"] for step in instance_status["steps"]]))
        steps_compress_str = ".".join(sub_step["node_name"] for sub_step in sub_steps)

        # 兼容相同操作动作，执行步骤不一致的情况（版本迭代重试旧任务导致）
        action_steps_inst_status_list_map[f"{instance_action_str}-{steps_compress_str}"] = instance_status

        inst_status_gby_inst_action_and_steps[instance_action_str][steps_compress_str].append(instance_status)

    create_pipeline_result = create_pipeline_from_instance_status(list(action_steps_inst_status_list_map.values()))

    pipeline = create_pipeline_result["pipeline"]
    act_gby_instance_action_and_steps = create_pipeline_result["act_gby_instance_action_and_steps"]
    step_info_gby_instance_action_and_steps = create_pipeline_result["step_info_gby_instance_action_and_steps"]

    actions = {}
    inst_record_detail_to_be_created = []
    for instance_action_str, inst_status_gby_steps in inst_status_gby_inst_action_and_steps.items():
        instance_action = json.loads(instance_action_str)
        for steps_compress_str, instance_statuses in inst_status_gby_steps.items():

            record_id_gby_status = defaultdict(list)
            for instance_status in instance_statuses:
                actions[instance_status["instance_id"]] = instance_action
                record_id_gby_status[instance_status["status"]].append(instance_status["record_id"])

            # 更新实例状态及步骤信息
            steps = step_info_gby_instance_action_and_steps[instance_action_str][steps_compress_str]
            for status, record_ids in record_id_gby_status.items():
                models.SubscriptionInstanceRecord.objects.filter(id__in=record_ids).update(
                    status=status,
                    steps=steps,
                    pipeline_id=steps[0]["pipeline_id"] if steps else None,
                    start_pipeline_id=steps[0]["pipeline_id"] if steps else None,
                    update_time=timezone.now(),
                )
                log_and_print(f"transfer_record: {status}'s num -> {len(record_ids)}", execute_id=execute_id)

            for instance_status in instance_statuses:
                sub_steps = list(
                    itertools.chain(*[step["target_hosts"][0]["sub_steps"] for step in instance_status["steps"]])
                )
                steps_compress_str = ".".join(sub_step["node_name"] for sub_step in sub_steps)

                index_act_map = {
                    act["index"]: act
                    for act in act_gby_instance_action_and_steps[instance_action_str][steps_compress_str]
                }
                for index, sub_step in enumerate(sub_steps):
                    if sub_step["status"] == constants.JobStatusType.PENDING:
                        break
                    inst_record_detail_to_be_created.append(
                        models.SubscriptionInstanceStatusDetail(
                            subscription_instance_record_id=instance_status["record_id"],
                            node_id=index_act_map[index]["id"],
                            status=sub_step["status"],
                            log=sub_step.get("log"),
                            update_time=sub_step.get("finish_time") or timezone.now(),
                            create_time=sub_step.get("start_time") or timezone.now(),
                        )
                    )

    task_ids_valid = set([inst_status["task_id"] for inst_status in instance_status_list])
    # 保存实例动作信息到task，便于此类任务的重试
    models.SubscriptionTask.objects.filter(id__in=task_ids_valid).update(
        pipeline_id=pipeline["id"], is_ready=True, actions=actions
    )

    # 创建实例状态详细
    models.SubscriptionInstanceStatusDetail.objects.bulk_create(inst_record_detail_to_be_created)

    log_and_print(
        f"inst_record_detail_to_be_created_num -> {len(inst_record_detail_to_be_created)}", execute_id=execute_id
    )

    # 创建pipeline，id重新生成，不会被下面的操作误删
    models.PipelineTree.objects.create(id=pipeline["id"], tree=pipeline)

    # 删除废弃Pipeline
    # clean_pipeline_data(pipeline_objs=pipeline_parser_inst.pipeline_trees)


def check_transfer_finished(instance_records: List[models.SubscriptionInstanceRecord]) -> bool:
    """检查订阅实例是否处在执行状态"""
    status_set = set([instance_record.status for instance_record in instance_records])
    if status_set & {constants.JobStatusType.PENDING, constants.JobStatusType.RUNNING}:
        return False
    return True


def transfer_record_slice(execute_id: int, subscription_id_slice: List[int], agent_sub_ids: Set[int]):
    error_sub_ids = []
    for index, subscription_id in enumerate(subscription_id_slice, 1):
        try:
            log_and_print(f"subscription_id -> {subscription_id} start", execute_id=execute_id)
            transfer_record(
                execute_id=execute_id, subscription_id=subscription_id, is_agent=subscription_id in agent_sub_ids
            )
        except Exception as error:
            error_sub_ids.append(subscription_id)
            traceback.print_exc()
            log_and_print(f"subscription_id -> {subscription_id}, error: {error}", execute_id=execute_id)
        log_and_print(
            f"subscription_id -> {subscription_id}, " f"{index} / {len(subscription_id_slice)}", execute_id=execute_id
        )
    return error_sub_ids


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("sub_id_range", nargs="+", type=int, help="subscription_id range(closed interval)")
        parser.add_argument("--enable", action="store_true", help="迁移enable=True的订阅任务")

    def handle(self, *args, **options):
        """
        迁移旧任务历史数据到重构Pipeline
        """
        begin_time = time.time()

        sub_id_begin, sub_id_end = tuple(options["sub_id_range"])

        if sub_id_end < sub_id_begin:
            raise CommandError(f"Wrong range -> [{sub_id_begin}, {sub_id_end}]")

        log_and_print(f"开始执行迁移：subscription id range -> [{sub_id_begin}, {sub_id_end}]")

        agent_sub_ids = set(
            models.Job.objects.filter(
                job_type__in=constants.JOB_TYPE_MAP["agent"] + constants.JOB_TYPE_MAP["proxy"]
            ).values_list("subscription_id", flat=True)
        )

        # 通过task pipeline反查需要迁移的订阅状态
        sub_ids_need_transfer = list(
            set(
                models.SubscriptionTask.objects.filter(
                    subscription_id__range=(sub_id_begin, sub_id_end), pipeline_id=""
                ).values_list("subscription_id", flat=True)
            )
        )

        sub_ids_need_transfer = list(
            models.Subscription.objects.filter(id__in=sub_ids_need_transfer, enable=options["enable"]).values_list(
                "id", flat=True
            )
        )

        log_and_print(f"迁移订阅数量 -> {len(sub_ids_need_transfer)}")

        # 随机打乱订阅ID，防止集中性的大范围订阅导致某一线程长时间RUNNING
        random.shuffle(sub_ids_need_transfer)

        begin, limit, index = 0, math.ceil(len(sub_ids_need_transfer) / 8), 1
        call_params_list = []
        while begin < len(sub_ids_need_transfer):
            call_params_list.append(
                {
                    "subscription_id_slice": sub_ids_need_transfer[begin : begin + limit],
                    "agent_sub_ids": agent_sub_ids,
                    "execute_id": index,
                }
            )
            index += 1
            begin += limit

        error_sub_ids = concurrent.batch_call(
            func=transfer_record_slice, params_list=call_params_list, get_data=lambda x: x, extend_result=True
        )

        log_and_print(
            f"迁移完成，subscription_id_range -> [{sub_id_begin}, {sub_id_end}], "
            f"error_subscription_ids -> {error_sub_ids}, total_cost -> {round(time.time() - begin_time, 2)}s"
        )
