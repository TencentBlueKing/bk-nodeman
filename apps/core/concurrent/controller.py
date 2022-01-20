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
from collections import ChainMap
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

import wrapt
from django.utils.translation import ugettext as _
from rest_framework import exceptions

from apps.exceptions import ValidationError
from apps.utils import basic, concurrent

from . import serializers


class ConcurrentControlConfig:
    """并发控制配置"""

    execute_all: bool = None
    limit: int = None
    is_concurrent_between_batches: bool = None
    interval: float = None

    def __init__(self, config_dict: Dict[str, Any]):
        try:
            data_serializer = serializers.ConcurrentControlConfigSerializer(data=config_dict)
            data_serializer.is_valid(raise_exception=True)
        except exceptions.ValidationError as err:
            raise ValidationError(_("解析并发控制配置失败，报错原因 -> {err}").format(err=err))
        validated_data = data_serializer.validated_data

        self.execute_all = validated_data["execute_all"]
        self.limit = validated_data["limit"]
        self.is_concurrent_between_batches = validated_data["is_concurrent_between_batches"]
        self.interval = validated_data["interval"]


class ConcurrentController:
    """
    并发控制器
    功能：细粒度控制不同执行逻辑的单次并发量，将批量任务先按设置的单次并发限制数量进行分批，批次间选择并行或串行
    背景：
        - 并发 ssh 连接问题
            使用 paramiko 远程连接时发现，当任务量 > CONCURRENT_NUMBER 时，部分线程出现 self.chan.recv(RECV_BUFLEN) 超时的问题
            经测试，如果需要下发多条命令，一次并发量 <= CONCURRENT_NUMBER 是安全的
        - JOB 执行脚本接口调用限频
        ...
    """

    # 并发配置类
    SETTING_CLASS: Type[ConcurrentControlConfig] = ConcurrentControlConfig

    # 待执行对象列表名称
    data_list_name: str = None
    # 批量执行方法
    batch_call_func: Callable[..., List] = None
    # 获取配置方法
    get_config_dict_func: Optional[Callable[..., Dict[str, Any]]] = None
    # 获取配置方法 位置参数
    get_config_dict_args: Tuple[Any] = None
    # 获取配置方法 关键字参数
    get_config_dict_kwargs: Dict[str, Any] = None

    # 对 batch_call_func 结果进行预处理
    get_data: Callable = None
    # 是否展开结果
    extend_result: bool = None
    # 其他调用参数，覆盖 config、及显式传入参数
    batch_call_kwargs: Dict[str, Any] = None

    def __init__(
        self,
        data_list_name: str,
        batch_call_func: Callable[..., List],
        get_config_dict_func: Optional[Callable[..., Dict[str, Any]]] = None,
        get_config_dict_args: Optional[Tuple[Any]] = None,
        get_config_dict_kwargs: Optional[Dict[str, Any]] = None,
        get_data: Callable = lambda x: x,
        extend_result: bool = True,
        batch_call_kwargs: Dict[str, Any] = None,
    ):
        """
        :param data_list_name: 待执行对象列表名称
        :param batch_call_func: 批量执行方法，定义方式参考 batch_call
        :param get_config_dict_func: 获取配置方法
        :param get_config_dict_args: 获取配置方法 位置参数
        :param get_config_dict_kwargs: 获取配置方法 关键字参数
        :param get_data: 对 batch_call_func 结果进行预处理
        :param extend_result: 是否展开结果
        :param batch_call_kwargs: 其他调用参数
        """

        self.data_list_name = data_list_name
        self.batch_call_func = batch_call_func

        self.get_config_dict_func = get_config_dict_func
        self.get_config_dict_args = get_config_dict_args or ()
        self.get_config_dict_kwargs = get_config_dict_kwargs or {}

        self.get_data = get_data
        self.extend_result = extend_result
        self.batch_call_kwargs = batch_call_kwargs or {}

    def get_config_obj(self) -> ConcurrentControlConfig:
        """并发配置实例"""
        config_dict = {}
        if self.get_config_dict_func is not None:
            # 获取并发配置
            config_dict = self.get_config_dict_func(*self.get_config_dict_args, **self.get_config_dict_kwargs)
        return self.SETTING_CLASS(config_dict=config_dict)

    # 使用 wrapt 模块减少嵌套层级，参考：https://github.com/piglei/one-python-craftsman/blob/master/zh_CN/8-tips-on-decorators.md
    # 文档：https://wrapt.readthedocs.io/en/latest/decorators.html
    @wrapt.decorator
    def __call__(self, wrapped: Callable, instance: Optional[object], args: Tuple[Any], kwargs: Dict[str, Any]):
        """
        :param wrapped: 被装饰的函数或类方法
        :param instance:
            - 如果被装饰者为普通类方法，该值为类实例
            - 如果被装饰者为 classmethod / 类方法，该值为类
            - 如果被装饰者为类/函数/静态方法，该值为 None
        :param args: 位置参数
        :param kwargs: 关键字参数
        :return:
        """
        config_obj = self.get_config_obj()
        # 全量执行
        if config_obj.execute_all:
            return wrapped(*args, **kwargs)

        params_list: List[Dict[str, Any]] = []
        for chunk_list in basic.chunk_lists(kwargs[self.data_list_name], config_obj.limit):
            params_list.append(dict(ChainMap({self.data_list_name: chunk_list}, kwargs)))

        # 如果批次间非并发，batch_call_func 默认使用 batch_call_serial
        if not config_obj.is_concurrent_between_batches:
            self.batch_call_func = concurrent.batch_call_serial
        return self.batch_call_func(
            func=wrapped,
            params_list=params_list,
            **dict(
                ChainMap(
                    self.batch_call_kwargs,
                    {
                        "get_data": self.get_data,
                        "extend_result": self.extend_result,
                        "interval": config_obj.interval,
                    },
                )
            )
        )
