# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making 蓝鲸 (Blueking) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""
from typing import List, Union

from iam import Resource

from apps.gsekit.cmdb import mock_data as cmdb_mock_data
from apps.iam import Permission
from apps.iam.handlers.actions import ActionMeta


class PermissionMock(Permission):
    def filter_business_list_by_action(self, action: Union[ActionMeta, str], business_list: List = None):
        return cmdb_mock_data.BIZ_LIST_RESPONSE

    def batch_is_allowed(self, actions: List[ActionMeta], resources: List[List[Resource]]):
        admin_actions = {action.id: True for action in actions}
        result = {}
        for resource_list in resources:
            for resource in resource_list:
                result[resource.id] = admin_actions

        return result

    def grant_creator_action(self, resource: Resource, creator: str = None, raise_exception=False):
        return True, "success"
