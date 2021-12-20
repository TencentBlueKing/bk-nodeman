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
import logging

from django.core.cache import cache

from apps.component.esbclient import client_v2
from apps.exceptions import BizNotExistError
from apps.node_man import constants
from apps.utils.batch_request import batch_request

logger = logging.getLogger("app")

client_v2.backend = True


def get_host_object_attribute(bk_biz_id):
    biz_property_cache_key = f"{bk_biz_id}{constants.BIZ_CUSTOM_PROPERTY_CACHE_SUFFIX}"
    biz_property = cache.get(biz_property_cache_key)
    if biz_property is not None:
        return biz_property

    kwargs = {"bk_obj_id": "host", "bk_biz_id": bk_biz_id}
    data = client_v2.cc.search_object_attribute(kwargs) or []
    custom_fields = [_property["bk_property_id"] for _property in data if _property["bk_biz_id"] != 0]
    cache.set(biz_property_cache_key, custom_fields, 600)
    return custom_fields


def list_biz_hosts(bk_biz_id, condition, func, split_params=False):
    biz_custom_property = []
    kwargs = {
        "fields": constants.LIST_BIZ_HOSTS_KWARGS,
    }
    if bk_biz_id:
        biz_custom_property = get_host_object_attribute(bk_biz_id)
        kwargs["bk_biz_id"] = bk_biz_id

    kwargs["fields"] += list(set(biz_custom_property))
    kwargs["fields"] = list(set(kwargs["fields"]))
    kwargs.update(condition)

    hosts = batch_request(getattr(client_v2.cc, func), kwargs, split_params=split_params)
    # 排除掉CMDB中内网IP为空的主机
    cleaned_hosts = [host for host in hosts if host.get("bk_host_innerip")]
    return cleaned_hosts


def get_host_by_inst(bk_biz_id, inst_list):
    """
    根据拓扑节点查询主机
    :param inst_list: 实例列表
    :param bk_biz_id: 业务ID
    :return: dict 主机信息
    """
    if not bk_biz_id:
        raise BizNotExistError()

    hosts = []
    bk_module_ids = []
    bk_set_ids = []
    bk_biz_ids = []

    # 获取主线模型的业务拓扑信息
    topo_data_list = client_v2.cc.get_mainline_object_topo()
    bk_obj_id_list = [topo_data["bk_obj_id"] for topo_data in topo_data_list]

    for inst in inst_list:
        # 处理各种类型的节点
        if inst["bk_obj_id"] == "biz":
            bk_biz_ids.append(bk_biz_id)
        elif inst["bk_obj_id"] == "set":
            bk_set_ids.append(inst["bk_inst_id"])
        elif inst["bk_obj_id"] == "module":
            bk_module_ids.append(inst["bk_inst_id"])
        elif inst["bk_obj_id"] in bk_obj_id_list:
            # 自定义层级
            topo_cond = {"bk_obj_id": inst["bk_obj_id"], "bk_inst_id": inst["bk_inst_id"]}
            hosts.extend(list_biz_hosts(bk_biz_id, topo_cond, "find_host_by_topo"))

    if bk_biz_ids:
        # 业务查询
        for bk_biz_id in bk_biz_ids:
            hosts.extend(list_biz_hosts(bk_biz_id, {}, "list_biz_hosts"))
    if bk_set_ids:
        # 集群查询
        hosts.extend(
            list_biz_hosts(
                bk_biz_id,
                {"set_cond": [{"field": "bk_set_id", "operator": "$in", "value": bk_set_ids}]},
                "list_biz_hosts",
            )
        )
    if bk_module_ids:
        # 模块查询 这里CMDB限制了bk_module_ids不能超过500, 需要拆分参数 split_params=True
        hosts.extend(list_biz_hosts(bk_biz_id, {"bk_module_ids": bk_module_ids}, "list_biz_hosts", split_params=True))

    return hosts
