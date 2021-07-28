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
import hashlib
from collections import Counter, namedtuple
from typing import Any, List, Set, Union


def tuple_choices(tupl):
    """从django-model的choices转换到namedtuple"""
    return [(t, t) for t in tupl]


def dict_to_choices(dic, is_reversed=False):
    """从django-model的choices转换到namedtuple"""
    if is_reversed:
        return [(v, k) for k, v in list(dic.items())]
    return [(k, v) for k, v in list(dic.items())]


def reverse_dict(dic):
    return {v: k for k, v in list(dic.items())}


def dict_to_namedtuple(dic):
    """从dict转换到namedtuple"""
    return namedtuple("AttrStore", list(dic.keys()))(**dic)


def choices_to_namedtuple(choices):
    """从django-model的choices转换到namedtuple"""
    return dict_to_namedtuple(dict(choices))


def tuple_to_namedtuple(tupl):
    """从tuple转换到namedtuple"""
    return dict_to_namedtuple(dict(tuple_choices(tupl)))


def filter_values(data: dict, filter_empty=False) -> dict:
    """
    用于过滤空值
    :param filter_empty: 是否同时过滤空值
    :param data: 存放各个映射关系的字典
    :return: 去掉None值的字典
    """

    ret = {}
    for obj in data:
        if filter_empty and not data[obj]:
            continue
        if data[obj] is not None:
            ret[obj] = data[obj]
    return ret


def suffix_slash(os, path):
    if os.lower() == "windows":
        if not path.endswith("\\"):
            path = path + "\\"
    else:
        if not path.endswith("/"):
            path = path + "/"
    return path


def md5(file_name):
    """内部实现的平台无关性计算MD5"""
    hash = hashlib.md5()
    try:
        with open(file_name, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                if not chunk:
                    break
                hash.update(chunk)
    except IOError:
        return "-1"

    return hash.hexdigest()


def chunk_lists(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def distinct_dict_list(dict_list: list):
    """
    返回去重后字典列表，仅支持value为不可变对象的字典
    :param dict_list: 字典列表
    :return: 去重后的字典列表
    """
    return [dict(tupl) for tupl in set([tuple(sorted(item.items())) for item in dict_list])]


def order_dict(dictionary: dict):
    """
    递归把字典按key进行排序
    :param dictionary:
    :return:
    """
    if not isinstance(dictionary, dict):
        return dictionary
    return {k: order_dict(v) if isinstance(v, dict) else v for k, v in sorted(dictionary.items())}


def list_equal(
    left: Union[List[Union[str, int]], Set[Union[str, int]]],
    right: Union[List[Union[str, int]], Set[Union[str, int]]],
    use_sort=True,
) -> bool:
    """
    判断列表是否相等，支持具有重复值列表的比较
    参考：https://stackoverflow.com/questions/9623114/check-if-two-unordered-lists-are-equal
    :param left:
    :param right:
    :param use_sort: 使用有序列表可比较的特性，数据规模不大的情况下性能优于Counter
    :return:
    """
    if isinstance(left, set) and isinstance(right, set):
        return left == right

    if use_sort:
        return sorted(list(left)) == sorted(list(right))

    return Counter(left) == Counter(right)


def list_slice(lst: List[Any], limit: int) -> List[List[Any]]:
    begin = 0
    slice_list = []
    while begin < len(lst):
        slice_list.append(lst[begin : begin + limit])
        begin += limit
    return slice_list


def to_int_or_default(val: Any, default: Any = None) -> Union[int, Any, None]:
    try:
        return int(val)
    except ValueError:
        return default
