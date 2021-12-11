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
from __future__ import absolute_import, unicode_literals

import json
import logging
import time
import traceback
from collections import OrderedDict, defaultdict
from copy import deepcopy
from functools import wraps
from typing import Any, Dict, List, Union

from django.utils.translation import ugettext as _

from apps.backend.celery import app
from apps.backend.components.collections.base import ActivityType
from apps.backend.subscription import agent_tasks, tools
from apps.backend.subscription.constants import TASK_HOST_LIMIT
from apps.backend.subscription.errors import SubscriptionInstanceEmpty
from apps.backend.subscription.steps import StepFactory
from apps.backend.subscription.steps.agent import InstallAgent, InstallProxy
from apps.node_man import constants, models
from apps.node_man import tools as node_man_tools
from apps.node_man.handlers.cmdb import CmdbHandler
from pipeline import builder
from pipeline.builder import Data, NodeOutput, ServiceActivity, Var
from pipeline.core.pipeline import Pipeline
from pipeline.parser import PipelineParser
from pipeline.service import task_service

logger = logging.getLogger("app")


def mark_acts_tail_and_head(activities: List[ServiceActivity]) -> None:
    """标记头尾节点，用于在开始和结束时实现一些钩子"""
    if len(activities) == 1:
        activities[0].component.inputs.act_type = Var(type=Var.PLAIN, value=ActivityType.HEAD_TAIL)
        return
    activities[0].component.inputs.act_type = Var(type=Var.PLAIN, value=ActivityType.HEAD)
    activities[-1].component.inputs.act_type = Var(type=Var.PLAIN, value=ActivityType.TAIL)


def build_instances_task(
    subscription_instances: List[models.SubscriptionInstanceRecord],
    step_actions: Dict[str, str],
    subscription: models.Subscription,
    global_pipeline_data: Data,
):
    """
    对同类step_actions任务进行任务编排
    :param subscription_instances: 订阅实例列表
    :param step_actions: {"basereport": "MAIN_INSTALL_PLUGIN"}
    :param subscription: 订阅对象
    :param global_pipeline_data: 全局pipeline变量
    :return:
    """
    # 首先获取当前订阅对应步骤的工厂类
    step_id_manager_map = OrderedDict()
    for step in subscription.steps:
        step_id_manager_map[step.step_id] = StepFactory.get_step_manager(step)
    step_map = {step.step_id: step for step in subscription.steps}
    step_id_record_step_map = {
        step_id: {"id": step_id, "type": step_map[step_id].type, "pipeline_id": "", "action": action, "extra_info": {}}
        for step_id, action in step_actions.items()
    }

    # 对流程步骤进行编排
    current_activities = []
    for step_id in step_id_manager_map:
        if step_id not in step_actions:
            continue
        step_manager = step_id_manager_map[step_id]

        action_name = step_actions[step_manager.step_id]
        action_manager = step_manager.create_action(action_name, subscription_instances)

        activities, pipeline_data = action_manager.generate_activities(
            subscription_instances, current_activities=current_activities
        )

        # 记录每个step的起始id及步骤名称
        step_id_record_step_map[step_id].update(
            pipeline_id=activities[0].id, node_name=f"[{step_id}] {action_manager.ACTION_DESCRIPTION}"
        )

        current_activities.extend(activities)

    mark_acts_tail_and_head(current_activities)
    subscription_instance_ids = [sub_inst.id for sub_inst in subscription_instances]

    # 每个原子引用上个原子成功输出的 succeeded_subscription_instance_ids
    for index, act in enumerate(current_activities):
        if index == 0:
            # 第一个activity 需传入初始的 subscription_instance_ids
            act.component.inputs.subscription_instance_ids = Var(type=Var.PLAIN, value=subscription_instance_ids)
            continue

        source_act_id = current_activities[index - 1].id
        succeeded_ids_output_name = f"${{succeeded_subscription_instance_ids_{act.id}}}"
        act.component.inputs.succeeded_subscription_instance_ids = Var(type=Var.SPLICE, value=succeeded_ids_output_name)
        global_pipeline_data.inputs[succeeded_ids_output_name] = NodeOutput(
            type=Var.SPLICE, source_act=source_act_id, source_key="succeeded_subscription_instance_ids"
        )

    instance_start = current_activities[0]
    current_node = deepcopy(instance_start)
    # 用extend串联这些activities
    for act in current_activities:
        if act:
            current_node = current_node.extend(act)

    models.SubscriptionInstanceRecord.objects.filter(id__in=subscription_instance_ids).update(
        pipeline_id=instance_start.id, steps=list(step_id_record_step_map.values())
    )
    return instance_start


def create_pipeline(
    subscription: models.Subscription,
    instances_action: Dict[str, Dict[str, str]],
    subscription_instances: List[models.SubscriptionInstanceRecord],
) -> Pipeline:
    """
      批量执行实例的步骤的动作
      :param subscription: Subscription
      :param instances_action: {
          "instance_id_xxx": {
              "step_id_x": "INSTALL",
              "step_id_y": "UNINSTALL,
          }
      }
      :param subscription_instances
    构造形如以下的pipeline，根据 ${TASK_HOST_LIMIT} 来决定单条流水线的执行机器数量
                         StartEvent
                             |
                      ParallelGateway
                             |
          ---------------------------------------
          |                  |                  |
    500_host_init      500_host_init         .......
          |                  |                  |
    install_plugin     install_plugin        .......
          |                  |                  |
    render_config      render_config         .......
          |                  |                  |
       .......            .......            .......
          |                  |                  |
          ---------------------------------------
                             |
                       ConvergeGateway
                             |
                          EndEvent
    """
    start_event = builder.EmptyStartEvent()

    subscription_instance_map = {
        subscription_instance.instance_id: subscription_instance for subscription_instance in subscription_instances
    }

    # 把同类型操作进行聚合
    action_instances = defaultdict(list)
    for instance_id, step_actions in instances_action.items():
        if instance_id in subscription_instance_map:
            action_instances[json.dumps(step_actions)].append(subscription_instance_map[instance_id])

    global_pipeline_data = Data()
    sub_processes = []
    for step_actions, instances in action_instances.items():
        step_actions = json.loads(step_actions)
        start = 0
        while start < len(instances):
            activities_start_event = build_instances_task(
                instances[start : start + TASK_HOST_LIMIT], step_actions, subscription, global_pipeline_data
            )
            sub_processes.append(activities_start_event)
            start = start + TASK_HOST_LIMIT
    parallel_gw = builder.ParallelGateway()
    converge_gw = builder.ConvergeGateway()
    end_event = builder.EmptyEndEvent()
    start_event.extend(parallel_gw).connect(*sub_processes).to(parallel_gw).converge(converge_gw).extend(end_event)

    # 构造pipeline树
    tree = builder.build_tree(start_event, data=global_pipeline_data)
    models.PipelineTree.objects.create(id=tree["id"], tree=tree)

    parser = PipelineParser(pipeline_tree=tree)
    pipeline = parser.parse()
    return pipeline


def create_task_transaction(create_task_func):
    """创建任务事务装饰器，用于创建时发生异常时记录错误或抛出异常回滚"""

    @wraps(create_task_func)
    def wrapper(subscription: models.Subscription, subscription_task: models.SubscriptionTask, *args, **kwargs):
        try:
            func_return = create_task_func(subscription, subscription_task, *args, **kwargs)
        except Exception as err:
            logger.exception(err)
            if subscription_task.is_auto_trigger or kwargs.get("preview_only"):
                # 自动触发的发生异常或者仅预览的情况，记录日志后直接删除此任务即可
                models.SubscriptionTask.objects.filter(id=subscription_task.id).delete()
                # 抛出异常用于前端展示或事务回滚
                raise err
            # 非自动触发的，记录错误信息
            subscription_task.err_msg = str(err)
            subscription_task.save(update_fields=["err_msg"])
        else:
            if kwargs.get("preview_only"):
                # 仅预览，不执行动作
                return func_return
            subscription_task.is_ready = True
            logger.info(f"subscription_task[{subscription_task.id}] is ready, actions:{subscription_task.actions}")
            subscription_task.save(update_fields=["is_ready"])
            # 创建好实例后立刻执行
            run_subscription_task(subscription_task)
            return func_return

    return wrapper


@app.task(queue="backend")
@create_task_transaction
def create_task(
    subscription: models.Subscription,
    subscription_task: models.SubscriptionTask,
    instances: Dict[str, Dict[str, Union[Dict, Any]]],
    instance_actions: Dict[str, Dict[str, str]],
    preview_only: bool = False,
):
    """
    创建执行任务
    :param preview_only: 是否仅预览
    :param subscription: Subscription
    :param subscription_task: SubscriptionTask
    :param instances: dict
    :param instance_actions: {
        "instance_id_xxx": {
            "step_id_x": "INSTALL",
            "step_id_y": "UNINSTALL,
        }
    }
    :return: SubscriptionTask
    """

    instance_id_list = list(instance_actions.keys())

    batch_size = models.GlobalSettings.get_config("BATCH_SIZE", default=100)
    bk_host_ids = {
        instance_info["host"]["bk_host_id"]
        for instance_info in instances.values()
        if instance_info["host"].get("bk_host_id")
    }
    plugin__host_id__bk_obj_sub_map = {}

    # 前置错误需要跳过的主机，不创建订阅任务实例
    error_hosts = []

    topo_order = CmdbHandler.get_topo_order()
    # 批量创建订阅实例执行记录
    to_be_created_records_map = {}
    for instance_id, step_action in instance_actions.items():
        if instance_id not in instances:
            # instance_id不在instances中，则说明该实例可能已经不在该业务中，因此无法操作，故不处理。
            continue

        # 新装AGENT或PROXY会保存安装信息，需要清理
        need_clean = step_action.get("agent") in [
            InstallAgent.ACTION_NAME,
            InstallProxy.ACTION_NAME,
        ]
        instance_info = instances[instance_id]
        host_info = instance_info["host"]
        record = models.SubscriptionInstanceRecord(
            task_id=subscription_task.id,
            subscription_id=subscription.id,
            instance_id=instance_id,
            instance_info=instance_info,
            steps=[],
            is_latest=True,
            need_clean=need_clean,
        )
        record.subscription = subscription

        # agent 任务无需检查抑制情况
        if "agent" in step_action:
            to_be_created_records_map[instance_id] = record
            continue

        is_suppressed = False
        for step_id, action in step_action.items():
            if step_id in plugin__host_id__bk_obj_sub_map:
                host_id__bk_obj_sub_map = plugin__host_id__bk_obj_sub_map.get(step_id)
            else:
                host_id__bk_obj_sub_map = models.Subscription.get_host_id__bk_obj_sub_map(bk_host_ids, step_id)
                plugin__host_id__bk_obj_sub_map[step_id] = host_id__bk_obj_sub_map

            # 检查订阅策略间的抑制关系
            result = subscription.check_is_suppressed(
                action=action,
                cmdb_host_info=record.instance_info["host"],
                topo_order=topo_order,
                host_id__bk_obj_sub_map=host_id__bk_obj_sub_map,
            )
            is_suppressed = result["is_suppressed"]
            if is_suppressed:
                # 策略被抑制，跳过部署，记为已忽略
                error_hosts.append(
                    {
                        "ip": host_info["bk_host_innerip"],
                        "bk_host_id": host_info.get("bk_host_id"),
                        "bk_biz_id": host_info.get("bk_biz_id"),
                        "bk_cloud_id": host_info.get("bk_cloud_id"),
                        "suppressed_by_id": result["suppressed_by"]["subscription_id"],
                        "suppressed_by_name": result["suppressed_by"]["name"],
                        "os_type": node_man_tools.HostV2Tools.get_os_type(host_info),
                        "status": constants.JobStatusType.IGNORED,
                        "msg": _(
                            "当前{category_alias}（{bk_obj_name} 级）"
                            "已被优先级更高的{suppressed_by_category_alias}【{suppressed_by_name}(ID: {suppressed_by_id})】"
                            "（{suppressed_by_obj_name} 级）抑制"
                        ).format(
                            category_alias=models.Subscription.CATEGORY_ALIAS_MAP[result["category"]],
                            bk_obj_name=constants.CmdbObjectId.OBJ_ID_ALIAS_MAP.get(
                                result["sub_inst_bk_obj_id"],
                                constants.CmdbObjectId.OBJ_ID_ALIAS_MAP[constants.CmdbObjectId.CUSTOM],
                            ),
                            suppressed_by_category_alias=models.Subscription.CATEGORY_ALIAS_MAP[
                                result["suppressed_by"]["category"]
                            ],
                            suppressed_by_name=result["suppressed_by"]["name"],
                            suppressed_by_id=result["suppressed_by"]["subscription_id"],
                            suppressed_by_obj_name=constants.CmdbObjectId.OBJ_ID_ALIAS_MAP.get(
                                result["suppressed_by"]["bk_obj_id"],
                                constants.CmdbObjectId.OBJ_ID_ALIAS_MAP[constants.CmdbObjectId.CUSTOM],
                            ),
                        ),
                    }
                )
                break
        if is_suppressed:
            continue
        to_be_created_records_map[instance_id] = record

    # 保存instance_actions，用于重试场景
    subscription_task.actions = instance_actions
    if preview_only:
        # 仅做预览，不执行下面的代码逻辑，直接返回计算后的结果
        return {
            "to_be_created_records_map": to_be_created_records_map,
            "error_hosts": error_hosts,
        }

    # 这里反写到 job 表里，与SaaS逻辑耦合了，需解耦
    if error_hosts:
        models.Job.objects.filter(subscription_id=subscription.id, task_id_list__contains=subscription_task.id).update(
            error_hosts=error_hosts
        )

    if not to_be_created_records_map:
        logger.warning(
            "subscription_task[{subscription_task_id}] 没有需要执行的主机".format(subscription_task_id=subscription_task.id)
        )
        if subscription_task.is_auto_trigger:
            # 如果是自动触发，且没有任何实例，那么直接抛出异常，回滚数据库
            raise SubscriptionInstanceEmpty()

        # 非自动触发的直接退出即可
        return {
            "to_be_created_records_map": to_be_created_records_map,
            "error_hosts": error_hosts,
        }

    # TODO 判断是否AGENT类型的任务，待AGENT流程统一化后干掉此处差异的逻辑分支
    is_agent = "agent" in step_action
    if is_agent:
        to_be_saved_records, to_be_saved_pipelines, to_be_displayed_errors = agent_tasks.build_task(
            subscription_task, instance_actions, to_be_created_records_map.values()
        )
        models.PipelineTree.objects.bulk_create(to_be_saved_pipelines, batch_size=batch_size)

    # 将最新属性置为False并批量创建订阅实例
    models.SubscriptionInstanceRecord.objects.filter(
        subscription_id=subscription.id,
        instance_id__in=instance_id_list,
    ).update(is_latest=False)
    models.SubscriptionInstanceRecord.objects.bulk_create(to_be_created_records_map.values(), batch_size=batch_size)

    if not is_agent:

        # 批量创建订阅实例，由于bulk_create返回的objs没有主键，此处需要重新查出
        created_instance_records = list(
            models.SubscriptionInstanceRecord.objects.filter(
                subscription_id=subscription.id, instance_id__in=instance_id_list, is_latest=True
            )
        )

        pipeline = create_pipeline(subscription, instance_actions, created_instance_records)
        # 保存pipeline id
        subscription_task.pipeline_id = pipeline.id
    subscription_task.save(update_fields=["actions", "pipeline_id"])
    logger.info(
        "subscription({}),subscription_task({})  execute actions: {}".format(
            subscription.id, subscription_task.id, instance_actions
        )
    )
    return {
        "to_be_created_records_map": to_be_created_records_map,
        "error_hosts": error_hosts,
    }


def run_subscription_task_and_create_instance_transaction(func):
    """创建任务事务装饰器，用于创建时发生异常时记录错误或抛出异常回滚"""

    @wraps(func)
    def wrapper(subscription: models.Subscription, subscription_task: models.SubscriptionTask, *args, **kwargs):
        try:
            func_result = func(subscription, subscription_task, *args, **kwargs)
        except Exception as err:
            logger.exception(err)
            if subscription_task.is_auto_trigger or kwargs.get("preview_only"):
                # 自动触发的发生异常或者仅预览的情况
                # 记录日志后直接删除此任务即可
                models.SubscriptionTask.objects.filter(id=subscription_task.id).delete()
                # 抛出异常用于前端展示或事务回滚
                raise err
            # 任务创建失败is_ready置为False，防止create_task_transaction置为True但实际任务创建失败的情况
            # 例如：can not find celery workers - pipeline run 报错
            subscription_task.is_ready = False
            # 非自动触发的，记录错误信息
            subscription_task.err_msg = str(err)
            subscription_task.save(update_fields=["err_msg", "is_ready"])
        else:
            return func_result

    return wrapper


@app.task(queue="backend")
@run_subscription_task_and_create_instance_transaction
def run_subscription_task_and_create_instance(
    subscription: models.Subscription,
    subscription_task: models.SubscriptionTask,
    scope: Dict = None,
    actions: Dict = None,
    preview_only: bool = False,
):
    """
    自动检查实例及配置的变更，执行相应动作
    :param preview_only: 是否仅预览，若为true则不做任何保存或执行动作
    :param subscription: Subscription
    :param subscription_task: SubscriptionTask
    :param scope
    {
        "bk_biz_id": 2,
        "nodes": [],
        "node_type": "INSTANCE",
        "object_type": "HOST"
    }
    :param actions {
        "step_id_xxx": "INSTALL"
    }
    """
    # 如果不传范围，则使用订阅全部范围
    if not scope:
        scope = subscription.scope
    else:
        scope["object_type"] = subscription.object_type
        scope["bk_biz_id"] = subscription.bk_biz_id

    # 获取订阅范围内全部实例
    instances = tools.get_instances_by_scope(scope)
    logger.info(f"run_subscription_task[{subscription_task.id}] instances_num={len(instances)}")
    # 创建步骤管理器实例
    step_managers = {step.step_id: StepFactory.get_step_manager(step) for step in subscription.steps}
    # 删除无用subscription缓存，否则执行延时任务时传入可能引起pickle异常
    if hasattr(subscription, "_steps"):
        delattr(subscription, "_steps")

    logger.info(f"run_subscription_task[{subscription_task.id}] step_managers={step_managers}")
    if actions is not None:
        # 指定了动作，不需要计算，直接执行即可
        instance_actions = {instance_id: actions for instance_id in instances}
        create_task(subscription, subscription_task, instances, instance_actions)
        return

    # 按步骤顺序计算实例变更所需的动作
    instance_actions = defaultdict(dict)
    instance_migrate_reasons = defaultdict(dict)
    for step in step_managers.values():
        # 计算变更的动作
        migrate_results = step.make_instances_migrate_actions(
            instances, auto_trigger=subscription_task.is_auto_trigger, preview_only=preview_only
        )
        # 归类变更动作
        instance_id_action_map = migrate_results["instance_actions"]
        for instance_id, action in instance_id_action_map.items():
            instance_actions[instance_id][step.step_id] = action

        # 归类变更原因
        instance_id_action_reason_map = migrate_results["migrate_reasons"]
        for instance_id, migrate_reason in instance_id_action_reason_map.items():
            instance_migrate_reasons[instance_id][step.step_id] = migrate_reason

    logger.info(
        f"subscription_task -> {subscription_task.id}, execute result -> make_instances_migrate_actions: \n"
        f"instance_actions -> {instance_actions} \n migrate_reasons -> {instance_migrate_reasons}"
    )

    # 查询被从范围内移除的实例
    instance_not_in_scope = [instance_id for instance_id in instance_actions if instance_id not in instances]

    if instance_not_in_scope:
        deleted_id_not_in_scope = []
        for instance_id in instance_not_in_scope:
            if subscription.object_type == models.Subscription.ObjectType.HOST:
                host_key = tools.parse_node_id(instance_id)["id"]
                deleted_id_not_in_scope.append(tools.parse_host_key(host_key))
            else:
                service_instance_id = tools.parse_node_id(instance_id)["id"]
                deleted_id_not_in_scope.append({"id": service_instance_id})

        deleted_instance_info = tools.get_instances_by_scope(
            {
                "bk_biz_id": subscription.bk_biz_id,
                "object_type": subscription.object_type,
                "node_type": models.Subscription.NodeType.INSTANCE,
                "nodes": deleted_id_not_in_scope,
            }
        )

        # 如果被删掉的实例在 CMDB 找不到，那么就使用最近一次的 InstanceRecord 的快照数据
        not_exist_instance_id = set(instance_not_in_scope) - set(deleted_instance_info)

        if not_exist_instance_id:
            records = models.SubscriptionInstanceRecord.objects.filter(
                subscription_id=subscription.id, instance_id__in=not_exist_instance_id, is_latest=True
            )
            for record in records:
                deleted_instance_info[record.instance_id] = record.instance_info

        instances.update(deleted_instance_info)

    create_task_result = create_task(
        subscription, subscription_task, instances, instance_actions, preview_only=preview_only
    )

    return {
        "to_be_created_records_map": create_task_result["to_be_created_records_map"],
        "error_hosts": create_task_result["error_hosts"],
        "instance_actions": instance_actions,
        "instance_migrate_reasons": instance_migrate_reasons,
        "instance_id__inst_info_map": instances,
    }


@app.task(queue="backend")
def run_subscription_task(subscription_task: models.SubscriptionTask):
    logger.info(f"debug update_subscription enter run_subscription_task[{subscription_task.id}]")
    pipeline_ids = {}
    if subscription_task.pipeline_id:
        pipeline_ids[subscription_task.pipeline_id] = 0
    else:
        for index, record in enumerate(subscription_task.instance_records):
            pipeline_ids[record.pipeline_id] = index

    from apps.node_man.models import PipelineTree

    pipelines = PipelineTree.objects.filter(id__in=list(pipeline_ids.keys()))
    ordered_pipelines = []
    for pipeline in pipelines:
        ordered_pipelines.append((pipeline_ids[pipeline.id], pipeline))
    # 排序
    ordered_pipelines.sort(key=lambda item: item[0])
    for index, pipeline in ordered_pipelines:
        pipeline.run(index % 255)


@app.task(queue="backend")
def retry_node(node_id: str):
    task_service.retry_activity(node_id)


@app.task(queue="backend")
def set_record_status(instance_record_ids: List[str], status: str, delay_seconds: float):
    # 不允许长时间占用资源
    time.sleep(delay_seconds if delay_seconds < 2 else 2)
    models.SubscriptionInstanceRecord.objects.filter(id__in=instance_record_ids).update(status=status)


@app.task(queue="backend_additional_task", ignore_result=True)
def update_subscription_instances_chunk(subscription_ids: List[int]):
    """
    分片更新订阅状态
    """
    subscriptions = models.Subscription.objects.filter(id__in=subscription_ids, enable=True, is_deleted=False)
    for subscription in subscriptions:
        try:
            if subscription.is_running():
                logger.info(
                    "[update_subscription_instances] subscription({subscription_id}) "
                    "task created failed, some instances is running".format(subscription_id=subscription.id)
                )
                continue

            # 创建订阅任务记录
            subscription_task = models.SubscriptionTask.objects.create(
                subscription_id=subscription.id,
                scope=subscription.scope,
                actions={},
                is_auto_trigger=True,
            )
            run_subscription_task_and_create_instance(subscription, subscription_task)
            logger.info(
                "[update_subscription_instances] subscription({subscription_id}) "
                "task created successful, task_id({task_id})".format(
                    subscription_id=subscription.id, task_id=subscription_task.id
                )
            )
        except SubscriptionInstanceEmpty:
            logger.info(
                "[update_subscription_instances] subscription({subscription_id}) "
                "has no change, do nothing.".format(subscription_id=subscription.id)
            )
        except Exception as e:
            logger.exception(
                "[update_subscription_instances] subscription({subscription_id}) task created failed, "
                "exception: {message}, {e}".format(subscription_id=subscription.id, message=traceback.format_exc(), e=e)
            )
