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
import traceback
from enum import Enum
from typing import Any, Callable, Dict, Tuple

from django.utils.translation import ugettext_lazy as _

from apps.core.concurrent import core_concurrent_constants
from apps.node_man import models
from apps.utils import enum

from . import base


class ServiceCCConfigName(enum.EnhanceEnum):

    SSH = "SERVICE_SSH"
    WMIEXE = "SERVICE_WMIEXE"
    JOB_CMD = "SERVICE_JOB_CMD"
    QUERY_PASSWORD = "SERVICE_QUERY_PASSWORD"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {
            cls.SSH: _("使用 ssh 会话执行命令"),
            cls.WMIEXE: _("使用 wmiexe 会话执行命令"),
            cls.JOB_CMD: _("使用 job 执行命令"),
            cls.QUERY_PASSWORD: _("查询密码"),
        }


def get_config_dict(config_name: str) -> Dict[str, Any]:
    default_concurrent_control_config = copy.deepcopy(core_concurrent_constants.DEFAULT_CONCURRENT_CONTROL_CONFIG)
    if config_name == ServiceCCConfigName.SSH.value:
        # 目前 asyncssh 协程执行的最佳批次内数量
        default_concurrent_control_config.update(limit=100)
    elif config_name == ServiceCCConfigName.WMIEXE.value:
        # Windows 管控数量相对较少，且单个执行约为 30 秒，需要减少批次内串行的数量
        default_concurrent_control_config.update(limit=4)
    elif config_name == ServiceCCConfigName.JOB_CMD.value:
        # 通过作业平台执行时，批次间串行防止触发接口限频
        default_concurrent_control_config.update(is_concurrent_between_batches=False, interval=2)

    current_controller_settings = models.GlobalSettings.get_config(
        key=models.GlobalSettings.KeyEnum.CONCURRENT_CONTROLLER_SETTINGS.value, default={}
    )
    return current_controller_settings.get(config_name, default_concurrent_control_config)


def default_sub_inst_id_extractor(args: Tuple[Any], kwargs: Dict[str, Any]):
    """
    默认订阅实例ID提取器
    :param args: 位置参数
    :param kwargs: 关键字参数
    :return: 订阅实例ID
    """
    if args:
        return args[0]
    else:
        return kwargs["sub_inst_id"]


def default_sub_inst_task_exc_handler(
    wrapped: Callable, instance: base.BaseService, args: Tuple[Any], kwargs: Dict[str, Any], exc: Exception
) -> Any:
    """
    默认的单订阅实例任务异常处理，用于批量调用时规避单任务异常导致整体执行失败的情况
    :param wrapped: 被装饰的函数或类方法
    :param instance: 基础Pipeline服务
    :param exc: 捕获到异常
    :param args: 位置参数
    :param kwargs: 关键字参数
    :return:
    """
    sub_inst_id = default_sub_inst_id_extractor(args, kwargs)
    instance.move_insts_to_failed([sub_inst_id], str(exc))
    # 打印 DEBUG 日志
    instance.log_debug(sub_inst_id, log_content=traceback.format_exc(), fold=True)
    return None
