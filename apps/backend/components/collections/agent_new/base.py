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
from typing import Dict, List, Set, Union

from apps.node_man import constants, models

from .. import job
from ..base import BaseService, CommonData


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


# 根据 JOB 的插件额外封装一层，保证后续基于 Agent 增加定制化功能的可扩展性


class AgentExecuteScriptService(job.JobExecuteScriptService, AgentBaseService):
    pass


class AgentTransferFileService(job.JobTransferFileService, AgentBaseService):
    pass


class AgentPushConfigService(job.JobPushConfigService, AgentBaseService):
    pass
