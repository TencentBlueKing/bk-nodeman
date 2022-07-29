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
from typing import Any, Callable, Dict, List, Set, Tuple, Union

from django.utils.translation import ugettext_lazy as _

from apps.core.concurrent import controller
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

    def _execute(self, data, parent_data, common_data: AgentCommonData):
        sub_inst_ids_without_agent_id: Set[int] = set()
        host_agent_relations: List[Dict[str, Union[int, str]]] = []
        # 对于绑定操作，此时应用侧 DB 的 bk_agent_id 最新，取该值进行绑定
        for bk_host_id, host in common_data.host_id_obj_map.items():
            if host.bk_agent_id:
                host_agent_relations.append({"bk_host_id": bk_host_id, "bk_agent_id": host.bk_agent_id})
            else:
                sub_inst_ids_without_agent_id.add(common_data.host_id__sub_inst_id_map[bk_host_id])

        if sub_inst_ids_without_agent_id:
            self.move_insts_to_failed(sub_inst_ids=sub_inst_ids_without_agent_id, log_content=_("bk_agent_id 不存在"))

        if host_agent_relations:
            self.bind_host_agent(
                host_id__sub_inst_id_map=common_data.host_id__sub_inst_id_map, host_agent_relations=host_agent_relations
            )
