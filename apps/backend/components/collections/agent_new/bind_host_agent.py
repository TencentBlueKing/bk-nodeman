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
import traceback
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from apps.core.concurrent import controller
from apps.node_man import models
from apps.utils import concurrent, exc
from common.api import CCApi

from .. import base
from .base import AgentBaseService, AgentCommonData


def exc_handler(
    wrapped: Callable, instance: base.BaseService, args: Tuple[Any], kwargs: Dict[str, Any], _exc: Exception
):
    failed_sub_inst_ids: List[int] = []
    host_id__sub_inst_id_map: Dict[int, int] = kwargs["host_id__sub_inst_id_map"]
    host_agent_relations: List[Dict[str, Union[int, str]]] = kwargs["host_agent_relations"]
    for host_agent_relation in host_agent_relations:
        failed_sub_inst_ids.append(host_id__sub_inst_id_map[host_agent_relation["bk_host_id"]])
    # 该方法具备原子性，如果出现异常表示该批次全部失败
    instance.move_insts_to_failed(failed_sub_inst_ids, str(_exc))
    instance.log_debug(failed_sub_inst_ids, log_content=traceback.format_exc(), fold=True)
    return []


class BindHostAgentService(AgentBaseService):
    @controller.ConcurrentController(
        data_list_name="host_agent_relations",
        batch_call_func=concurrent.batch_call,
        get_config_dict_func=lambda: {"limit": 200},
    )
    @exc.ExceptionHandler(exc_handler=exc_handler)
    def bind_host_agent(
        self,
        host_id__sub_inst_id_map: Dict[int, int],
        host_agent_relations: List[Dict[str, Union[int, str]]],
    ) -> List[int]:
        """
        绑定 Agent 到 主机
        :param host_id__sub_inst_id_map: 主机ID - 订阅实例ID 映射
        :param host_agent_relations: 主机 Agent 绑定关系
        :return:
        """
        CCApi.bind_host_agent({"list": host_agent_relations})
        succeed_host_ids: List[int] = []
        for host_agent_relation in host_agent_relations:
            succeed_host_ids.append(host_agent_relation["bk_host_id"])
            self.log_info(
                sub_inst_ids=host_id__sub_inst_id_map[host_agent_relation["bk_host_id"]],
                log_content=_("已将 Agent[bk_agent_id: {bk_agent_id}] 绑定到 主机[bk_host_id: {bk_host_id}]").format(
                    bk_agent_id=host_agent_relation["bk_agent_id"], bk_host_id=host_agent_relation["bk_host_id"]
                ),
            )
        return succeed_host_ids

    @controller.ConcurrentController(
        data_list_name="host_agent_relations",
        batch_call_func=concurrent.batch_call,
        get_config_dict_func=lambda: {"limit": 200},
    )
    @exc.ExceptionHandler(exc_handler=exc_handler)
    def unbind_host_agent(
        self,
        host_agent_relations: List[Dict[str, Union[int, str]]],
    ) -> List[int]:
        """
        解除主机和 Agent 间的绑定关系
        :param host_agent_relations: 主机 Agent 绑定关系
        :return:
        """
        succeed_host_ids: List[int] = []
        CCApi.unbind_host_agent({"list": host_agent_relations})
        for host_agent_relation in host_agent_relations:
            succeed_host_ids.append(host_agent_relation["bk_host_id"])
        return succeed_host_ids

    def _execute(self, data, parent_data, common_data: AgentCommonData):
        host_ids: List[int] = []
        agent_ids: List[str] = []
        sub_inst_ids_without_agent_id: Set[int] = set()
        host_agent_relations: List[Dict[str, Union[int, str]]] = []

        for sub_inst in common_data.subscription_instances:
            bk_host_id: int = common_data.sub_inst_id__host_id_map[sub_inst.id]
            bk_agent_id: Optional[str] = sub_inst.instance_info["host"].get("bk_agent_id")
            if bk_agent_id:
                host_ids.append(bk_host_id)
                agent_ids.append(bk_agent_id)
                host_agent_relations.append({"bk_host_id": bk_host_id, "bk_agent_id": bk_agent_id})
            else:
                sub_inst_ids_without_agent_id.add(sub_inst.id)

        if sub_inst_ids_without_agent_id:
            self.move_insts_to_failed(sub_inst_ids=sub_inst_ids_without_agent_id, log_content=_("bk_agent_id 不存在"))

        # 找出准备注册的 AgentID 所属的其他主机
        # 这种情况一般出现于动态主机复用 AgentID，此时需要将旧主机的 AgentID 绑定关系释放掉
        need_release_host_agent_relations: List[Dict[str, Union[int, str]]] = list(
            models.Host.objects.filter(Q(bk_agent_id__in=agent_ids) & ~Q(bk_host_id__in=host_ids)).values(
                "bk_host_id", "bk_agent_id"
            )
        )
        if need_release_host_agent_relations:
            succeed_unbind_host_ids: List[int] = self.unbind_host_agent(
                host_agent_relations=need_release_host_agent_relations
            )
            models.Host.objects.filter(bk_host_id__in=succeed_unbind_host_ids).update(bk_agent_id=None)

        if host_agent_relations:
            report_agent_id_hosts: List[models.Host] = [
                models.Host(
                    bk_host_id=host_agent_relation["bk_host_id"], bk_agent_id=host_agent_relation["bk_agent_id"]
                )
                for host_agent_relation in host_agent_relations
            ]
            models.Host.objects.bulk_update(report_agent_id_hosts, fields=["bk_agent_id"])
            self.bind_host_agent(
                host_id__sub_inst_id_map=common_data.host_id__sub_inst_id_map, host_agent_relations=host_agent_relations
            )
