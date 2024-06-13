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

from django_mysql.models import QuerySet

from apps.core.ipchooser.tools.host_tool import HostTool
from apps.node_man.models import GlobalSettings

from .. import constants, types
from ..tools import base
from .base import BaseHandler


class HostHandler:
    @staticmethod
    def details_base(
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
        host_queryset: QuerySet = base.HostQuerySqlHelper.multiple_cond_sql(
            params={}, biz_scope=[scope["bk_biz_id"] for scope in scope_list], return_all_node_type=True
        )
        host_queryset = base.HostQueryHelper.or_query_hosts(host_queryset, or_conditions=or_conditions)
        if limit_host_ids is not None:
            host_queryset = host_queryset.filter(bk_host_id__in=limit_host_ids)
        # 获取主机信息
        host_fields: typing.List[str] = constants.CommonEnum.DEFAULT_HOST_FIELDS.value
        untreated_host_infos: typing.List[types.HostInfo] = list(host_queryset.values(*host_fields))

        if show_agent_realtime_state:
            enable = GlobalSettings.get_config(
                key=GlobalSettings.KeyEnum.IP_CHOOSER_ENABLE_SHOW_REALTIME_AGENT_STATE.value, default=False
            )
            if not enable:
                return BaseHandler.format_hosts(untreated_host_infos)
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
