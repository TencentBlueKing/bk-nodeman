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
import ipaddress
import json
from collections import Counter, namedtuple
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional, Set, Union


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


def filter_values(data: Dict, filter_empty=False) -> Dict:
    """
    用于过滤空值
    :param filter_empty: 是否同时过滤布尔值为False的值
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


def suffix_slash(os, path) -> str:
    if os.lower() in ["windows", "WINDOWS"]:
        if not path.endswith("\\"):
            path = path + "\\"
    else:
        if not path.endswith("/"):
            path = path + "/"
    return path


def chunk_lists(lst: List[Any], n) -> List[Any]:
    """Yield successive n-sized chunks from lst."""
    for idx in range(0, len(lst), n):
        yield lst[idx : idx + n]


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


def obj_to_dict(obj) -> Dict[str, Any]:
    """
    对象转字典
    :param obj:
    :return:
    """
    return json.loads(json.dumps(obj, default=lambda o: getattr(o, "__dict__", str(o))))


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


def remove_keys_from_dict(
    origin_data: Union[Dict, List], keys: Iterable[Any], return_deep_copy: bool = True, recursive: bool = False
) -> Dict[str, Any]:
    """)
    从字典或列表结构中，移除结构中存在的字典所指定的key
    :param origin_data: 原始数据
    :param keys: 待移除的键
    :param return_deep_copy: 是否返回深拷贝的数据
    :param recursive: 是否递归移除
    :return:
    """

    def _remove_dict_keys_recursively(_data: Union[List, Dict]) -> Union[List, Dict]:

        if isinstance(_data, dict):
            for _key in keys:
                _data.pop(_key, None)

        if not recursive:
            return _data

        _is_dict = isinstance(_data, dict)

        for _key_or_item in _data:
            _item = _data[_key_or_item] if _is_dict else _key_or_item
            if not (isinstance(_item, dict) or isinstance(_item, list)):
                continue
            _remove_dict_keys_recursively(_item)

        return _data

    data = deepcopy(origin_data) if return_deep_copy else origin_data
    return _remove_dict_keys_recursively(data)


def get_chr_seq(begin_chr: str, end_chr: str) -> List[str]:
    """

    :param begin_chr:
    :param end_chr:
    :return:
    """
    return [chr(ascii_int) for ascii_int in range(ord(begin_chr), ord(end_chr) + 1)]


def ipv6_formatter(data: Dict[str, Any], ipv6_field_names: List[str]):
    """
    将 data 中 ipv6_field_names 转为 IPv6 标准格式
    :param data: 可能包含 v6 的字典数据
    :param ipv6_field_names:IPv6 字段
    :return:
    """
    for ipv6_field_name in ipv6_field_names:
        ipv6_val: Optional[str] = data.get(ipv6_field_name)
        if not ipv6_val:
            continue
        ip_address = ipaddress.ip_address(ipv6_val)
        # 将 v6 转为标准格式
        if ip_address.version == 6:
            data[ipv6_field_name] = ip_address.exploded


def ipv4_to_v6(ipv4: str) -> str:
    """
    IPv4 转为 IPv6
    :param ipv4: IPv4
    :return: IPv6 标准形式
    """
    ipv4_address: ipaddress.IPv4Address = ipaddress.IPv4Address(ipv4)
    prefix6to4: int = int(ipaddress.IPv6Address("2002::"))
    ipv6_address: ipaddress.IPv6Address = ipaddress.IPv6Address(prefix6to4 | (int(ipv4_address) << 80))
    return ipv6_address.exploded
