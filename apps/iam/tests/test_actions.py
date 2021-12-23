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
from apps.iam import ActionEnum
from apps.iam.exceptions import ActionNotExistError
from apps.iam.handlers.actions import (
    ActionMeta,
    fetch_related_actions,
    generate_all_actions_json,
    get_action_by_id,
)
from apps.utils.unittest import testcase


class TestAction(testcase.CustomBaseTestCase):
    def test_to_json(self):
        self.assertIsInstance(ActionEnum.VIEW_BUSINESS.to_json(), dict)

    def test_get_action_by_id(self):
        action = get_action_by_id(ActionEnum.VIEW_BUSINESS)
        self.assertIsInstance(action, ActionMeta)

        self.assertRaises(ActionNotExistError, get_action_by_id, "not_exist_action")
        action = get_action_by_id(ActionEnum.VIEW_BUSINESS.id)
        self.assertEqual(action, ActionEnum.VIEW_BUSINESS)

    def test_fetch_related_actions(self):
        related_actions = fetch_related_actions([ActionEnum.AGENT_VIEW])
        self.assertEqual(related_actions, {ActionEnum.VIEW_BUSINESS.id: ActionEnum.VIEW_BUSINESS})

    def test_generate_all_actions_json(self):
        action_json = generate_all_actions_json()
        self.assertIsInstance(action_json, list)
