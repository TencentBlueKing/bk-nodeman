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

from functools import wraps
from typing import Callable, Optional


def class_member_cache(name: Optional[str] = None):
    """
    类成员缓存
    :param name: 缓存名称，为空则使用 class_func.__name__
    :return:
    """

    def class_member_cache_inner(class_func: Callable) -> Callable:
        @wraps(class_func)
        def wrapper(self, *args, **kwargs):

            cache_field = f"_{name or class_func.__name__}"

            cache_member = getattr(self, cache_field, None)
            if cache_member:
                return cache_member
            cache_member = class_func(self, *args, **kwargs)
            setattr(self, cache_field, cache_member)
            return cache_member

        return wrapper

    return class_member_cache_inner
