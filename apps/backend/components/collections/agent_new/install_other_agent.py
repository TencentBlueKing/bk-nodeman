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
from typing import Any, Dict, List

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from apps.backend.api.constants import (
    INSTALL_OTHER_AGENT_POLLING_TIMEOUT,
    POLLING_INTERVAL,
)
from apps.core.gray.constants import INSTALL_OTHER_AGENT_AP_ID_OFFSET
from apps.core.gray.handlers import GrayHandler
from apps.exceptions import ApiError
from apps.node_man import models
from apps.node_man.constants import JobStatusType, OpType
from apps.node_man.handlers.job import JobHandler
from apps.node_man.models import GlobalSettings
from apps.utils.batch_request import request_multi_thread
from common.api import NodeApi
from env.constants import GseVersion
from pipeline.core.flow.activity import StaticIntervalGenerator

from .base import AgentBaseService, AgentCommonData


class InstallOtherAgentService(AgentBaseService):
    """
    安装额外Agent
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(POLLING_INTERVAL)

    def _execute(self, data, parent_data, common_data: AgentCommonData):
        extra_agent_version: str = data.get_one_of_inputs("extra_agent_version")
        node_type: str = data.get_one_of_inputs("node_type")
        install_other_agent_blacklist: Dict[str, List[int]] = {
            GseVersion.V1.value: GlobalSettings.get_config(
                key=GlobalSettings.KeyEnum.INSTALL_OTHER_AGENT_V1_BIZ_BLACKLIST.value, default=[]
            ),
            GseVersion.V2.value: GlobalSettings.get_config(
                key=GlobalSettings.KeyEnum.INSTALL_OTHER_AGENT_V2_BIZ_BLACKLIST.value, default=[]
            ),
        }
        biz_blacklist: List[int] = install_other_agent_blacklist[extra_agent_version]

        # 生成安装参数
        try:
            gray_ap_map: Dict[int, int] = GrayHandler.get_gray_ap_map()
            gray_ap_map.update({v: k for k, v in gray_ap_map.items()})
        except ApiError:
            gray_ap_map: Dict[int, int] = {}

        host_id_identity_data_map: Dict[int, models.IdentityData] = models.IdentityData.host_id_identity_data_map(
            **{"bk_host_id__in": list(common_data.bk_host_ids)}
        )

        hosts: List[Dict[str, Any]] = []
        sub_inst_ids: List[int] = []
        for sub_inst in common_data.subscription_instances:
            bk_host_id: int = common_data.sub_inst_id__host_id_map[sub_inst.id]
            host = common_data.host_id_obj_map[bk_host_id]
            if host.bk_biz_id in biz_blacklist:
                self.log_info(
                    sub_inst.id,
                    log_content=_(
                        "当前主机所处业务[{bk_biz_id}] 无需要额外安装 GSE [{gse_version}] Agent.".format(
                            bk_biz_id=host.bk_biz_id, gse_version=extra_agent_version
                        )
                    ),
                )
                continue
            identty_data = host_id_identity_data_map[bk_host_id]
            ap_id = gray_ap_map.get(host.ap_id)
            if ap_id is None:
                self.log_info(sub_inst.id, log_content=_("未配置与接入点ID:[{ap_id}]对应的映射,跳过此安装步骤".format(ap_id=host.ap_id)))
                continue

            sub_inst_ids.append(sub_inst.id)
            # AP_ID 偏移规则 ap_id * 100000 + install_channel_id
            offset_ap_id = ap_id * INSTALL_OTHER_AGENT_AP_ID_OFFSET + (host.install_channel_id or 0)
            hosts.append(
                {
                    "bk_host_id": host.bk_host_id,
                    "os_type": host.os_type,
                    "bk_addressing": host.bk_addressing,
                    "port": identty_data.port,
                    "auth_type": identty_data.auth_type,
                    "password": identty_data.password,
                    "account": identty_data.account,
                    "key": identty_data.key or "",
                    "inner_ip": host.inner_ip,
                    "inner_ipv6": host.inner_ipv6 or "",
                    "outer_ip": host.outer_ip or "",
                    "outer_ipv6": host.outer_ipv6 or "",
                    "login_ip": host.login_ip,
                    "bk_biz_id": host.bk_biz_id,
                    "ap_id": offset_ap_id,
                    "bk_cloud_id": host.bk_cloud_id,
                    "is_manual": False,
                    "install_channel_id": host.install_channel_id,
                    "peer_exchange_switch_for_agent": host.extra_data.get("peer_exchange_switch_for_agent", 0),
                }
            )

        if hosts:
            install_params: Dict[str, Any] = {
                "job_type": f"{OpType.INSTALL}_{node_type}",
                "is_install_latest_plugins": False,
                "is_install_other_agent": True,
                "hosts": hosts,
            }
            job_result: Dict[str, Any] = NodeApi.install(install_params)
            # 对请求的hosts输出任务连接
            self.log_info(
                sub_inst_ids=sub_inst_ids,
                log_content=_(
                    '{log}\n作业任务ID为 [{node_man_task_id}]，点击跳转到 <a href="{link}" target="_blank">[节点管理]</a>'
                ).format(
                    log=_("安装额外Agent任务已启动"),
                    node_man_task_id=job_result["job_id"],
                    link=job_result["job_url"],
                ),
            )

            data.outputs.job_result = job_result

        data.outputs.host_count = len(hosts)
        data.outputs.polling_time = 0
        return True

    def _schedule(self, data, parent_data, callback_data=None):
        host_count: int = data.get_one_of_outputs("host_count")
        if host_count == 0:
            self.finish_schedule()
            return True

        common_data = self.get_common_data(data)
        polling_time: int = data.get_one_of_outputs("polling_time")
        next_polling_time: int = polling_time + POLLING_INTERVAL
        job_result: Dict[str, Any] = data.get_one_of_outputs("job_result")

        pagesize: int = 100
        params_list: List[Dict[str, int]] = [
            {
                "params": {"page": page, "pagesize": pagesize, "pk": job_result["job_id"]},
            }
            for page in range(1, host_count + 1, pagesize)
        ]
        # TODO: 由于apigw接口与esb接口路径存在不一致情况暂不使用接口直接使用JobHandler
        # task_results = request_multi_thread(NodeApi.job_details, params_list, lambda x: x["list"])
        task_results = request_multi_thread(JobHandler(job_result["job_id"]).retrieve, params_list, lambda x: x["list"])

        host_id_status_map: Dict[str, Dict[str, Any]] = {}
        for instance in task_results:
            host_id_status_map[instance["bk_host_id"]] = instance

        running_inst_ids: List[int] = []
        for sub_inst in common_data.subscription_instances:
            bk_host_id: int = common_data.sub_inst_id__host_id_map[sub_inst.id]
            if host_id_status_map[bk_host_id]["status"] in JobStatusType.PROCESSING_STATUS:
                running_inst_ids.append(sub_inst.id)
            elif host_id_status_map[bk_host_id]["status"] == JobStatusType.SUCCESS:
                pass
            else:
                if host_id_status_map[bk_host_id]["status"] == JobStatusType.FAILED:
                    log_link: str = "{bk_nodeman_host}/#/task-list/{job_id}/log/{instance_id}".format(
                        bk_nodeman_host=settings.BK_NODEMAN_HOST,
                        job_id=job_result["job_id"],
                        instance_id=host_id_status_map[bk_host_id]["instance_id"],
                    )
                    error_log: str = _(
                        '{log}\n作业任务ID为 [{node_man_task_id}]，点击跳转到 <a href="{link}" target="_blank">[节点管理]</a> 查看详情'
                    ).format(
                        log=_("安装额外Agent失败"),
                        node_man_task_id=job_result["job_id"],
                        link=log_link,
                    )
                    self.move_insts_to_failed([sub_inst.id], error_log)
                elif host_id_status_map[bk_host_id]["status"] in [
                    JobStatusType.REMOVED,
                    JobStatusType.TERMINATED,
                    JobStatusType.FILTERED,
                    JobStatusType.IGNORED,
                    JobStatusType.PART_FAILED,
                ]:
                    error_log: str = _("安装额外Agent失败, 请点任务链接查看详情")
                    self.move_insts_to_failed([sub_inst.id], error_log)

        if next_polling_time > INSTALL_OTHER_AGENT_POLLING_TIMEOUT:
            # 任务执行超时
            self.log_error(
                running_inst_ids,
                _('{log}\n作业任务ID为 [{node_man_task_id}]，点击跳转到 <a href="{link}" target="_blank">[节点管理]</a> 查看详情').format(
                    log=_("安装额外Agent超时"),
                    node_man_task_id=job_result["job_id"],
                    link=job_result["job_url"],
                ),
            )
            self.finish_schedule()
            return False
        elif not running_inst_ids:
            # 没有在运行的任务
            self.finish_schedule()
            return True

        data.outputs.polling_time: int = next_polling_time
        return True
