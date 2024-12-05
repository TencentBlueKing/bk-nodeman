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
from collections import defaultdict

from django_mysql.models import QuerySet

from apps.core.concurrent import controller
from apps.core.ipchooser.tools.host_tool import HostTool
from apps.node_man.constants import QUERY_CMDB_LIMIT
from apps.node_man.models import GlobalSettings
from apps.node_man.periodic_tasks.sync_cmdb_host import bulk_differential_sync_biz_hosts
from apps.utils import batch_request, concurrent
from common.api import CCApi
from common.log import logger

from .. import constants, types
from ..tools import base
from .base import BaseHandler


class HostHandler:
    @classmethod
    def query_host_by_cloud_ip(cls, cloud_inner_ip: typing.List[str]) -> typing.List[int]:
        """
        查询主机host_id用于查询主机的业务信息
        """
        bk_cloud_ids: typing.Set[int] = set()
        bk_host_innerip: typing.Set[str] = set()
        for cloud_ip in cloud_inner_ip:
            bk_cloud_ids.add(int(cloud_ip.split(constants.CommonEnum.SEP.value)[0]))
            bk_host_innerip.add(cloud_ip.split(constants.CommonEnum.SEP.value)[1])

        query_hosts_params: typing.Dict[str, typing.Any] = {
            "fields": ["bk_host_id"],
            "host_property_filter": {
                "condition": "AND",
                "rules": [
                    {"field": "bk_host_innerip", "operator": "in", "value": list(bk_host_innerip)},
                    {"field": "bk_cloud_id", "operator": "in", "value": list(bk_cloud_ids)},
                ],
            },
            "no_request": True,
        }

        cmdb_host_infos: typing.List[typing.Dict[str, typing.Any]] = batch_request.batch_request(
            func=CCApi.list_hosts_without_biz, params=query_hosts_params
        )

        logger.info(f"need_differential_sync_cloud_ip count: {len(cmdb_host_infos)} -> {cmdb_host_infos}")

        return [host["bk_host_id"] for host in cmdb_host_infos]

    @controller.ConcurrentController(
        data_list_name="bk_host_ids",
        batch_call_func=concurrent.batch_call,
        get_config_dict_func=lambda: {"limit": QUERY_CMDB_LIMIT},
    )
    @classmethod
    def find_host_biz_relations(
        cls, bk_host_ids: typing.List[int]
    ) -> typing.List[typing.Optional[typing.Dict[str, typing.Any]]]:
        """
        查询主机业务关系信息
        :param bk_host_ids: 主机列表
        :return: 主机业务关系列表
        """
        # 接口对于空数组的处理是报错，这里需要提前处理返回
        if not bk_host_ids:
            return []

        return CCApi.find_host_biz_relations({"bk_host_id": bk_host_ids})

    @classmethod
    def fetch_need_differential_sync_bk_host_ids(
        cls, untreated_host_infos, or_conditions
    ) -> typing.List[typing.Optional[int]]:
        """
        获取所有需要差量同步的主机id
        """
        exist_hosts: typing.Dict[str, typing.Set] = {
            "bk_host_id": set(),
            "cloud_inner_ip": set(),
        }
        for host in untreated_host_infos:
            exist_hosts["bk_host_id"].add(host["bk_host_id"])
            exist_hosts["cloud_inner_ip"].add(
                f"{host['bk_cloud_id']}{constants.CommonEnum.SEP.value}{host['inner_ip']}"
            )
        or_conditions_map: typing.Dict = {item["key"]: item["val"] for item in or_conditions}

        need_differential_sync_bk_host_ids: typing.List[int] = list(
            or_conditions_map.get("bk_host_id", set()) - exist_hosts["bk_host_id"]
        )
        need_differential_sync_cloud_ip: typing.List[str] = list(
            or_conditions_map.get("cloud_inner_ip", set()) - exist_hosts["cloud_inner_ip"]
        )
        if need_differential_sync_cloud_ip:
            # 如果是IP形式需要查询出主机ID
            need_differential_sync_cloud_ip_host_ids = cls.query_host_by_cloud_ip(need_differential_sync_cloud_ip)
            # 所有需求差量同步的主机ID
            need_differential_sync_bk_host_ids += need_differential_sync_cloud_ip_host_ids

        logger.info(
            f"need_differential_sync_bk_host_ids "
            f"count:{len(need_differential_sync_bk_host_ids)} -> {need_differential_sync_bk_host_ids}"
        )

        return need_differential_sync_bk_host_ids

    @classmethod
    def bulk_differential_sync_hosts(cls, need_differential_sync_bk_host_ids):
        """
        差量同步所有需要同步的主机
        """
        # 查询主机id所属业务
        host_biz_relations: typing.List[typing.Optional[typing.Dict[str, typing.Any]]] = cls.find_host_biz_relations(
            bk_host_ids=need_differential_sync_bk_host_ids
        )

        expected_bk_host_ids_gby_bk_biz_id: typing.Dict[int, typing.List[int]] = defaultdict(list)
        for host_biz_realtion in host_biz_relations:
            expected_bk_host_ids_gby_bk_biz_id[host_biz_realtion["bk_biz_id"]].append(host_biz_realtion["bk_host_id"])

        bulk_differential_sync_biz_hosts(expected_bk_host_ids_gby_bk_biz_id)

    @classmethod
    def fetch_untreated_host_infos(
        cls, limit_host_ids, or_conditions, scope_list
    ) -> typing.List[typing.Dict[str, typing.Any]]:
        host_queryset: QuerySet = base.HostQuerySqlHelper.multiple_cond_sql(
            params={}, biz_scope=[scope["bk_biz_id"] for scope in scope_list], return_all_node_type=True
        )
        host_queryset = base.HostQueryHelper.or_query_hosts(host_queryset, or_conditions=or_conditions)
        if limit_host_ids is not None:
            host_queryset = host_queryset.filter(bk_host_id__in=limit_host_ids)
        # 获取主机信息
        host_fields: typing.List[str] = constants.CommonEnum.DEFAULT_HOST_FIELDS.value
        untreated_host_infos: typing.List[types.HostInfo] = list(host_queryset.values(*host_fields))
        return untreated_host_infos

    @classmethod
    def details_base(
        cls,
        scope_list: types.ScopeList,
        or_conditions: typing.List[types.Condition],
        limit_host_ids: typing.Optional[typing.List[int]] = None,
        show_agent_realtime_state: bool = False,
    ) -> typing.List[types.FormatHostInfo]:
        """
        获取主机详情
        :param scope_list: 资源范围数组
        :param or_conditions: 逻辑或查询条件
        :param limit_host_ids: 限制检索的主机 ID 列表
        :param show_agent_realtime_state: 是否展示Agent实时状态
        :return:
        """
        untreated_host_infos: typing.List[typing.Dict[str, typing.Any]] = cls.fetch_untreated_host_infos(
            limit_host_ids, or_conditions, scope_list
        )

        need_differential_sync_bk_host_ids: typing.List[
            typing.Optional[int]
        ] = cls.fetch_need_differential_sync_bk_host_ids(untreated_host_infos, or_conditions)

        if need_differential_sync_bk_host_ids:
            # 差量同步主机
            cls.bulk_differential_sync_hosts(need_differential_sync_bk_host_ids)

            # 查询差量主机信息回填查询结果
            differential_host_infos: typing.List[typing.Dict[str, typing.Any]] = cls.fetch_untreated_host_infos(
                need_differential_sync_bk_host_ids, [], scope_list
            )
            untreated_host_infos += differential_host_infos

        bk_biz_ids: typing.List[int] = [scope["bk_biz_id"] for scope in scope_list]

        biz_whitelist: typing.List[int] = GlobalSettings.get_config(
            key=GlobalSettings.KeyEnum.IP_CHOOSER_BIZ_WHITELIST.value, default=[]
        )
        if any(
            [
                bk_biz_ids in biz_whitelist,
                set(bk_biz_ids) & set(biz_whitelist),
            ]
        ):
            HostTool.fill_agent_state_info_to_hosts(host_infos=untreated_host_infos)
            return BaseHandler.format_hosts(untreated_host_infos)

        if show_agent_realtime_state:
            enable: bool = GlobalSettings.get_config(
                key=GlobalSettings.KeyEnum.IP_CHOOSER_ENABLE_SHOW_REALTIME_AGENT_STATE.value, default=False
            )
            if enable:
                HostTool.fill_agent_state_info_to_hosts(host_infos=untreated_host_infos)

        return BaseHandler.format_hosts(untreated_host_infos)

    @classmethod
    def check(
        cls,
        scope_list: types.ScopeList,
        limit_host_ids: typing.Optional[typing.List[int]],
        ip_list: typing.List[str],
        ipv6_list: typing.List[str],
        key_list: typing.List[str],
    ) -> typing.List[types.FormatHostInfo]:
        """
        根据输入的`IP`/`IPv6`/`主机名`/`host_id`等关键字信息获取真实存在的机器信息。
        :param scope_list: 资源范围数组
        :param limit_host_ids: 限制检索的主机 ID 列表
        :param ip_list: IPv4 列表
        :param ipv6_list: IPv6 列表
        :param key_list: 关键字列表
        :return:
        """
        if not scope_list:
            return []
        inner_ip_set: typing.Set[str] = set()
        bk_host_id_set: typing.Set[int] = set()
        bk_host_name_set: typing.Set[str] = set()
        cloud_inner_ip_set: typing.Set[str] = set()
        cloud_inner_ipv6_set: typing.Set[str] = set()

        for ip_or_cloud_ip in ip_list:
            # 按分隔符切割，获取切割后长度
            block_num: int = len(ip_or_cloud_ip.split(constants.CommonEnum.SEP.value, 1))
            # 长度为 1 表示单 IP，否则认为是 cloud_id:ip
            if block_num == 1:
                inner_ip_set.add(ip_or_cloud_ip)
            else:
                if "[" and "]" in ip_or_cloud_ip:
                    ip_or_cloud_ip = ip_or_cloud_ip.replace("[", "").replace("]", "")
                cloud_inner_ip_set.add(ip_or_cloud_ip)
        for ipv6_or_cloud_ip in ipv6_list:
            block_num: int = len(ipv6_or_cloud_ip.split(constants.CommonEnum.SEP.value, 1))
            if block_num == 1:
                inner_ip_set.add(ipv6_or_cloud_ip)
            else:
                if "[" and "]" in ipv6_or_cloud_ip:
                    ipv6_or_cloud_ip = ipv6_or_cloud_ip.replace("[", "").replace("]", "")
                    cloud_inner_ipv6_set.add(ipv6_or_cloud_ip)
        for key in key_list:
            # 尝试将关键字解析为主机 ID
            try:
                bk_host_id_set.add(int(key))
            except ValueError:
                pass
            bk_host_name_set.add(key)

        # 构造逻辑或查询条件
        or_conditions: typing.List[types.Condition] = [
            {"key": "inner_ip", "val": inner_ip_set},
            {"key": "inner_ipv6", "val": set(ipv6_list)},
            {"key": "bk_host_id", "val": bk_host_id_set},
            {"key": "bk_host_name", "val": bk_host_name_set},
            {"key": "cloud_inner_ip", "val": cloud_inner_ip_set},
            {"key": "cloud_inner_ipv6", "val": cloud_inner_ipv6_set},
        ]
        return cls.details_base(scope_list, or_conditions, limit_host_ids=limit_host_ids)

    @classmethod
    def details(
        cls, scope_list: types.ScopeList, host_list: typing.List[types.FormatHostInfo], show_agent_realtime_state: bool
    ) -> typing.List[types.FormatHostInfo]:
        """
        根据主机关键信息获取机器详情信息
        :param scope_list: 资源范围数组
        :param host_list: 主机关键信息列表
        :param show_agent_realtime_state: 是否展示Agent实时状态
        :return:
        """
        bk_host_id_set: typing.Set[int] = set()
        cloud_inner_ip_set: typing.Set[str] = set()

        for host_info in host_list:
            # 优先取主机 ID 作为查询条件
            if "host_id" in host_info:
                bk_host_id_set.add(host_info["host_id"])
            else:
                cloud_inner_ip_set.add(f"{host_info['cloud_id']}{constants.CommonEnum.SEP.value}{host_info['ip']}")
        # 构造逻辑或查询条件
        or_conditions: typing.List[types.Condition] = [
            {"key": "bk_host_id", "val": bk_host_id_set},
            {"key": "cloud_inner_ip", "val": cloud_inner_ip_set},
        ]
        return cls.details_base(scope_list, or_conditions, show_agent_realtime_state=show_agent_realtime_state)
