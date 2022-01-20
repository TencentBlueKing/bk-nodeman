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
from copy import deepcopy
from typing import Any, Dict

from apps.node_man import models, tools
from apps.node_man.constants import DEFAULT_CLOUD_NAME, IamActionType
from apps.node_man.handlers.cmdb import CmdbHandler
from apps.node_man.handlers.host import HostHandler


class HostV2Handler:
    @staticmethod
    def list(
        params: dict,
        only_queryset: bool = False,
        with_agent_status_counter: bool = False,
        view_action=IamActionType.strategy_create,
        op_action=IamActionType.strategy_create,
        return_all_node_type: bool = False,
    ):
        """
        查询主机
        :param return_all_node_type: 是否返回所有节点类型
        :param params: 仅校验后的查询条件
        :param only_queryset: 仅返回queryset
        :param with_agent_status_counter:
        :param view_action: 查看权限
        :param op_action: 操作权限
        :return: 主机列表
        """
        if params.get("action"):
            view_action = params["action"]
            op_action = params["action"]

        # 用户有权限的业务
        user_biz = CmdbHandler().biz_id_name({"action": view_action})

        # 用户主机操作权限
        operate_bizs = CmdbHandler().biz_id_name({"action": op_action})

        # TODO: HostHandler实例化与否不影响功能，后续可优化
        host_tools = HostHandler()

        if params["pagesize"] != -1:
            begin = (params["page"] - 1) * params["pagesize"]
            end = (params["page"]) * params["pagesize"]
        else:
            begin = None
            end = None
            # 跨页全选模式，仅返回用户有权限操作的主机
            user_biz = operate_bizs

        scope: Dict[str, Any] = params.get("scope")
        if scope:
            # scopes 与 nodes 同传时，结果需要落在scope中
            bk_host_ids = tools.HostV2Tools.list_scope_host_ids(scope)

            if params.get("bk_host_id"):
                params["bk_host_id"] = list(set(params["bk_host_id"]) & set(bk_host_ids))
            else:
                params["bk_host_id"] = bk_host_ids

        params["conditions"] = params.get("conditions", [])
        params["conditions"].extend(tools.HostV2Tools.parse_nodes2conditions(params.get("nodes", []), operate_bizs))

        # 生成sql查询主机
        hosts_sql = host_tools.multiple_cond_sql(params, user_biz, return_all_node_type=return_all_node_type).exclude(
            bk_host_id__in=params.get("exclude_hosts", [])
        )

        if params.get("agent_status_count"):
            # 仅统计Agent状态
            return tools.HostV2Tools.get_agent_status_counter(hosts_sql)

        if only_queryset:
            return hosts_sql

        fetch_fields = ["bk_cloud_id", "bk_biz_id", "bk_host_id", "os_type", "inner_ip", "status", "cpu_arch"]

        hosts = list(hosts_sql.values(*fetch_fields)[begin:end])

        bk_cloud_ids = [host["bk_cloud_id"] for host in hosts]

        # 获得云区域名称
        cloud_name = dict(
            models.Cloud.objects.filter(bk_cloud_id__in=bk_cloud_ids).values_list("bk_cloud_id", "bk_cloud_name")
        )
        cloud_name[0] = DEFAULT_CLOUD_NAME

        # 填充云区域及业务名称
        for host in hosts:
            host["bk_cloud_name"] = cloud_name.get(host["bk_cloud_id"])
            host["bk_biz_name"] = user_biz.get(host["bk_biz_id"], "")

        host_page = {"total": hosts_sql.count(), "list": hosts}

        if with_agent_status_counter:
            host_page["agent_status_count"] = tools.HostV2Tools.get_agent_status_counter(hosts_sql)

        return host_page

    @staticmethod
    def agent_status(nodes: list, action: str) -> list:
        """
        统计拓扑节点列表中每个节点的agent状态
        :param nodes:
        :param action:
        :return:
        [
            {
                "bk_biz_id": 1,
                "bk_inst_id": 10,
                "bk_obj_id": "module",
                "agent_status_count": {
                    "total": 22,        // 总数
                    "RUNNING": 10,      // 唯一表示正常的状态，异常Agent数 = result["total"] - result["RUNNING"]
                    "TERMINATED": 2,
                    "NOT_INSTALLED": 4,
                }
            },
        ]
        """
        # TODO 循环里sql查询并且是联表查，性能堪忧
        nodes = deepcopy(nodes)
        CmdbHandler().check_biz_permission([node["bk_biz_id"] for node in nodes], action)
        result = []
        for node in nodes:
            node["agent_status_count"] = HostV2Handler.list(
                params={"agent_status_count": True, "bk_biz_id": [node["bk_biz_id"]], "nodes": [node], "pagesize": -1},
            )
            result.append(node)
        return result
