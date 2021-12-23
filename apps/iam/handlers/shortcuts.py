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

from apps.iam import Permission
from apps.iam.handlers.actions import ActionMeta


def assert_allowed(action: Union[ActionMeta], resources: List[Resource] = None):
    """
    权限校验
    """
    Permission().is_allowed(action, resources, raise_exception=True)
