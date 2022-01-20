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
from enum import Enum
from typing import Any, Callable, Dict, Optional, Union

import mock

from apps.utils.enum import EnhanceEnum
from apps.utils.unittest.base import CallRecorder

DEFAULT_BK_BIZ_ID = 2

DEFAULT_BK_BIZ_NAME = "测试业务"

DEFAULT_USERNAME = "admin"

DEFAULT_IP = "127.0.0.1"

JOB_TASK_PIPELINE_ID = "1ae89ce9deec319bbd8727a0c4b2ca82"


class MockReturnType(EnhanceEnum):

    RETURN_VALUE = "return_value"
    SIDE_EFFECT = "side_effect"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.RETURN_VALUE: "直接返回指定data", cls.SIDE_EFFECT: "返回可调用函数"}


class MockReturn:
    return_type: str = None
    return_obj: Optional[Union[Callable, Any]] = None

    def __init__(self, return_type: str, return_obj: Union[Callable, Any]):
        if return_type not in MockReturnType.list_member_values():
            raise ValueError(f"except return type -> {MockReturnType.list_member_values()}, but get {return_type}")
        self.return_type = return_type

        if self.return_type == MockReturnType.SIDE_EFFECT.value:
            if not callable(return_obj):
                raise ValueError(f"return_obj must be callable because return type is {self.return_type}")
        self.return_obj = return_obj


class BaseMockClient:
    call_recorder: CallRecorder = None

    def __init__(self):
        self.call_recorder = CallRecorder()

    @classmethod
    def generate_magic_mock(cls, mock_return_obj: Optional[MockReturn]):
        mock_return_obj = mock_return_obj or MockReturn(return_type=MockReturnType.RETURN_VALUE.value, return_obj=None)
        return mock.MagicMock(**{mock_return_obj.return_type: mock_return_obj.return_obj})
