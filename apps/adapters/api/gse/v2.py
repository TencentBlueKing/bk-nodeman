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
import logging
import typing
from collections import Mapping

from django.conf import settings

from apps.exceptions import ApiResultError
from apps.node_man import constants, models

from . import base
from .v1 import GseV1ApiHelper

logger = logging.getLogger("app")


class GseV2ApiHelper(GseV1ApiHelper):
    def get_agent_id(self, mixed_types_of_host_info: typing.Union[base.InfoDict, models.Host]) -> str:

        # 如果动态寻址配置未开启，暂不启用 AgentID
        if not settings.BKAPP_ENABLE_DHCP:
            return super(GseV2ApiHelper, self).get_agent_id(mixed_types_of_host_info)

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
        **options,
    ) -> base.AgentIdInfoMap:
        agent_id_list: typing.List[str] = list({self.get_agent_id(host_info) for host_info in host_info_list})
        query_params: base.InfoDict = {
            "meta": {"namespace": constants.GSE_NAMESPACE, "name": proc_name, "labels": {"proc_name": proc_name}},
            "agent_id_list": agent_id_list,
            "no_request": True,
        }
        proc_infos: base.InfoDictList = self.gse_api_obj.get_proc_status_v2(query_params).get("proc_infos") or []
        agent_id__proc_info_map: base.AgentIdInfoMap = {}
        for proc_info in proc_infos:
            proc_info["host"]["bk_agent_id"] = proc_info["bk_agent_id"]
            agent_id__proc_info_map[self.get_agent_id(proc_info)] = {
                "version": proc_info.get("version") or "",
                "status": constants.PLUGIN_STATUS_DICT[proc_info["status"]],
                "is_auto": constants.AutoStateType.AUTO if proc_info["isauto"] else constants.AutoStateType.UNAUTO,
                "name": proc_info["meta"]["name"],
            }
        return agent_id__proc_info_map

    def _list_agent_state(self, host_info_list: base.InfoDictList) -> base.AgentIdInfoMap:
        agent_id_list: typing.List[str] = list({self.get_agent_id(host_info) for host_info in host_info_list})

        try:
            if not agent_id_list:
                agent_state_list = []
            else:
                agent_state_list: base.InfoDictList = self.gse_api_obj.list_agent_state(
                    {"agent_id_list": agent_id_list, "no_request": True}
                )
        except ApiResultError as err:
            if err.code == 1011003:
                # 1011003 表示传入 agent_id_list 均查询不到 Agent 信息，这种情况下取 Agent 默认状态
                logging.warning(
                    f"Call GSE API list_agent_state failed: "
                    f"err -> {err}, ignored -> all agents not found, set agent_state_list =  []"
                )
                agent_state_list = []
            else:
                logging.exception(f"Call GSE API list_agent_state failed: agent_id_list -> {agent_id_list}")
                raise

        agent_id__state_map: base.AgentIdInfoMap = {}
        agent_id__state_partial_map: base.AgentIdInfoMap = {
            agent_state["bk_agent_id"]: agent_state for agent_state in agent_state_list
        }
        for agent_id in agent_id_list:
            # 若查询不到状态信息，填充默认值
            agent_state: base.InfoDict = agent_id__state_partial_map.get(
                agent_id,
                {"bk_agent_id": agent_id, "version": "", "status_code": constants.GseAgentStatusCode.NOT_FOUND.value},
            )
            status_code: typing.Optional[int] = (
                agent_state.pop("status_code", None) or constants.GseAgentStatusCode.NOT_FOUND.value
            )
            if status_code == constants.GseAgentStatusCode.RUNNING.value:
                agent_state["bk_agent_alive"] = constants.BkAgentStatus.ALIVE.value
            else:
                agent_state["bk_agent_alive"] = constants.BkAgentStatus.NOT_ALIVE.value
            agent_id__state_map[agent_id] = agent_state

        return agent_id__state_map

    def preprocessing_proc_operate_info(
        self, host_info_list: base.InfoDictList, proc_operate_info: base.InfoDict
    ) -> base.InfoDict:
        proc_operate_info["agent_id_list"] = list({self.get_agent_id(host_info) for host_info in host_info_list})
        return proc_operate_info

    def _operate_proc_multi(self, proc_operate_req: base.InfoDictList, **options) -> str:
        return self.gse_api_obj.operate_proc_multi({"proc_operate_req": proc_operate_req, "no_request": True})[
            "task_id"
        ]

    def _upgrade_to_agent_id(self, hosts: base.InfoDictList) -> base.InfoDict:
        return self.gse_api_obj.upgrade_to_agent_id({"hosts": hosts, "no_request": True})

    def get_proc_operate_result(self, task_id: str) -> base.InfoDict:
        return self.gse_api_obj.get_proc_operate_result_v2({"task_id": task_id, "no_request": True}, raw=True)
