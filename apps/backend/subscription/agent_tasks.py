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
import traceback
from collections import OrderedDict
from typing import Dict, List

from apps.backend.subscription.errors import PluginValidationError
from apps.backend.subscription.steps import AgentStep, StepFactory
from apps.node_man import models
from apps.node_man.models import PipelineTree, SubscriptionInstanceRecord
from pipeline import builder

"""
TODO 此文件是为了兼容当前AGENT任务流程，后续把AGENT任务流程优化为多实例后（与插件流程一致）可废弃此文件
"""
logger = logging.getLogger("app")


def build_instance_task(
    record: SubscriptionInstanceRecord, step_actions: Dict[str, str], step_managers: Dict[str, AgentStep]
):
    """
    按实例执行任务
    :param SubscriptionInstanceRecord record: InstanceRecord
    :param step_actions: 步骤动作
            {
                "step_id_x": "INSTALL",
                "step_id_y": "UNINSTALL,
            }
    :param step_managers: dict 步骤管理器
            {
                "agent": AgentStep
            }
    构造形如以下的pipeline
               StartEvent
                   |
             ParallelGateway
                   |
          --------------------
          |                  |
     register_cmdb      register_cmdb
          |                  |
     install_agent      install_agent
          |                  |
       .......            .......
          |                  |
          --------------------
                   |
             ConvergeGateway
                   |
                EndEvent
    """
    instance_start = builder.EmptyStartEvent()
    instance_end = builder.EmptyEndEvent()
    current_node = instance_start

    for step_id in step_managers:
        if step_id not in step_actions:
            continue
        step_manager = step_managers[step_id]

        action_name = step_actions[step_manager.step_id]
        action_manager = step_manager.create_action(action_name, record)

        # 执行action&更新状态
        sub_processes = [action_manager.execute(record)]

        # 根据主机数量，生成并行网关
        step_name = "[{}] {}".format(step_id, action_manager.ACTION_DESCRIPTION)

        step_start = builder.EmptyStartEvent()
        step_end = builder.EmptyEndEvent()

        pg = builder.ParallelGateway()
        cg = builder.ConvergeGateway()
        step_start.extend(pg).connect(*sub_processes).to(pg).converge(cg).extend(step_end)

        step_pipeline = builder.SubProcess(start=step_start, name=step_name)
        action_manager.set_pipeline_id(step_pipeline.id)
        current_node = current_node.extend(step_pipeline)

    current_node.extend(instance_end)

    return instance_start


def build_task(
    subscription_task: models.SubscriptionTask,
    instances_action: Dict[str, Dict[str, str]],
    instance_records: List[models.SubscriptionInstanceRecord],
):
    """
    批量执行实例的步骤的动作
    :param subscription_task: 订阅任务
    :param instances_action: {
        "instance_id_xxx": {
            "step_id_x": "INSTALL",
            "step_id_y": "UNINSTALL,
        }
    }
    :param instance_records 订阅实例记录
    """
    subscription = subscription_task.subscription

    instance_records_dict = {record.instance_id: record for record in instance_records}

    step_managers = OrderedDict()
    step_data = []
    for step in subscription.steps:
        step_managers[step.step_id] = StepFactory.get_step_manager(step)
        step_data.append({"id": step.step_id, "type": step.type, "pipeline_id": "", "action": None, "extra_info": {}})

    to_be_saved_records = []
    to_be_saved_pipelines = []
    to_be_displayed_errors = []
    # 对每个实例执行指定动作
    for instance_id, step_actions in instances_action.items():
        record = instance_records_dict[instance_id]

        try:
            record.steps = step_data
            instance_task = build_instance_task(record, step_actions, step_managers)
        except PluginValidationError as err:
            # 插件操作系统不支持，忽略该实例
            logger.error(str(err))
            logger.error(traceback.format_exc())
            to_be_displayed_errors.append(str(err))
            continue

        # 构建 Pipeline 拓扑
        pipeline_tree = builder.build_tree(instance_task)
        pipeline_id = pipeline_tree["id"]
        record.pipeline_id = pipeline_id

        to_be_saved_records.append(record)
        to_be_saved_pipelines.append(
            PipelineTree(
                id=pipeline_id,
                tree=pipeline_tree,
            )
        )

    return to_be_saved_records, to_be_saved_pipelines, to_be_displayed_errors
