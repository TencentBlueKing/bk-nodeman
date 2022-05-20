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
from typing import Any, Dict, List, Union

from django.utils.translation import ugettext_lazy as _

from apps.node_man import constants, models

from ..base import CommonData
from ..common.script_content import REACHABLE_SCRIPT_TEMPLATE
from .base import AgentCommonData, AgentExecuteScriptService


class CheckPolicyGseToProxyService(AgentExecuteScriptService):
    @property
    def script_name(self):
        return "is_target_reachable"

    def get_target_servers(
        self, data, common_data: CommonData, host: models.Host
    ) -> Dict[str, Union[List[Dict[str, Any]], List[int]]]:
        # 取接入点
        ap = common_data.ap_id_obj_map[host.ap_id]
        bt_file_server_queryset = models.Host.objects.filter(
            inner_ip__in=[bt_server["inner_ip"] for bt_server in ap.btfileserver], bk_cloud_id=constants.DEFAULT_CLOUD
        ).values_list("bk_host_id", flat=True)
        bt_file_server_ids: List[int] = [bk_host_id for bk_host_id in bt_file_server_queryset]

        return {
            "ip_list": [
                {
                    "bk_cloud_id": constants.DEFAULT_CLOUD,
                    "ip": bt_server["inner_ip"],
                }
                for bt_server in ap.btfileserver
            ],
            "host_id_list": bt_file_server_ids,
        }

    def get_script_content(self, data, common_data: AgentCommonData, host: models.Host) -> str:
        port_config = common_data.host_id__ap_map[host.bk_host_id].port_config
        return REACHABLE_SCRIPT_TEMPLATE % {
            "proxy_ip": host.outer_ip,
            "btsvr_thrift_port": port_config.get("btsvr_thrift_port"),
            "bt_port": port_config.get("bt_port"),
            "tracker_port": port_config.get("tracker_port"),
            "msg": _("请检查出口IP是否正确或策略是否开通"),
        }

    def _execute(self, data, parent_data, common_data: AgentCommonData):

        for sub_inst_id in common_data.subscription_instance_ids:
            bk_host_id = common_data.sub_inst_id__host_id_map[sub_inst_id]
            host = common_data.host_id_obj_map[bk_host_id]
            ap = common_data.host_id__ap_map[bk_host_id]
            port_config = ap.port_config
            self.log_info(
                sub_inst_id,
                _(
                    "请确保 GSE BT File Server 公网IP（{bt_server_ips}）到 Proxy 出口IP（{proxy_outer_ip}）的 "
                    "{btsvr_thrift_port}(tcp), {bt_port}-{tracker_port}(tcp/udp) 访问策略正常。\n"
                    "另外请注意：\n"
                    "1. 可执行 curl ipinfo.io 确认「出口IP」\n"
                    "2. 不支持多台 Proxy 使用同一个「出口IP」\n"
                    "3. 请保证「出口IP」固定不变"
                ).format(
                    bt_server_ips=",".join([bt_server["outer_ip"] for bt_server in ap.btfileserver]),
                    proxy_outer_ip=host.outer_ip,
                    btsvr_thrift_port=port_config.get("btsvr_thrift_port"),
                    bt_port=port_config.get("bt_port"),
                    tracker_port=port_config.get("tracker_port"),
                ),
            )

        return super()._execute(data, parent_data, common_data)
