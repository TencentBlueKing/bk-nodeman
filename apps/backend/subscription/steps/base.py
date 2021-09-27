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


import abc
from typing import List

from apps.node_man import constants as const
from apps.node_man.models import (
    ProcessStatus,
    Subscription,
    SubscriptionInstanceRecord,
    SubscriptionStep,
)


class Step(object, metaclass=abc.ABCMeta):
    """
    步骤基类
    """

    STEP_TYPE = ""

    def __init__(self, subscription_step: SubscriptionStep):
        """
        :param models.SubscriptionStep subscription_step: 订阅步骤
        """
        self.subscription_step = subscription_step

        # shortcut
        self.step_id = subscription_step.step_id
        self.subscription: Subscription = subscription_step.subscription

    def get_supported_actions(self):
        """
        获取插件支持的动作列表，键值对：{action_name: action_cls}
        """
        return {}

    def create_action(self, action_name: str, subscription_instances: List[SubscriptionInstanceRecord]):
        """
        获取步骤的动作处理类
        :param action_name: 动作名称
        :param subscription_instances: 订阅实例记录
        :rtype: Action
        """
        for name, action_cls in self.get_supported_actions().items():
            if name == action_name:
                return action_cls(action_name, self, subscription_instances)
        raise ValueError("action [%s] is not registered" % action_name)

    @abc.abstractmethod
    def make_instances_migrate_actions(self, instances, auto_trigger=False, preview_only=False, **kwargs):
        """
        计算实例变化所需要变更动作
        :param instances: list 变更后的实例列表
        :param auto_trigger: bool 是否自动触发
        :param preview_only: 是否仅预览，若为true则不做任何保存或执行动作
        :return: dict 需要对哪些实例做哪些动作
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_step_data(self, instance_info, target_host, agent_config):
        """
        根据当前实例及目标机器，获取步骤上下文数据数据
        """
        raise NotImplementedError

    def get_all_step_data(self, instance_info, target_host):
        from apps.backend.subscription.steps import StepFactory

        all_step_data = {
            step.step_id: StepFactory.get_step_manager(step).get_step_data(instance_info, target_host)
            for step in self.subscription.steps
        }
        return all_step_data


class Action(object, metaclass=abc.ABCMeta):
    """
    步骤动作调度器
    """

    # 动作名称
    ACTION_NAME = ""

    # 动作描述
    ACTION_DESCRIPTION = ""

    def __init__(self, action_name: str, step: Step, instance_record_ids: List[int]):
        """
        :param Step step: 步骤实例
        :param models.SubscriptionInstanceRecord instance_record_ids: 订阅实例执行记录
        """
        self.step = step
        self.instance_record_ids = instance_record_ids

    @abc.abstractmethod
    def generate_activities(self, *args, **kwargs):
        raise NotImplementedError

    def _update_or_create_process_status(self, bk_host_id, group_id, rewrite_path_info):
        if self.step.subscription.is_main:
            source_id = self.step.subscription.id
            source_type = ProcessStatus.SourceType.SUBSCRIPTION
        else:
            source_id = None
            source_type = ProcessStatus.SourceType.DEFAULT
            group_id = ""
        host_status, is_created = ProcessStatus.objects.get_or_create(
            bk_host_id=bk_host_id,
            name=self.step.plugin_name,
            source_id=source_id,
            source_type=source_type,
            group_id=group_id,
            proc_type=const.ProcType.PLUGIN,
            defaults=dict(
                rewrite_path_info,
                version=self.step.plugin_version,
            ),
        )

        if not is_created:
            for key, value in rewrite_path_info.items():
                setattr(host_status, key, value)
            host_status.version = self.step.plugin_version
            host_status.save()
        return host_status
