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

from typing import Optional


def str2bool(string: Optional[str], strict: bool = True) -> bool:
    """
    字符串转布尔值
    对于bool(str) 仅在len(str) == 0 or str is None 的情况下为False，为了适配bool("False") 等环境变量取值情况，定义该函数
    参考：https://stackoverflow.com/questions/21732123/convert-true-false-value-read-from-file-to-boolean
    :param string:
    :param strict: 严格校验，非 False / True / false / true  时抛出异常，用于环境变量的转换
    :return:
    """
    if string in ["False", "false"]:
        return False
    if string in ["True", "true"]:
        return True

    if strict:
        raise ValueError(f"{string} can not convert to bool")
    return bool(string)
