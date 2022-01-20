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
from apps.backend.subscription.steps.agent import AgentStep
from apps.backend.subscription.steps.plugin import PluginStep

SUPPORTED_STEPS = {"PLUGIN": PluginStep, "AGENT": AgentStep}


class StepFactory(object):
    @classmethod
    def get_step_manager(cls, subscription_step):
        cache_step = getattr(subscription_step, "step_manager", None)
        if cache_step:
            return cache_step
        step_type = subscription_step.type
        try:
            step_cls = SUPPORTED_STEPS[step_type]
        except KeyError:
            raise KeyError(f"unsupported step type: {step_type}")
        cache_step = step_cls(subscription_step)
        setattr(subscription_step, "step_manager", cache_step)
        return cache_step
