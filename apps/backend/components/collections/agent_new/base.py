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

from apps.backend.api.job import process_parms
from apps.node_man import constants, models
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

    @classmethod
    def get_common_data(cls, data):
        """
        初始化常用数据，注意这些数据不能放在 self 属性里，否则会产生较大的 process snap shot，
        另外也尽量不要在 schedule 中使用，否则多次回调可能引起性能问题
        """

        common_data = super().get_common_data(data)

        # 默认接入点
        default_ap = models.AccessPoint.get_default_ap()
        # 主机ID - 接入点 映射关系
        # 引入背景：在聚合流程中，类似 host.agent_config, host.ap 的逻辑会引发 n + 1 DB查询问题
        host_id__ap_map: Dict[int, models.AccessPoint] = {}

        for bk_host_id in common_data.bk_host_ids:
            host = common_data.host_id_obj_map[bk_host_id]
            # 有两种情况需要使用默认接入点
            # 1. 接入点已被删除
            # 2. 主机未选择接入点 ap_id = -1
            host_id__ap_map[bk_host_id] = common_data.ap_id_obj_map.get(host.ap_id, default_ap)

        return AgentCommonData(
            bk_host_ids=common_data.bk_host_ids,
            host_id_obj_map=common_data.host_id_obj_map,
            ap_id_obj_map=common_data.ap_id_obj_map,
            subscription=common_data.subscription,
            subscription_instances=common_data.subscription_instances,
            subscription_instance_ids=common_data.subscription_instance_ids,
            sub_inst_id__host_id_map=common_data.sub_inst_id__host_id_map,
            # Agent 新增的公共数据
            default_ap=default_ap,
            host_id__ap_map=host_id__ap_map,
        )

    @classmethod
    def get_general_node_type(cls, node_type: str) -> str:
        """
        获取广义上的节点类型，既仅为 proxy 或 agent
        :param node_type: 取值参考 models.HOST.node_type
        :return:
        """
        return (constants.NodeType.AGENT.lower(), constants.NodeType.PROXY.lower())[
            node_type == constants.NodeType.PROXY
        ]

    @classmethod
    def get_agent_upgrade_pkg_name(cls, host: models.Host) -> str:
        """
        获取 Agent 升级包名称
        :param host:
        :return:
        """
        package_type = ("client", "proxy")[host.node_type == constants.NodeType.PROXY]
        agent_upgrade_package_name = f"gse_{package_type}-{host.os_type.lower()}-{host.cpu_arch}_upgrade.tgz"
        return agent_upgrade_package_name


class AgentCommonData(CommonData):
    def __init__(
        self,
        bk_host_ids: Set[int],
        host_id_obj_map: Dict[int, models.Host],
        ap_id_obj_map: Dict[int, models.AccessPoint],
        subscription: models.Subscription,
        subscription_instances: List[models.SubscriptionInstanceRecord],
        subscription_instance_ids: Set[int],
        sub_inst_id__host_id_map: Dict[int, int],
        # Agent 新增的公共数据
        default_ap: models.AccessPoint,
        host_id__ap_map: Dict[int, models.AccessPoint],
    ):

        # 默认接入点
        self.default_ap = default_ap
        # 主机ID - 接入点 映射关系
        self.host_id__ap_map = host_id__ap_map

        super().__init__(
            bk_host_ids=bk_host_ids,
            host_id_obj_map=host_id_obj_map,
            ap_id_obj_map=ap_id_obj_map,
            subscription=subscription,
            subscription_instances=subscription_instances,
            subscription_instance_ids=subscription_instance_ids,
            sub_inst_id__host_id_map=sub_inst_id__host_id_map,
        )


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


class AgentTransferPackageService(JobV3BaseService, AgentBaseService, metaclass=abc.ABCMeta):
    def _execute(self, data, parent_data, common_data: AgentCommonData):
        timeout = data.get_one_of_inputs("timeout")
        # 批量请求作业平台的参数
        multi_job_params_map: Dict[str, Dict[str, Any]] = {}
        for sub_inst in common_data.subscription_instances:
            bk_host_id = sub_inst.instance_info["host"]["bk_host_id"]
            host_obj = common_data.host_id_obj_map[bk_host_id]

            file_list = self.get_file_list(data=data, common_data=common_data, host=host_obj)
            file_target_path = self.get_file_target_path(data=data, common_data=common_data, host=host_obj)
            # 如果分发的文件列表 & 目标路径一致，合并到一个作业中，提高执行效率
            md5_key = f"{self.get_md5('|'.join(sorted(file_list)))}-{file_target_path}"

            if md5_key in multi_job_params_map:
                multi_job_params_map[md5_key]["subscription_instance_id"].append(sub_inst.id)
                multi_job_params_map[md5_key]["job_params"]["target_server"]["ip_list"].append(
                    {"bk_cloud_id": host_obj.bk_cloud_id, "ip": host_obj.inner_ip}
                )
            else:
                multi_job_params_map[md5_key] = {
                    "job_func": JobApi.fast_transfer_file,
                    "subscription_instance_id": [sub_inst.id],
                    "subscription_id": common_data.subscription.id,
                    "job_params": {
                        "target_server": {"ip_list": [{"bk_cloud_id": host_obj.bk_cloud_id, "ip": host_obj.inner_ip}]},
                        "file_target_path": file_target_path,
                        "file_source_list": [{"file_list": file_list}],
                        "timeout": timeout,
                        "os_type": host_obj.os_type,
                    },
                }

        self.run_job_or_finish_schedule(multi_job_params_map)

    def get_file_list(self, data, common_data: AgentCommonData, host: models.Host) -> List[str]:
        """
        获取主机所需的文件路径列表
        :param data:
        :param common_data:
        :param host: 主机对象
        :return: 文件路径列表
        """
        raise NotImplementedError()

    def get_file_target_path(self, data, common_data: AgentCommonData, host: models.Host) -> str:
        """
        获取主机所需的文件路径列表
        :param data:
        :param common_data:
        :param host: 主机对象
        :return: 文件路径列表
        """
        raise NotImplementedError()


class AgentPushConfigService(JobV3BaseService, AgentBaseService, metaclass=abc.ABCMeta):
    def cal_job_unique_key(self, config_info_list: List[Dict[str, Any]], file_target_path: str):
        """
        计算分发任务的唯一标识
        如果配置文件名称、MD5、目标路径一致，认为分发内容一致，整合到一个作业中
        :param config_info_list:
        :param file_target_path:
        :return:
        """
        config_unique_keys = []
        for config_info in config_info_list:
            config_unique_keys.append(f"{config_info['file_name']}-{self.get_md5(config_info['content'])}")
        return f"{'-'.join(sorted(config_unique_keys))}-{file_target_path}"

    def _execute(self, data, parent_data, common_data: AgentCommonData):
        timeout = data.get_one_of_inputs("timeout")
        # 批量请求作业平台的参数
        multi_job_params_map: Dict[str, Dict[str, Any]] = {}
        for sub_inst in common_data.subscription_instances:
            bk_host_id = sub_inst.instance_info["host"]["bk_host_id"]
            host_obj = common_data.host_id_obj_map[bk_host_id]

            config_info_list = self.get_config_info_list(data=data, common_data=common_data, host=host_obj)
            file_target_path = self.get_file_target_path(data=data, common_data=common_data, host=host_obj)

            job_unique_key = self.cal_job_unique_key(config_info_list, file_target_path)
            if job_unique_key in multi_job_params_map:
                multi_job_params_map[job_unique_key]["subscription_instance_id"].append(sub_inst.id)
                multi_job_params_map[job_unique_key]["job_params"]["target_server"]["ip_list"].append(
                    {"bk_cloud_id": host_obj.bk_cloud_id, "ip": host_obj.inner_ip}
                )
            else:
                file_source_list = []
                for config_info in config_info_list:
                    file_source_list.append(
                        {"file_name": config_info["file_name"], "content": process_parms(config_info["content"])}
                    )
                multi_job_params_map[job_unique_key] = {
                    "job_func": JobApi.push_config_file,
                    "subscription_instance_id": [sub_inst.id],
                    "subscription_id": common_data.subscription.id,
                    "job_params": {
                        "target_server": {"ip_list": [{"bk_cloud_id": host_obj.bk_cloud_id, "ip": host_obj.inner_ip}]},
                        "file_target_path": file_target_path,
                        "file_list": file_source_list,
                        "timeout": timeout,
                        "os_type": host_obj.os_type,
                    },
                }

        self.run_job_or_finish_schedule(multi_job_params_map)

    def get_config_info_list(self, data, common_data: AgentCommonData, host: models.Host) -> List[Dict[str, Any]]:
        """
        获取主机所需的配置文件信息列表
        :param data:
        :param common_data:
        :param host: 主机对象
        :return: 文件路径列表
        """
        raise NotImplementedError()

    def get_file_target_path(self, data, common_data: AgentCommonData, host: models.Host) -> str:
        """
        获取主机所需的文件路径列表
        :param data:
        :param common_data:
        :param host: 主机对象
        :return: 文件路径列表
        """
        raise NotImplementedError()
