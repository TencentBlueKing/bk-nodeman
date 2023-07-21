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

from apps.node_man.constants import QUERY_AGENT_STATUS_HOST_LENS
from apps.node_man.models import Host
from apps.node_man.periodic_tasks.sync_agent_status_task import (
    update_or_create_host_agent_status,
)
from common.log import logger


class HostTool:
    @classmethod
    def fill_agent_state_info_to_hosts(cls, host_infos: typing.List[typing.Dict[str, typing.Any]]):
        """
        实时查询 Agent 状态，并填充到主机信息列表中
        :param host_infos: 主机信息列表
        :return:
        """
        if len(host_infos) > QUERY_AGENT_STATUS_HOST_LENS:
            return

        bk_host_ids: typing.List[int] = [host_info["bk_host_id"] for host_info in host_infos]

        try:
            host_id__agent_state_info: typing.Dict[int, str] = update_or_create_host_agent_status(
                task_id="[fill_agent_state_info_to_hosts]",
                host_queryset=Host.objects.filter(bk_host_id__in=bk_host_ids),
            )
        except Exception as e:
            # 获取主机状态信息失败，跳过填充步骤
            logger.error(f"fill_agent_state_info_to_hosts error: {e}")
            return

        for host_info in host_infos:
            try:
                bk_host_id: int = host_info["bk_host_id"]
                host_info["status"] = host_id__agent_state_info[bk_host_id]["status_display"]
                host_info["version"] = host_id__agent_state_info[bk_host_id]["version"]
            except KeyError:
                pass
