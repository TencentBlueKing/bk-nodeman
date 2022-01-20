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

from apps.backend.subscription.commons import get_host_by_inst
from apps.component.esbclient import client_v2
from apps.node_man import constants, models
from apps.utils.batch_request import batch_request

"""
此文件的函数不应被其他任何函数共用，仅用于处理渲染逻辑
"""
logger = logging.getLogger("app")

client_v2.backend = True


def get_host_detail_by_template(bk_obj_id, template_info_list: list, bk_biz_id: int = None):
    """
    根据集群模板ID/服务模板ID获得主机的详细信息
    :param bk_obj_id: 模板类型
    :param template_info_list: 模板信息列表
    :param bk_biz_id: 业务ID
    :return: 主机列表信息
    """
    if not template_info_list:
        return []

    fields = constants.FIND_HOST_BY_TEMPLATE_FIELD

    if bk_obj_id == models.Subscription.NodeType.SERVICE_TEMPLATE:
        # 服务模板
        call_func = client_v2.cc.find_host_by_service_template
        template_ids = [info["bk_inst_id"] for info in template_info_list]
        host_info_result = batch_request(
            call_func, dict(bk_service_template_ids=template_ids, bk_biz_id=bk_biz_id, fields=fields)
        )
    else:
        # 集群模板
        call_func = client_v2.cc.find_host_by_set_template
        template_ids = [info["bk_inst_id"] for info in template_info_list]
        host_info_result = batch_request(
            call_func, dict(bk_set_template_ids=template_ids, bk_biz_id=bk_biz_id, fields=fields)
        )

    return host_info_result


def get_hosts_by_node(config_hosts):
    """
    解析拓扑或模板，获得其内的所有主机
    :param config_hosts: list
        // HOST-TOPO/TEMPLATE
        [{'bk_biz_id': 2, 'bk_inst_id': 2, 'bk_obj_id': 'set'}]
        // HOST-INSTANCE
        [{'ip': '127.0.0.1'}, {'ip': '127.0.0.1'}, {'ip': '127.0.0.1'}]
    :return: [{'ip': '127.0.0.1'}, {'ip': '127.0.0.1'}, {'ip': '127.0.0.1'}]
    """
    instances = []
    if len(config_hosts) and config_hosts[0].get("ip"):
        # 针对静态类型，传过来的都是IP，直接返回即可
        instances = config_hosts
    else:
        bk_biz_id = config_hosts[0]["bk_biz_id"]
        bk_obj_id = config_hosts[0]["bk_obj_id"]
        if bk_obj_id in [models.Subscription.NodeType.SERVICE_TEMPLATE, models.Subscription.NodeType.SET_TEMPLATE]:
            # 根据 模板 类型节点来计算IP
            instances.extend(
                [
                    {"ip": inst["bk_host_innerip"]}
                    for inst in get_host_detail_by_template(bk_obj_id, config_hosts, bk_biz_id=bk_biz_id)
                ]
            )
        else:
            # 针对 TOPO 类型节点计算IP
            instances.extend([{"ip": inst["bk_host_innerip"]} for inst in get_host_by_inst(bk_biz_id, config_hosts)])
    return instances
