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
from collections import defaultdict
from typing import Dict, List, Set, Union

from django.utils.translation import ugettext_lazy as _

from apps.backend.api.constants import POLLING_INTERVAL, POLLING_TIMEOUT
from apps.node_man import constants, models
from common.api import GseApi
from pipeline.core.flow import Service, StaticIntervalGenerator

from .base import AgentBaseService, AgentCommonData


class GetAgentStatusService(AgentBaseService):

    __need_schedule__ = True
    interval = StaticIntervalGenerator(POLLING_INTERVAL)

    def inputs_format(self):
        return super().inputs_format() + [
            Service.InputItem(name="expect_status", key="expect_status", type="str", required=True),
        ]

    def outputs_format(self):
        return super().outputs_format() + [
            Service.InputItem(name="polling_time", key="polling_time", type="int", required=True),
            Service.InputItem(name="host_ids_need_to_query", key="host_ids_need_to_query", type="list", required=True),
        ]

    def _execute(self, data, parent_data, common_data: AgentCommonData):
        expect_status = data.get_one_of_inputs("expect_status")
        self.log_info(
            sub_inst_ids=common_data.subscription_instance_ids,
            log_content=_("期望的 Agent 状态为 {expect_status_alias}「{expect_status}」").format(
                expect_status=expect_status,
                expect_status_alias=constants.PROC_STATUS_CHN.get(expect_status, expect_status),
            ),
        )
        # 保证进程记录唯一性
        self.maintain_agent_proc_status_uniqueness(bk_host_ids=common_data.bk_host_ids)

        data.outputs.polling_time = 0
        data.outputs.host_ids_need_to_query = list(common_data.bk_host_ids)

    def _schedule(self, data, parent_data, callback_data=None):
        common_data: AgentCommonData = self.get_common_data(data)
        expect_status = data.get_one_of_inputs("expect_status")
        host_ids_need_to_query: Set[int] = data.get_one_of_outputs("host_ids_need_to_query")

        # 构造 gse 请求参数
        hosts: List[Dict[str, Union[int, str]]] = []
        for host_id in host_ids_need_to_query:
            host_obj = common_data.host_id_obj_map[host_id]
            hosts.append({"ip": host_obj.inner_ip, "bk_cloud_id": host_obj.bk_cloud_id})

        # 请求 gse
        host_key__agent_info_map: Dict[str, Dict[str, Union[int, str]]] = GseApi.get_agent_info({"hosts": hosts})
        host_key__agent_status_info_map: Dict[str, Dict[str, Union[int, str]]] = GseApi.get_agent_status(
            {"hosts": hosts}
        )

        # 分隔符，用于构造 bk_cloud_id - ip，status - version 等键
        sep = ":"
        # 已获取期望状态的主机ID列表
        host_ids_get_expect_status: List[int] = []
        # 需要在下一个调度查询 Agent 相关信息的主机ID列表
        host_ids_need_to_next_query: List[int] = []
        # 按 status - version 聚合的主机ID列表
        host_ids_gby_status_version_key: Dict[str, List[int]] = defaultdict(list)
        # 主机ID - 订阅实例ID 映射关系
        host_id__sub_inst_id_map: Dict[int, int] = {
            host_id: sub_inst_id for sub_inst_id, host_id in common_data.sub_inst_id__host_id_map.items()
        }
        for host_id in host_ids_need_to_query:
            host_obj = common_data.host_id_obj_map[host_id]
            host_key = f"{host_obj.bk_cloud_id}{sep}{host_obj.inner_ip}"
            # 根据 host_key，取得 agent 版本及状态信息
            agent_info = host_key__agent_info_map.get(host_key, {"version": ""})
            # 默认值为 None 的背景：expect_status 是可传入的，不能设定一个明确状态作为默认值，不然可能与 expect_status 一致
            # 误判为当前 Agent 状态已符合预期
            agent_status_info = host_key__agent_status_info_map.get(host_key, {"bk_agent_alive": None})
            # 获取 agent 版本号及状态
            agent_status = constants.PROC_STATUS_DICT.get(agent_status_info["bk_agent_alive"], None)
            agent_version = agent_info["version"]

            self.log_info(
                host_id__sub_inst_id_map[host_id],
                log_content=_("查询 GSE 得到主机 [{host_key}] Agent 状态 -> {status_alias}「{status}」, 版本 -> {version}").format(
                    host_key=host_key,
                    status_alias=constants.PROC_STATUS_CHN.get(agent_status, agent_status),
                    status=agent_status,
                    version=agent_version or _("无"),
                ),
            )

            if agent_status != expect_status:
                host_ids_need_to_next_query.append(host_id)
            else:
                host_ids_get_expect_status.append(host_id)
                host_ids_gby_status_version_key[f"{agent_status}{sep}{agent_version}"].append(host_id)

        # 更新 ProcessStatus
        # status - version 的组合总类有限，聚合更新减少 DB 请求次数
        for status_version_key, bk_host_ids in host_ids_gby_status_version_key.items():
            status, version = status_version_key.split(sep=sep, maxsplit=1)
            models.ProcessStatus.objects.filter(**self.agent_proc_common_data, bk_host_id__in=bk_host_ids).update(
                status=status, version=version
            )

        # 将查询到期望状态的主机节点来源更新为 NODE_MAN
        host_ids_need_to_update_node_from = []
        for host_id in host_ids_get_expect_status:
            if common_data.host_id_obj_map[host_id].node_from != constants.NodeFrom.NODE_MAN:
                host_ids_need_to_update_node_from.append(host_id)
        models.Host.objects.filter(bk_host_id__in=host_ids_need_to_update_node_from).update(
            node_from=constants.NodeFrom.NODE_MAN
        )

        # 提前结束调度
        if not host_ids_need_to_next_query:
            data.outputs.host_ids_need_to_query = []
            self.finish_schedule()
            return

        polling_time = data.get_one_of_outputs("polling_time")
        if polling_time + POLLING_INTERVAL > POLLING_TIMEOUT:
            sub_inst_ids = [host_id__sub_inst_id_map[host_id] for host_id in host_ids_need_to_query]
            self.move_insts_to_failed(sub_inst_ids=sub_inst_ids, log_content=_("查询 GSE 超时"))
            self.finish_schedule()
            return

        data.outputs.polling_time = polling_time + POLLING_INTERVAL
        data.outputs.host_ids_need_to_query = host_ids_need_to_next_query
