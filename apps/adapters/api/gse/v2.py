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

import typing
from collections import Mapping

from apps.node_man import constants, models

from . import base
from .v1 import GseV1ApiHelper


class GseV2ApiHelper(GseV1ApiHelper):
    def get_agent_id(self, mixed_types_of_host_info: typing.Union[base.InfoDict, models.Host]) -> str:
        if isinstance(mixed_types_of_host_info, Mapping):
            if "host" in mixed_types_of_host_info:
                return self.get_agent_id(mixed_types_of_host_info["host"])
            bk_agent_id: typing.Optional[str] = mixed_types_of_host_info.get("bk_agent_id")
        else:
            bk_agent_id: typing.Optional[int] = getattr(mixed_types_of_host_info, "bk_agent_id")
        if not bk_agent_id:
            return super(GseV2ApiHelper, self).get_agent_id(mixed_types_of_host_info)
        return bk_agent_id

    def _list_proc_state(
        self,
        namespace: str,
        proc_name: str,
        labels: base.InfoDict,
        host_info_list: base.InfoDictList,
        extra_meta_data: base.InfoDict,
        **options
    ) -> base.AgentIdInfoMap:
        agent_id_list: typing.List[str] = [self.get_agent_id(host_info) for host_info in host_info_list]
        query_params: base.InfoDict = {
            "meta": {"namespace": constants.GSE_NAMESPACE, "name": proc_name, "labels": {"proc_name": proc_name}},
            "agent_id_list": agent_id_list,
        }
        proc_infos: base.InfoDictList = (
            self.gse_api_obj.v2_proc_get_proc_status_v2(query_params).get("proc_infos") or []
        )
        agent_id__proc_info_map: base.AgentIdInfoMap = {}
        for proc_info in proc_infos:
            proc_info["host"]["bk_agent_id"] = proc_info["bk_agent_id"]
            agent_id__proc_info_map[self.get_agent_id(proc_info)] = {
                "version": self.get_version(proc_info.get("version")),
                "status": constants.PLUGIN_STATUS_DICT[proc_info["status"]],
                "is_auto": constants.AutoStateType.AUTO if proc_info["isauto"] else constants.AutoStateType.UNAUTO,
                "name": proc_info["meta"]["name"],
            }
        return agent_id__proc_info_map

    def _list_agent_state(self, host_info_list: base.InfoDictList) -> base.AgentIdInfoMap:
        agent_id_list: typing.List[str] = [self.get_agent_id(host_info) for host_info in host_info_list]
        agent_state_list: base.InfoDictList = self.gse_api_obj.v2_cluster_list_agent_state(
            {"agent_id_list": agent_id_list}
        )
        agent_id__state_map: base.AgentIdInfoMap = {}
        for agent_state in agent_state_list:
            status_code: typing.Optional[int] = agent_state.pop("status_code", None)
            if status_code == constants.GseAgentStatusCode.RUNNING.value:
                agent_state["bk_agent_alive"] = constants.BkAgentStatus.ALIVE.value
            else:
                agent_state["bk_agent_alive"] = constants.BkAgentStatus.NOT_ALIVE.value
            agent_id__state_map[agent_state["bk_agent_id"]] = agent_state
        return agent_id__state_map

    def preprocessing_proc_operate_info(
        self, host_info_list: base.InfoDictList, proc_operate_info: base.InfoDict
    ) -> base.InfoDict:
        proc_operate_info["agent_id_list"] = [self.get_agent_id(host_info) for host_info in host_info_list]
        return proc_operate_info

    def _operate_proc_multi(self, proc_operate_req: base.InfoDictList, **options) -> str:
        return self.gse_api_obj.v2_proc_operate_proc_multi({"proc_operate_req": proc_operate_req})["task_id"]

    def get_proc_operate_result(self, task_id: str) -> base.InfoDict:
        return self.gse_api_obj.v2_proc_get_proc_operate_result_v2({"task_id": task_id}, raw=True)
