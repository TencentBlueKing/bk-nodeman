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

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from apps.core.concurrent import controller
from apps.node_man import constants as node_man_constants
from apps.utils import concurrent
from apps.utils.batch_request import batch_request
from common.api import CCApi

from .. import constants, exceptions, types

logger = logging.getLogger("app")


class ResourceQueryHelper:
    @staticmethod
    def fetch_biz_list(bk_biz_ids: typing.Optional[typing.List[int]] = None) -> typing.List[typing.Dict]:
        """
        查询业务列表
        :param bk_biz_ids: 业务 ID 列表
        :return: 列表 ，包含 业务ID、名字、业务运维
        """
        search_business_params = {
            "not_request": True,
            "fields": ["bk_biz_id", "bk_biz_name", "bk_biz_maintainer"],
        }
        biz_infos: typing.List[typing.Dict] = CCApi.search_business(search_business_params)["info"]
        biz_infos.append(
            {"bk_biz_id": settings.BK_CMDB_RESOURCE_POOL_BIZ_ID, "bk_biz_name": _("资源池"), "bk_biz_maintainer": "admin"}
        )
        if not bk_biz_ids:
            return biz_infos
        # 转为 set，避免 n^2 查找
        bk_biz_ids: typing.Set[int] = set(bk_biz_ids)
        return [biz_info for biz_info in biz_infos if biz_info["bk_biz_id"] in bk_biz_ids]

    @staticmethod
    def get_topo_tree(bk_biz_id: int) -> types.TreeNode:

        try:
            topo_tree: types.TreeNode = CCApi.search_biz_inst_topo({"bk_biz_id": bk_biz_id, "not_request": True})[0]
        except IndexError:
            logger.error(f"topo not exists, bk_biz_id -> {bk_biz_id}")
            raise exceptions.TopoNotExistsError({"bk_biz_id": bk_biz_id})

        internal_set_info: typing.Dict = CCApi.get_biz_internal_module({"bk_biz_id": bk_biz_id, "not_request": True})
        internal_topo: typing.Dict = {
            "bk_obj_name": constants.ObjectType.get_member_value__alias_map().get(constants.ObjectType.SET.value, ""),
            "bk_obj_id": constants.ObjectType.SET.value,
            "bk_inst_id": internal_set_info["bk_set_id"],
            "bk_inst_name": internal_set_info["bk_set_name"],
            "child": [],
        }

        for internal_module in internal_set_info.get("module") or []:
            internal_topo["child"].append(
                {
                    "bk_obj_name": constants.ObjectType.get_member_value__alias_map().get(
                        constants.ObjectType.MODULE.value, ""
                    ),
                    "bk_obj_id": constants.ObjectType.MODULE.value,
                    "bk_inst_id": internal_module["bk_module_id"],
                    "bk_inst_name": internal_module["bk_module_name"],
                    "child": [],
                }
            )

        # 补充空闲机拓扑
        topo_tree["child"] = [internal_topo] + topo_tree.get("child") or []
        return topo_tree

    @staticmethod
    def fetch_host_topo_relations(bk_biz_id: int) -> typing.List[typing.Dict]:
        host_topo_relations: typing.List[typing.Dict] = batch_request(
            func=CCApi.find_host_topo_relation,
            params={"bk_biz_id": bk_biz_id, "no_request": True},
            get_data=lambda x: x["data"],
        )
        return host_topo_relations

    @staticmethod
    @controller.ConcurrentController(
        data_list_name="filter_inst_ids",
        batch_call_func=concurrent.batch_call,
        extend_result=True,
        get_config_dict_func=lambda: {"limit": 200},
    )
    def fetch_biz_hosts(
        bk_biz_id: int,
        fields: typing.List[str] = None,
        filter_obj_id: typing.Optional[str] = None,
        filter_inst_ids: typing.Optional[typing.List[int]] = None,
        host_property_filter: typing.Optional[typing.Dict] = None,
    ) -> typing.List[types.HostInfo]:
        query_params: typing.Dict[str, typing.Union[int, typing.Dict, typing.List[int]]] = {
            "bk_biz_id": bk_biz_id,
            "fields": fields or node_man_constants.CC_HOST_FIELDS,
            "not_request": True,
        }
        if filter_inst_ids:
            query_params[f"bk_{filter_obj_id}_ids"] = filter_inst_ids
        if host_property_filter:
            query_params["host_property_filter"] = host_property_filter
        return batch_request(func=CCApi.list_biz_hosts, params=query_params)
