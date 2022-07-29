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

from typing import Dict, List, Optional, Set, Union

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from apps.core.concurrent import controller
from apps.node_man import models
from apps.utils import concurrent, exc
from common.api import CCApi

from . import bind_host_agent
from .base import AgentBaseService, AgentCommonData


class UnBindHostAgentService(AgentBaseService):
    @controller.ConcurrentController(
        data_list_name="host_agent_relations",
        batch_call_func=concurrent.batch_call,
        get_config_dict_func=lambda: {"limit": 200},
    )
    @exc.ExceptionHandler(exc_handler=bind_host_agent.exc_handler)
    def unbind_host_agent(
        self,
        host_id__sub_inst_id_map: Dict[int, int],
        host_agent_relations: List[Dict[str, Union[int, str]]],
    ) -> List[int]:
        """
        解除主机和 Agent 间的绑定关系
        :param host_id__sub_inst_id_map: 主机ID - 订阅实例ID 映射
        :param host_agent_relations: 主机 Agent 绑定关系
        :return:
        """
        CCApi.unbind_host_agent({"list": host_agent_relations})
        succeed_host_ids: List[int] = []
        for host_agent_relation in host_agent_relations:
            succeed_host_ids.append(host_agent_relation["bk_host_id"])
            self.log_info(
                sub_inst_ids=host_id__sub_inst_id_map[host_agent_relation["bk_host_id"]],
                log_content=_("已将 Agent[bk_agent_id: {bk_agent_id}] 和 主机[bk_host_id: {bk_host_id}] 之间的绑定关系解除").format(
                    bk_agent_id=host_agent_relation["bk_agent_id"], bk_host_id=host_agent_relation["bk_host_id"]
                ),
            )
        return succeed_host_ids

    def _execute(self, data, parent_data, common_data: AgentCommonData):
        host_ids_without_agent_id: List[int] = []
        sub_inst_ids_without_agent_id: Set[int] = set()
        host_agent_relations: List[Dict[str, Union[int, str]]] = []

        # 对于解绑操作，以配置平台侧实时数据为准
        for sub_inst in common_data.subscription_instances:
            bk_host_id: int = common_data.sub_inst_id__host_id_map[sub_inst.id]
            bk_agent_id: Optional[str] = sub_inst.instance_info["host"].get("bk_agent_id")
            if bk_agent_id:
                host_agent_relations.append({"bk_host_id": bk_host_id, "bk_agent_id": bk_agent_id})
            else:
                host_ids_without_agent_id.append(bk_host_id)
                sub_inst_ids_without_agent_id.add(sub_inst.id)

        if sub_inst_ids_without_agent_id:
            self.log_info(sub_inst_ids=sub_inst_ids_without_agent_id, log_content=_("不存在绑定关系，无需解绑"))

        if host_agent_relations:
            succeed_unbind_host_ids: List[int] = self.unbind_host_agent(
                host_id__sub_inst_id_map=common_data.host_id__sub_inst_id_map, host_agent_relations=host_agent_relations
            )
        else:
            succeed_unbind_host_ids: List[int] = []

        # 此处将两类主机的 AgentID 置空
        # 1. 配置平台侧无 AgentID 的主机：避免 DB 存在脏数据
        # 2. 解绑成功的主机
        models.Host.objects.filter(bk_host_id__in=succeed_unbind_host_ids + host_ids_without_agent_id).update(
            bk_agent_id=None, updated_at=timezone.now()
        )
