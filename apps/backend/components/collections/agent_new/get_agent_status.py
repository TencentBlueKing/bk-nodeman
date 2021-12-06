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

from collections import defaultdict
from typing import Any, Dict, List

from django.utils.translation import ugettext_lazy as _

from apps.component.esbclient import client_v2
from apps.node_man import constants, models
from apps.node_man.models import Host, ProcessStatus
from pipeline.core.flow import Service, StaticIntervalGenerator

from .base import AgentBaseService, AgentCommonData


class GetAgentStatusService(AgentBaseService):

    __need_schedule__ = True
    interval = StaticIntervalGenerator(5)

    def inputs_format(self):
        return [
            Service.InputItem(name="expect_status", key="expect_status", type="str", required=True),
        ]

    def _execute(self, data, parent_data, common_data: AgentCommonData, callback_data=None):
        expect_status = data.get_one_of_inputs("expect_status")
        host_id_obj_map = common_data.host_id_obj_map
        subscription_instances = common_data.subscription_instances
        subscription_instance_ids = common_data.subscription_instance_ids
        batch_size = models.GlobalSettings.get_config("BATCH_SIZE", default=100)
        host_ids = list(common_data.bk_host_ids)

        create_proc_status_host_id_list: List[int] = []
        delete_proc_status_id_list: List[Dict[str, Any]] = []
        proc_statistics_map: Dict[int, Dict[str, Any]] = defaultdict(lambda: defaultdict(list))
        to_be_created_process_status: List[models.ProcessStatus] = []
        host_id_to_inst_id_map: Dict[int, int] = defaultdict()

        for subscription_instance in subscription_instances:
            bk_host_id = subscription_instance.instance_info["host"]["bk_host_id"]
            subscription_instance_ids.add(subscription_instance.id)
            host_id_to_inst_id_map[bk_host_id] = subscription_instance.id

        status_queryset = ProcessStatus.objects.filter(
            bk_host_id__in=host_ids,
            name=ProcessStatus.GSE_AGENT_PROCESS_NAME,
            source_type=ProcessStatus.SourceType.DEFAULT,
        )
        if not status_queryset:
            create_proc_status_host_id_list = host_ids
        else:
            for proc_status in status_queryset:
                count = proc_statistics_map[proc_status.bk_host_id]["count"] or 0
                proc_statistics_map[proc_status.bk_host_id]["count"] = count + 1
                proc_statistics_map[proc_status.bk_host_id]["proc_ids"].append(proc_status.id)
            for host_id, statistics in proc_statistics_map.items():
                if statistics["count"] > 1:
                    delete_proc_status_id_list.append(statistics["proc_ids"][1:])
                elif statistics["count"] == 0:
                    create_proc_status_host_id_list.append(host_id)

        # 创建不存在的进程记录
        if create_proc_status_host_id_list:
            for host_id in create_proc_status_host_id_list:
                to_be_created_process_status.append(
                    ProcessStatus(
                        bk_host_id=host_id,
                        name=ProcessStatus.GSE_AGENT_PROCESS_NAME,
                        source_type=ProcessStatus.SourceType.DEFAULT,
                    )
                )
            ProcessStatus.objects.bulk_create(to_be_created_process_status, batch_size=batch_size)

        # 删掉多余进程记录
        if delete_proc_status_id_list:
            status_queryset.filter(id__in=delete_proc_status_id_list).delete()

        unexpected_status_agents = self.get_agent_statues(
            host_ids,
            expect_status=expect_status,
            batch_size=batch_size,
            host_id_to_inst_id_map=host_id_to_inst_id_map,
            host_id_obj_map=host_id_obj_map,
        )

        if not unexpected_status_agents:
            self.__need_schedule__ = False
            self.clear_expired_outputs(data)
            return True
        data.set_outputs("unexpected_status_agents", unexpected_status_agents)
        data.set_outputs("host_id_obj_map", host_id_obj_map)
        data.set_outputs("host_id_to_inst_id_map", host_id_to_inst_id_map)

    @classmethod
    def clear_expired_outputs(cls, data):
        outputs = ["unexpected_status_agents", "host_id_to_inst_id_map", "host_id_obj_map"]
        for output in outputs:
            if hasattr(data.outputs, output):
                delattr(data.outputs, output)

    def _schedule(self, data, parent_data, callback_data=None):
        expect_status = data.get_one_of_inputs("expect_status")
        host_id_to_inst_id_map = data.get_one_of_outputs("host_id_to_inst_id_map")
        host_id_obj_map = data.get_one_of_outputs("host_id_obj_map")
        batch_size = models.GlobalSettings.get_config("BATCH_SIZE", default=100)
        schedule_agent_ids = data.get_one_of_outputs("unexpected_status_agents")
        inst_ids = [host_id_to_inst_id_map[host_id] for host_id in schedule_agent_ids]
        if self.interval.count > 60:
            self.move_insts_to_failed(sub_inst_ids=inst_ids, log_content=_("查询GSE主机状态超时"))
            self.finish_schedule()
            self.clear_expired_outputs(data)
            return False
        unexpected_status_agents = self.get_agent_statues(
            schedule_agent_ids,
            expect_status=expect_status,
            batch_size=batch_size,
            host_id_to_inst_id_map=host_id_to_inst_id_map,
            host_id_obj_map=host_id_obj_map,
        )
        if not unexpected_status_agents:
            self.clear_expired_outputs(data)
            self.finish_schedule()
            return True
        data.set_outputs("unexpected_status_agents", unexpected_status_agents)

    def get_agent_statues(
        self,
        host_ids: List[int],
        expect_status: Any,
        batch_size: int,
        host_id_to_inst_id_map: Dict[int, int],
        host_id_obj_map: Dict[int, models.Host],
    ):
        unexpected_status_agents: List[int] = []
        host_key_map = defaultdict()
        update_proc_list: Dict[str, List[models.ProcessStatus]] = defaultdict(list)
        update_host_list: Dict[str, List[models.Host]] = defaultdict(list)
        except_status_agents: Dict[str, Dict[str, Any]] = defaultdict(lambda: defaultdict(list))

        inst_ids = [host_id_to_inst_id_map[host_id] for host_id in host_ids]
        agent_host = [
            {"ip": host_id_obj_map[host_id], "bk_cloud_id": host_id_obj_map[host_id].bk_host_id} for host_id in host_ids
        ]

        for host_id in host_ids:
            key = "{}:{}".format(host_id_obj_map[host_id].bk_cloud_id, host_id_obj_map[host_id].inner_ip)
            host_key_map[key] = host_id

        try:
            agent_status_data = client_v2.gse.get_agent_status({"hosts": agent_host})
            agent_info_data = client_v2.gse.get_agent_info({"hosts": agent_host})
        except Exception as error:
            self.move_insts_to_failed(sub_inst_ids=inst_ids, log_content=_(f"get agent status error, {error}"))
            return

        for key, agent_status in agent_status_data.items():
            # 先处理预期状态的agent
            status = constants.PROC_STATUS_DICT[agent_status["bk_agent_alive"]]
            host_id = host_key_map[key]
            if status == expect_status:
                version = agent_info_data[key]["version"]
                host_ids = except_status_agents[version]["host_ids"]
                inst_ids = except_status_agents[version]["inst_ids"]
                host_ids.append(host_id)
                inst_ids.append(host_id_to_inst_id_map[host_id])
                except_status_agents[version] = {
                    "host_ids": host_ids,
                    "version": version,
                    "status": status,
                    "inst_ids": inst_ids,
                }

                update_proc_list[version].append(
                    ProcessStatus(
                        bk_host_id=host_id,
                        name=ProcessStatus.GSE_AGENT_PROCESS_NAME,
                        source_type=ProcessStatus.SourceType.DEFAULT,
                        version=agent_info_data[key]["version"],
                        status=agent_status["bk_agent_alive"],
                    )
                )

                update_host_list[version].append(
                    Host(
                        bk_host_id=host_id,
                        node_from=constants.NodeFrom.NODE_MAN,
                    )
                )
                for version, except_agents in except_status_agents.items():
                    # 以版本号为纬度更新表并且打印日志
                    proc_objs: List[ProcessStatus] = []
                    host_objs: List[Host] = []
                    proc_queryset = ProcessStatus.objects.filter(
                        bk_host_id__in=except_agents["host_ids"],
                        name=ProcessStatus.GSE_AGENT_PROCESS_NAME,
                        source_type=ProcessStatus.SourceType.DEFAULT,
                        is_latest=True,
                    )
                    host_queryset = Host.objects.filter(
                        bk_host_id__in=except_agents["host_ids"], node_from=constants.NodeFrom.CMDB
                    )
                    for host_query in host_queryset:
                        host_objs.append(Host(pk=host_query.id, node_from=constants.NodeFrom.NODE_MAN))
                    for proc in proc_queryset:
                        proc_objs.append(
                            ProcessStatus(
                                pk=proc.id,
                                status=except_agents["status"],
                                version=except_agents["version"],
                            )
                        )
                    ProcessStatus.objects.bulk_update(
                        proc_objs,
                        ["version", "status"],
                        batch_size=batch_size,
                    )
                    Host.objects.bulk_update(
                        host_objs,
                        ["node_from"],
                        batch_size=batch_size,
                    )

                    self.log_info(
                        sub_inst_ids=except_agents["inst_ids"],
                        log_content=_("查询GSE主机状态为{status}, 版本为{version}").format(
                            status=status,
                            version=version,
                        ),
                    )
            else:
                unexpected_status_agents.append(host_key_map[key])

        return unexpected_status_agents
