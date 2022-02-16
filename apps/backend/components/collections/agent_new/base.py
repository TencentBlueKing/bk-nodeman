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
import abc
import time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union

import wrapt

from apps.node_man import constants, models
from pipeline.core.flow import Service

from .. import job
from ..base import BaseService, CommonData


class AgentBaseService(BaseService, metaclass=abc.ABCMeta):
    """
    AGENT安装基类
    """

    def inputs_format(self):
        return super().inputs_format() + [
            Service.InputItem(name="blueking_language", key="blueking_language", type="str", required=True),
        ]

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

    @property
    def agent_proc_common_data(self) -> Dict[str, Any]:
        """
        获取 agent ProcessStatus 通用构造数据
        :return:
        """
        return {
            "name": models.ProcessStatus.GSE_AGENT_PROCESS_NAME,
            "source_type": models.ProcessStatus.SourceType.DEFAULT,
        }

    def maintain_agent_proc_status_uniqueness(self, bk_host_ids: Set[int]) -> None:
        """
        维持 Agent 进程的唯一性
        :param bk_host_ids: 主机ID列表
        :return:
        """
        proc_status_infos = models.ProcessStatus.objects.filter(
            **self.agent_proc_common_data, bk_host_id__in=bk_host_ids
        ).values("id", "bk_host_id", "status")

        proc_status_infos_gby_host_id: Dict[int, List[Dict[str, Union[str, int]]]] = defaultdict(list)
        for proc_status_info in proc_status_infos:
            proc_status_infos_gby_host_id[proc_status_info["bk_host_id"]].append(proc_status_info)

        # 对进程按 status 排序，保证 RUNNING 值最小位于列表第一位
        proc_status_infos_gby_host_id = {
            host_id: sorted(proc_status_infos, key=lambda x: (1, -1)[x["status"] == constants.ProcStateType.RUNNING])
            for host_id, proc_status_infos in proc_status_infos_gby_host_id.items()
        }

        # 记录多余的进程ID
        proc_status_ids_to_be_deleted: List[int] = []
        for __, proc_status_infos in proc_status_infos_gby_host_id.items():
            # 按上述的排序规则，保证保留至少一个RUNNING的记录 或 第一个异常记录
            proc_status_ids_to_be_deleted.extend([proc_status_info["id"] for proc_status_info in proc_status_infos[1:]])

        # 删除多余的进程
        models.ProcessStatus.objects.filter(id__in=proc_status_ids_to_be_deleted).delete()

        # 如果没有进程记录则创建
        proc_statuses_to_be_created: List[models.ProcessStatus] = []
        host_ids_without_proc = bk_host_ids - set(proc_status_infos_gby_host_id.keys())
        for host_id in host_ids_without_proc:
            proc_statuses_to_be_created.append(models.ProcessStatus(bk_host_id=host_id, **self.agent_proc_common_data))
        models.ProcessStatus.objects.bulk_create(proc_statuses_to_be_created, batch_size=self.batch_size)


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


class RetryHandler:
    """重试处理器"""

    # 重试间隔
    interval: float = None
    # 重试次数
    retry_times: int = None
    # 需要重试的异常类型
    exception_types: List[Type[Exception]] = None

    def __init__(
        self, interval: float = 0, retry_times: int = 1, exception_types: Optional[List[Type[Exception]]] = None
    ):
        self.interval = max(interval, 0)
        self.retry_times = max(retry_times, 0)
        self.exception_types = exception_types or [Exception]

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
        call_times = self.retry_times + 1
        while call_times > 0:
            call_times = call_times - 1
            try:
                return wrapped(*args, **kwargs)
            except Exception as exc_val:
                # 重试次数已用完或者异常捕获未命中时，抛出原异常
                if call_times == 0 or not self.hit_exceptions(exc_val):
                    raise
                # 休眠一段时间
                time.sleep(self.interval)

    def hit_exceptions(self, exc_val: Exception) -> bool:
        for exception in self.exception_types:
            if isinstance(exc_val, exception):
                return True
        return False


# 根据 JOB 的插件额外封装一层，保证后续基于 Agent 增加定制化功能的可扩展性


class AgentExecuteScriptService(job.JobExecuteScriptService, AgentBaseService):
    pass


class AgentTransferFileService(job.JobTransferFileService, AgentBaseService):
    pass


class AgentPushConfigService(job.JobPushConfigService, AgentBaseService):
    pass
