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
import copy
import logging

import six
from jinja2 import Template

"""
jinja2渲染相关的公共函数
"""
logger = logging.getLogger("app")

TEMPLATE_CACHE = {}


def find_element(element, dict_data):
    """
    根据路径字符串获取字典定义的嵌套key的值
    :param element: 路径字符串，格式 a.b.c.d
    :param dict_data: 字典数据
    :return: value
    """
    keys = element.split(".")
    rv = dict_data
    for key in keys:
        rv = rv[key]
    return rv


def nested_render_data(data, context):
    """
    递归渲染字典中的模板字符串
    """
    if isinstance(data, six.string_types):
        if "{{" not in data:
            # 无 jinja 占位符，直接跳过
            return data
        try:
            # 尝试渲染用户参数，一旦失败，立即返回原数据
            template = TEMPLATE_CACHE.get(data)
            if not template:
                template = Template(data)
                TEMPLATE_CACHE[data] = template
            return template.render(context)
        except Exception as err:
            logger.exception(err)
            return data
    elif isinstance(data, dict):
        if "$for" in data and "$item" in data and "$body" in data:
            # 循环动态变量解析
            data_list = []
            # 提取列表变量
            for_list = find_element(data["$for"], context)

            for item in for_list:
                # 临时设置上下文
                context[data["$item"]] = item
                # 深拷贝一次，防止原始模板被修改
                body_data = copy.deepcopy(data["$body"])
                data_list.append(nested_render_data(body_data, context))
                # 恢复上下文
                context.pop(data["$item"])
            return data_list

        for key, value in data.items():
            data[key] = nested_render_data(value, context)
    elif isinstance(data, list):
        for index, value in enumerate(data):
            data[index] = nested_render_data(value, context)
    return data
