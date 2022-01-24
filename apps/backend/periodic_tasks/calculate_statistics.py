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


import itertools
import logging
from collections import Counter, defaultdict

from celery.task import periodic_task
from django.utils import timezone

from apps.backend.subscription import task_tools
from apps.node_man import constants, models, tools

logger = logging.getLogger("celery")


@periodic_task(run_every=30, queue="backend", options={"queue": "backend"}, ignore_result=True)
def calculate_statistics():
    """
    统计任务汇总状态
    """
    logger.info("calculate_statistics begin.")
    jobs = list(
        models.Job.objects.filter(
            status__in=[
                constants.JobStatusType.RUNNING,
                constants.JobStatusType.PENDING,
                constants.JobStatusType.TERMINATED,
            ]
        ).exclude(job_type__in=[constants.JobType.PACKING_PLUGIN])
    )

    agent_subscription_ids = [
        job.subscription_id
        for job in jobs
        if job.job_type.rsplit("_")[-1] in [constants.SubStepType.PROXY, constants.SubStepType.AGENT]
    ]
    # Agent任务兼容原先的订阅，需要将状态更新至InstanceRecord
    logger.info(f"calculate_statistics: agent_subscription_ids -> {agent_subscription_ids}")
    task_tools.transfer_instance_record_status(agent_subscription_ids)

    subscription_ids = [job.subscription_id for job in jobs]

    task_infos = models.SubscriptionTask.objects.filter(
        subscription_id__in=subscription_ids, id__in=list(itertools.chain(*[job.task_id_list for job in jobs]))
    ).values("id", "subscription_id", "is_ready", "err_msg", "is_auto_trigger")
    task_id__task_infos_map = {task_info["id"]: task_info for task_info in task_infos}

    # 仅过滤出任务创建完成（is_ready=True）的实例
    instance_record_infos = models.SubscriptionInstanceRecord.objects.filter(
        subscription_id__in=subscription_ids,
        task_id__in=[task_info["id"] for task_info in task_infos if task_info["is_ready"]],
    ).values("subscription_id", "task_id", "status", "instance_id", "id")

    instance_record_infos_gby_task_id = defaultdict(list)
    for instance_record_info in instance_record_infos:
        instance_record_infos_gby_task_id[instance_record_info["task_id"]].append(instance_record_info)

    job_ids_gby_reason = {
        "TASK_NOT_EXIST": [],
        "TASK_NOT_READY": [],
        "CREATE_TASK_FAILED": [],
        "SUCCESS": [],
        "FAILED": [],
    }
    for job in jobs:

        try:
            latest_task_info = task_id__task_infos_map.get(max(job.task_id_list or [-1]))

            # 任务不存在，创建订阅任务时抛出异常导致该订阅任务被删除
            if not latest_task_info:
                # TODO 这类情况如果能在任务历史列表给个提示报错就很好，然后回退到上一task_id_list的状态统计，此处暂不处理
                job_ids_gby_reason["TASK_NOT_EXIST"].append(job.id)
                continue

            # 订阅任务还未准备就绪
            if not latest_task_info["is_ready"]:
                # 暂时没有报错信息，属于正常创建过程，此时暂不同步
                if not latest_task_info["err_msg"]:
                    job_ids_gby_reason["TASK_NOT_READY"].append(latest_task_info)
                    continue
                # 有错误信息，此时任务创建失败，和上述TODO一样的建议，此处将状态修改为失败
                job_ids_gby_reason["CREATE_TASK_FAILED"].append(job.id)
                job.global_params.update({latest_task_info["id"]: {"err_msg": latest_task_info["err_msg"]}})
                job.status = constants.JobStatusType.FAILED
                job.end_time = timezone.now()
                job.save(update_fields=["status", "end_time", "global_params"])
                continue

            # 同一任务中，不同task_id间可能存在相同instance_id的数据（例如重试场景）
            duplicate_instance_record_infos = itertools.chain(
                *[instance_record_infos_gby_task_id.get(task_id, []) for task_id in job.task_id_list]
            )

            # 实例id（instance_id） - 最新记录映射 ｜ 最新记录是指同一 instance_id 下最后创建的记录，是当前任务下某实例的最新状态
            # 此处不能用SubscriptionInstanceRecord.is_latest 字段进行筛选 - SaaS侧同一订阅可能下发多Job记录
            # 最早创建的Job通过task_id_list关联的 SubscriptionInstanceRecord is_latest可能全是False（例如策略的调整目标）
            instance_id__latest_record_map = {}
            for instance_record_info in duplicate_instance_record_infos:
                instance_id = instance_record_info["instance_id"]
                current_record = instance_id__latest_record_map.get(instance_id, {})

                # 通过 id 确定最新创建的记录，初次赋值使用假id=-1， 使得赋值条件必成立，减少特殊判断
                if current_record.get("id", -1) < instance_record_info["id"]:
                    instance_id__latest_record_map[instance_id] = instance_record_info

            status_counter = dict(
                Counter([latest_record["status"] for latest_record in instance_id__latest_record_map.values()])
            )
            tools.JobTools.update_job_statistics(job, status_counter)

            job_ids_gby_reason["SUCCESS"].append(job.id)

        except Exception as err:
            job_ids_gby_reason["FAILED"].append(job.id)
            logger.error(
                f"calculate_statistics error: job_id -> {job.id}, subscription_id -> {job.subscription_id}, "
                f"err_msg -> {err}"
            )
            logger.exception(err)

    logger.info(f"calculate_statistics finished: job_ids_gby_reason -> {job_ids_gby_reason}")
