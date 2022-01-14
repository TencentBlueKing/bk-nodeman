# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making 蓝鲸 (Blueking) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""
import json
from typing import Dict, List, Union

from django.utils.translation import ugettext as _
from iam import Action

from apps.iam.exceptions import ActionNotExistError
from apps.iam.handlers.resources import ResourceEnum


class ActionMeta(Action):
    """
    动作定义
    """

    def __init__(
        self,
        id: str,
        name: str,
        name_en: str,
        type: str,
        version: int,
        related_resource_types: list = None,
        related_actions: list = None,
        description: str = "",
        description_en: str = "",
    ):
        super(ActionMeta, self).__init__(id)
        self.name = name
        self.name_en = name_en
        self.type = type
        self.version = version
        self.related_resource_types = related_resource_types or []
        self.related_actions = related_actions or []
        self.description = description
        self.description_en = description_en

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "name_en": self.name_en,
            "type": self.type,
            "version": self.version,
            "related_resource_types": [resource.to_json() for resource in self.related_resource_types],
            "related_actions": self.related_actions,
            "description": self.description,
            "description_en": self.description_en,
        }


class ActionEnum:
    VIEW_BUSINESS = ActionMeta(
        id="view_business",
        name="业务访问",
        name_en="View Business",
        type="view",
        related_resource_types=[ResourceEnum.BUSINESS],
        related_actions=[],
        version=1,
    )

    TASK_HISTORY_VIEW = ActionMeta(
        id="task_history_view",
        name="任务历史查看",
        name_en="Task History View",
        type="view",
        related_resource_types=[ResourceEnum.BUSINESS],
        related_actions=[],
        version=1,
    )

    AGENT_VIEW = ActionMeta(
        id="agent_view",
        name="Agent查询",
        name_en="Agent View",
        type="view",
        related_resource_types=[ResourceEnum.BUSINESS],
        related_actions=[VIEW_BUSINESS.id],
        version=1,
    )

    AGENT_OPERATE = ActionMeta(
        id="agent_operate",
        name="Agent操作",
        name_en="Agent Operate",
        type="manage",
        related_resource_types=[ResourceEnum.BUSINESS],
        related_actions=[AGENT_VIEW.id],
        version=1,
    )

    PROXY_OPERATE = ActionMeta(
        id="proxy_operate",
        name="Proxy操作",
        name_en="Proxy Operate",
        type="manage",
        related_resource_types=[ResourceEnum.BUSINESS],
        related_actions=[AGENT_VIEW.id],
        version=1,
    )

    CLOUD_VIEW = ActionMeta(
        id="cloud_view",
        name="云区域查看",
        name_en="Cloud View",
        type="view",
        related_resource_types=[ResourceEnum.CLOUD],
        related_actions=[],
        version=1,
    )

    STRATEGY_CREATE = ActionMeta(
        id="strategy_create",
        name="策略创建",
        name_en="Strategy Create",
        type="manage",
        related_resource_types=[ResourceEnum.BUSINESS],
        related_actions=[],
        version=1,
    )

    STRATEGY_VIEW = ActionMeta(
        id="strategy_view",
        name="策略查看",
        name_en="Strategy View",
        type="view",
        related_resource_types=[ResourceEnum.BUSINESS],
        related_actions=[],
        version=1,
    )


_all_actions = {action.id: action for action in ActionEnum.__dict__.values() if isinstance(action, ActionMeta)}


def get_action_by_id(action_id: Union[str, ActionMeta]) -> ActionMeta:
    """
    根据动作ID获取动作实例
    """
    if isinstance(action_id, ActionMeta):
        # 如果已经是实例，则直接返回
        return action_id

    if action_id not in _all_actions:
        raise ActionNotExistError(_("动作ID不存在：{action_id}").format(action_id=action_id))

    return _all_actions[action_id]


def fetch_related_actions(actions: List[Union[ActionMeta, str]]) -> Dict[str, ActionMeta]:
    """
    递归获取 action 动作依赖列表
    """
    actions = [get_action_by_id(action) for action in actions]

    def fetch_related_actions_recursive(_action: ActionMeta):
        _related_actions = {}
        for related_action_id in _action.related_actions:
            try:
                related_action = get_action_by_id(related_action_id)
            except ActionNotExistError:
                continue
            _related_actions[related_action_id] = related_action
            _related_actions.update(fetch_related_actions_recursive(related_action))
        return _related_actions

    related_actions = {}
    for action in actions:
        related_actions.update(fetch_related_actions_recursive(action))

    # 剔除根节点本身
    for action in actions:
        related_actions.pop(action.id, None)

    return related_actions


def generate_all_actions_json() -> List:
    """
    生成migrations的json配置
    """
    results = []
    for value in _all_actions.values():
        results.append({"operation": "upsert_action", "data": value.to_json()})
    print(json.dumps(results, ensure_ascii=False, indent=4))
    return results
