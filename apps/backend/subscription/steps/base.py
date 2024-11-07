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


import abc
from typing import Any, Dict, List, Optional, Tuple, Union

from django.conf import settings
from django.utils.translation import get_language

from apps.node_man import models
from pipeline import builder
from pipeline.builder.flow.base import Element


class Step(object, metaclass=abc.ABCMeta):
    """
    步骤基类
    """

    STEP_TYPE = ""

    subscription: models.Subscription = None
    subscription_step: models.SubscriptionStep = None
    step_id: str = None

    def __init__(self, subscription_step: models.SubscriptionStep):
        """
        :param models.SubscriptionStep subscription_step: 订阅步骤
        """
        self.subscription_step: models.SubscriptionStep = subscription_step

        # shortcut
        self.step_id: str = subscription_step.step_id
        self.subscription: models.Subscription = subscription_step.subscription

    def get_supported_actions(self):
        """
        获取插件支持的动作列表，键值对：{action_name: action_cls}
        """
        return {}

    def create_action(self, action_name: str, subscription_instances: List[models.SubscriptionInstanceRecord]):
        """
        获取步骤的动作处理类
        :param action_name: 动作名称
        :param subscription_instances: 订阅实例记录
        :rtype: Action
        """
        action_cls = self.get_supported_actions().get(action_name)
        if not action_cls:
            raise ValueError(f"action -> {action_name} is not registered")
        return action_cls(action_name, self, subscription_instances)

    @abc.abstractmethod
    def make_instances_migrate_actions(
        self, instances: Dict[str, Dict[str, Union[Dict, Any]]], auto_trigger=False, preview_only=False, **kwargs
    ):
        """
        计算实例变化所需要变更动作
        :param instances: list 变更后的实例列表
        :param auto_trigger: bool 是否自动触发
        :param preview_only: 是否仅预览，若为true则不做任何保存或执行动作
        :return: dict 需要对哪些实例做哪些动作
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_step_data(
        self, instance_info: Dict, target_host: models.Host, agent_config: Dict[str, Union[Dict, str]]
    ) -> Dict:
        """
        根据当前实例及目标机器，获取步骤上下文数据数据
        :param instance_info: 主机实例信息
        :param target_host: 目标主机
        :param agent_config: models.AccessPoint.agent_config 接入点中有关Agent的路径信息
        :return:
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
    ACTION_NAME: str = ""

    # 动作描述
    ACTION_DESCRIPTION: str = ""

    def __init__(self, action_name: str, step: Step, instance_record_ids: List[int]):
        """
        :param Step step: 步骤实例
        :param models.SubscriptionInstanceRecord instance_record_ids: 订阅实例执行记录
        """
        self.action_name: str = action_name
        self.step: Step = step
        self.instance_record_ids = instance_record_ids

    def inject_vars_to_global_data(self, global_pipeline_data: builder.Data, meta: Dict[str, Any]):
        """
        注入流程公共变量
        参考：https://github.com/TencentBlueKing/bamboo-engine/blob/master/docs/user_guide/flow_orchestration.md
        增加公共变量后，在相应的 manager ServiceActivity 基类添加相关的变量引用
        :param global_pipeline_data: 全局pipeline公共变量
        :param meta: 任务元数据
        :return:
        """
        # locale
        blueking_language: str = self.step.subscription_step.params.get("blueking_language")
        if blueking_language not in settings.SUPPORT_LANGUAGE:
            blueking_language = get_language()
        global_pipeline_data.inputs["${blueking_language}"] = builder.Var(
            type=builder.Var.PLAIN, value=blueking_language
        )

    @abc.abstractmethod
    def generate_activities(
        self,
        subscription_instances: List[models.SubscriptionInstanceRecord],
        global_pipeline_data: builder.Data,
        meta: Dict[str, Any],
        current_activities=None,
        is_multi_paralle_gateway=False,
    ) -> Tuple[List[Union[builder.ServiceActivity, Element]], Optional[builder.Data]]:
        raise NotImplementedError
