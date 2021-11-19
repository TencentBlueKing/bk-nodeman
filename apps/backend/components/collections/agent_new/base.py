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

import abc
from functools import wraps
from typing import Any, Dict, List, Set, Union

from apps.node_man import models
from common.api import JobApi

from ..base import BaseService, CommonData
from ..job import JobV3BaseService


class AgentBaseService(BaseService, metaclass=abc.ABCMeta):
    """
    AGENT安装基类
    """

    def sub_inst_failed_handler(self, sub_inst_ids: Union[List[int], Set[int]]):
        """
        订阅实例失败处理器
        :param sub_inst_ids: 订阅实例ID列表/集合
        """
        pass


class AgentCommonData(CommonData):
    def __init__(self, sub_inst_id__host_id_map: Dict[int, int], **kwargs):
        self.sub_inst_id__host_id_map = sub_inst_id__host_id_map
        super().__init__(**kwargs)


def batch_call_single_exception_handler(single_func):
    # 批量执行时单个机器的异常处理
    @wraps(single_func)
    def wrapper(self, sub_inst_id, *args, **kwargs):
        try:
            return single_func(self, sub_inst_id, *args, **kwargs)
        except Exception as error:
            self.move_insts_to_failed([sub_inst_id], error)

    return wrapper


class AgentExecuteScriptService(JobV3BaseService, AgentBaseService, metaclass=abc.ABCMeta):

    PRINT_PARAMS_TO_LOG = True

    @property
    def script_name(self):
        """
        插件需要执行的脚本文件名称，由子类继承定义
        """
        raise NotImplementedError()

    def _execute(self, data, parent_data, common_data: AgentCommonData):

        timeout = data.get_one_of_inputs("timeout")
        # 批量请求作业平台的参数
        multi_job_params_map: Dict[str, Dict[str, Any]] = {}
        for sub_inst in common_data.subscription_instances:
            bk_host_id = sub_inst.instance_info["host"]["bk_host_id"]
            host_obj = common_data.host_id_obj_map[bk_host_id]
            script_param = self.get_script_param(data=data, common_data=common_data, host=host_obj)
            script_content = self.get_script_content(data=data, common_data=common_data, host=host_obj)

            # script_content 和 script_param md5一样的则认为是同样的脚本操作，合并到一个作业中，提高执行效率
            script_content_md5 = self.get_md5(script_content)
            script_param_md5 = self.get_md5(script_param)
            md5_key = f"{script_content_md5}-{script_param_md5}"

            if md5_key in multi_job_params_map:
                multi_job_params_map[md5_key]["subscription_instance_id"].append(sub_inst.id)
                multi_job_params_map[md5_key]["job_params"]["target_server"]["ip_list"].append(
                    {"bk_cloud_id": host_obj.bk_cloud_id, "ip": host_obj.inner_ip}
                )
            else:
                multi_job_params_map[md5_key] = {
                    "job_func": JobApi.fast_execute_script,
                    "subscription_instance_id": [sub_inst.id],
                    "subscription_id": common_data.subscription.id,
                    "job_params": {
                        "target_server": {"ip_list": [{"bk_cloud_id": host_obj.bk_cloud_id, "ip": host_obj.inner_ip}]},
                        "script_content": script_content,
                        "script_param": script_param,
                        "timeout": timeout,
                        "os_type": host_obj.os_type,
                    },
                }

        self.run_job_or_finish_schedule(multi_job_params_map)

    def get_script_content(self, data, common_data: AgentCommonData, host: models.Host) -> str:
        """
        获取脚本内容
        :param data:
        :param common_data:
        :param host: 主机对象
        :return: 脚本内容
        """
        raise NotImplementedError()

    def get_script_param(self, data, common_data: AgentCommonData, host: models.Host) -> str:
        """
        获取脚本参数
        :param data:
        :param common_data:
        :param host: 主机类型
        :return: 脚本参数
        """
        return ""
