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


class GseV1ApiHelper(base.GseApiBaseHelper):
    def get_agent_id(self, mixed_types_of_host_info: typing.Union[base.InfoDict, models.Host]) -> str:
        if isinstance(mixed_types_of_host_info, Mapping):
            if "host" in mixed_types_of_host_info:
                return self.get_agent_id(mixed_types_of_host_info["host"])
            bk_cloud_id: int = mixed_types_of_host_info["bk_cloud_id"]
            # v6 优先级最低
            for attr_name in ["ip", "inner_ip", "bk_host_innerip", "inner_ipv6", "bk_host_innerip_v6"]:
                ip = mixed_types_of_host_info.get(attr_name, "")
                if ip:
                    break
            if not ip:
                raise ValueError(f"can not get ip in dict type host info: {mixed_types_of_host_info}")
        else:
            bk_cloud_id: typing.Optional[int] = getattr(mixed_types_of_host_info, "bk_cloud_id")
            if bk_cloud_id is None:
                raise ValueError("can not get bk_cloud_id in obj type host info")
            for attr_name in ["inner_ip", "inner_ipv6"]:
                ip = getattr(mixed_types_of_host_info, attr_name, "")
                if ip:
                    break
            if not ip:
                raise ValueError("can not get ip in obj type host info")

        return f"{bk_cloud_id}:{ip}"

    def _list_proc_state(
        self,
        namespace: str,
        proc_name: str,
        labels: base.InfoDict,
        host_info_list: base.InfoDictList,
        extra_meta_data: base.InfoDict,
        **options,
    ) -> base.AgentIdInfoMap:
        hosts: base.InfoDictList = [
            {"ip": host_info["ip"], "bk_cloud_id": host_info["bk_cloud_id"]} for host_info in host_info_list
        ]
        query_params: base.InfoDict = {
            "meta": {"namespace": constants.GSE_NAMESPACE, "name": proc_name, "labels": {"proc_name": proc_name}},
            "hosts": hosts,
        }
        # 接口测试
        # 200: 0.3s-0.4s (0.41s 0.29s 0.33s)
        # 500: 0.35s-0.5s (0.34s 0.42s 0.51s)
        # 1000: 0.5s-0.6s (0.53s 0.56s 0.61s)
        # 2000: 0.9s (0.91s, 0.93s)
        # 5000: 2s-4s (2.3s 2.2s 4.1s 4.3s)
        proc_infos: base.InfoDictList = self.gse_api_obj.get_proc_status(query_params).get("proc_infos") or []
        agent_id__proc_info_map: base.AgentIdInfoMap = {}
        for proc_info in proc_infos:
            agent_id__proc_info_map[self.get_agent_id(proc_info)] = {
                "version": self.get_version(proc_info.get("version")),
                "status": constants.PLUGIN_STATUS_DICT[proc_info["status"]],
                "is_auto": constants.AutoStateType.AUTO if proc_info["isauto"] else constants.AutoStateType.UNAUTO,
                "name": proc_info["meta"]["name"],
            }
        return agent_id__proc_info_map

    def _list_agent_state(self, host_info_list: base.InfoDictList) -> base.AgentIdInfoMap:
        hosts: base.InfoDictList = [
            {"ip": host_info["ip"], "bk_cloud_id": host_info["bk_cloud_id"]} for host_info in host_info_list
        ]
        agent_id__info_map: base.AgentIdInfoMap = self.gse_api_obj.get_agent_info({"hosts": hosts})
        agent_id__status_map: base.AgentIdInfoMap = self.gse_api_obj.get_agent_status({"hosts": hosts})

        for agent_id, agent_info in agent_id__info_map.items():
            agent_info.update(agent_id__status_map.get(agent_id) or {})
            agent_info["version"] = self.get_version(agent_info.get("version"))
            agent_info["bk_agent_alive"] = agent_info.get("bk_agent_alive") or constants.BkAgentStatus.NOT_ALIVE.value

        return agent_id__info_map

    def preprocessing_proc_operate_info(
        self, host_info_list: base.InfoDictList, proc_operate_info: base.InfoDict
    ) -> base.InfoDict:
        proc_operate_info["hosts"] = [
            {"ip": host_info["ip"], "bk_cloud_id": host_info["bk_cloud_id"]} for host_info in host_info_list
        ]
        return proc_operate_info

    def _operate_proc_multi(self, proc_operate_req: base.InfoDictList, **options) -> str:
        return self.gse_api_obj.operate_proc_multi({"proc_operate_req": proc_operate_req})["task_id"]

    def get_proc_operate_result(self, task_id: str) -> base.InfoDict:
        return self.gse_api_obj.get_proc_operate_result({"task_id": task_id}, raw=True)
