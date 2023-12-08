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

import json
import typing
from collections import defaultdict
from dataclasses import dataclass, field

from apps.utils.basic import filter_values, is_v4, is_v6
from apps.utils.md5 import _count_md5
from common.log import logger


@dataclass
class Endpoint:
    v4: typing.Optional[str]
    v6: typing.Optional[str]
    host_id: int = None
    host_str: str = field(init=False)

    def __post_init__(self):
        self.host_str = self.v4 or self.v6


class EndpointInfo:
    def __init__(
        self,
        inner_ip_infos: typing.List[typing.Dict[str, typing.Union[str, int]]],
        outer_ip_infos: typing.List[typing.Dict[str, typing.Union[str, int]]],
    ):
        self.inner_endpoints: typing.List[Endpoint] = []
        self.outer_endpoints: typing.List[Endpoint] = []
        # shortcut
        self.outer_hosts: typing.List[str] = []
        self.inner_hosts: typing.List[str] = []

        def create_endpoint(ip_info: typing.Dict[str, typing.Union[str, int]]) -> Endpoint:
            ip = ip_info.get("ip")
            host_id = ip_info.get("bk_host_id")
            if is_v4(ip):
                return Endpoint(v4=ip, v6=None, host_id=host_id)
            else:
                return Endpoint(v6=ip, v4=None, host_id=host_id)

        self.inner_endpoints = [create_endpoint(ip_info) for ip_info in inner_ip_infos]
        self.outer_endpoints = [create_endpoint(ip_info) for ip_info in outer_ip_infos]

        self.inner_hosts = [endpoint.host_str for endpoint in self.inner_endpoints if endpoint.host_str]
        self.outer_hosts = [endpoint.host_str for endpoint in self.outer_endpoints if endpoint.host_str]


class EndPointTransform(object):
    # legacy_endpoint: [{ "inner_ip": "10.0.6.44", "outer_ip": "10.0.6.44"}, {"inner_ip": "xxx", "outer_ip": "xxx"}]
    # endpoint: {
    #    "inner_ip_infos": [{"ip": "",  "bk_host_id": x],
    #   "outer_ip_infos": [{"ip": "",  "bk_host_id": x]
    # }

    def transform(
        self, legacy_endpoints: typing.List[typing.Dict[str, typing.Any]]
    ) -> typing.Dict[str, typing.List[typing.Dict[str, typing.Union[str, int]]]]:
        endpoints = defaultdict(list)
        if not isinstance(legacy_endpoints, list):
            raise ValueError("legacy_endpoints must be list")
        for legacy_endpoint in legacy_endpoints:
            inner_ip = legacy_endpoint.get("inner_ip") or legacy_endpoint.get("inner_ipv6")
            outer_ip = legacy_endpoint.get("outer_ip") or legacy_endpoint.get("outer_ipv6")
            bk_host_id = legacy_endpoint.get("bk_host_id")
            if inner_ip:
                endpoints["inner_ip_infos"].append(
                    {
                        "bk_host_id": bk_host_id,
                        "ip": legacy_endpoint.get("inner_ip") or legacy_endpoint.get("inner_ipv6"),
                    }
                )
            if outer_ip:
                endpoints["outer_ip_infos"].append(
                    {
                        "ip": outer_ip,
                        "bk_host_id": bk_host_id,
                    }
                )
        # 把 endpoints 的 values 包括的字典中的空字段去掉 并且去重
        unique_endpoints = defaultdict(list)
        seen = set()
        for endpoint_type in endpoints:
            for endpoint in endpoints[endpoint_type]:
                hash_value = _count_md5(json.dumps(endpoint))
                if hash_value not in seen:
                    unique_endpoints[endpoint_type].append(filter_values(endpoint))
                    seen.add(hash_value)
        logger.info(f"unique_endpoints: {unique_endpoints}, endpoints: {endpoints}")
        return dict(unique_endpoints)

    def transform_endpoint_to_legacy(
        self,
        endpoints: typing.Dict[str, typing.List[typing.Dict[str, typing.Union[str, int]]]],
    ) -> typing.List[typing.Dict[str, typing.Any]]:
        legacy_endpoints = []
        if not isinstance(endpoints, dict):
            raise ValueError("endpoints must be dict")

        # endpoints 的 key 必须为这两个值，无序的 ["inner_ip_infos", "outer_ip_infos"]:
        legacy_endpoints = []
        for endpoint_type in endpoints:
            if endpoint_type not in ["inner_ip_infos", "outer_ip_infos"]:
                raise ValueError("endpoints key must be in inner_ip_infos or outer_ip_infos")
            if not isinstance(endpoints[endpoint_type], list):
                raise ValueError("endpoints value must be list")

        # 这里保留之前的为空的数据默认字段 inner_ip & outer_ip 的值为空字符串, 其他字段过滤掉
        legacy_endpoints = [
            {
                "inner_ip": inner_info.get("ip") if is_v4(inner_info.get("ip")) else "",
                "outer_ip": outer_info.get("ip") if is_v4(outer_info.get("ip")) else "",
                "inner_ipv6": inner_info.get("ip") if is_v6(inner_info.get("ip")) else None,
                "outer_ipv6": outer_info.get("ip") if is_v6(outer_info.get("ip")) else None,
                "bk_host_id": inner_info.get("bk_host_id") or outer_info.get("bk_host_id"),
            }
            for inner_info in endpoints.get("inner_ip_infos", [])
            for outer_info in endpoints.get("outer_ip_infos", [])
        ]

        # 把 legacy_endpoints 通过字典的 md5 去重
        seen = set()
        unique_endpoints = []
        for endpoint in legacy_endpoints:
            hash_value = _count_md5(json.dumps(endpoint))
            if hash_value not in seen:
                unique_endpoints.append(filter_values(endpoint))
                seen.add(hash_value)
        logger.info(f"unique_endpoints: {unique_endpoints}, legacy_endpoints: {legacy_endpoints}")

        return unique_endpoints
