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

import logging
import typing

from .. import constants, exceptions
from .base import BaseTargetHelper
from .plugin import PluginTargetHelper

logger = logging.getLogger("app")


TARGET_TYPE__HELPER_MAP: typing.Dict[typing.Any, typing.Type[BaseTargetHelper]] = {
    constants.TargetType.PLUGIN.value: PluginTargetHelper
}


def get_target_helper(target_type: str) -> typing.Type[BaseTargetHelper]:
    try:
        return TARGET_TYPE__HELPER_MAP[target_type]
    except KeyError:
        logger.error(f"target helper not exist: target_type -> {target_type}")
        raise exceptions.TargetHelperNotExistError({"target_type": target_type})
