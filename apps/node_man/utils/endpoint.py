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

from apps.utils.basic import filter_values
from apps.utils.md5 import _count_md5


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
        endpoints: typing.Dict[str, typing.List[typing.Dict[str, typing.Union[str, int]]]],
    ):
        self.inner_endpoints: typing.List[Endpoint] = []
        self.outer_endpoints: typing.List[Endpoint] = []
        # shortcut
        self.outer_hosts: typing.List[str] = []
        self.inner_hosts: typing.List[str] = []
        from apps.node_man.models import AccessPoint

        if isinstance(endpoints, dict):
            raise ValueError("endpoints must be dict")

        for endpoint_type, endpoint_info_list in endpoints.items():
            for endpoint_info in endpoint_info_list:
                if endpoint_type == AccessPoint.ServersType.INNER_IPS:
                    endpoint: Endpoint = Endpoint(
                        v4=endpoint_info.get("inner_ip"),
                        v6=endpoint_info.get("inner_ipv6"),
                        host_id=endpoint_info.get("bk_host_id"),
                    )
                    self.inner_endpoints.append(endpoint)
                    if endpoint.host_str:
                        self.inner_hosts.append(endpoint.host_str)
                elif endpoint_type == AccessPoint.ServersType.OUTER_IPS:
                    endpoint: Endpoint = Endpoint(
                        v4=endpoint_info.get("outer_ip"),
                        v6=endpoint_info.get("outer_ipv6"),
                        host_id=endpoint_info.get("bk_host_id"),
                    )
                    self.outer_endpoints.append(endpoint)
                    if endpoint.host_str:
                        self.outer_hosts.append(endpoint.host_str)


class EndPointTransform(object):
    # legacy_endpoint: [{ "inner_ip": "10.0.6.44", "outer_ip": "10.0.6.44"}, {"inner_ip": "xxx", "outer_ip": "xxx"}]
    # endpoint: {
    #    "inner_ips": [{"ip": "",  "bk_host_id": x],
    #   "outer_ips": [{"ip": "",  "bk_host_id": x]
    # }

    INNER_IPS = "inner_ips"
    OUTER_IPS = "outer_ips"

    def transform(
        self, legacy_endpoints: typing.List[typing.Dict[str, typing.Any]]
    ) -> typing.Dict[str, typing.List[typing.Dict[str, typing.Union[str, int]]]]:
        endpoints = defaultdict(list)
        if not isinstance(legacy_endpoints, list):
            raise ValueError("legacy_endpoints must be list")
        for legacy_endpoint in legacy_endpoints:
            endpoints[self.INNER_IPS].append(
                {
                    "inner_ip": legacy_endpoint.get("inner_ip"),
                    "bk_host_id": legacy_endpoint.get("bk_host_id"),
                    "inner_ipv6": legacy_endpoint.get("inner_ipv6"),
                }
            )
            endpoints[self.OUTER_IPS].append(
                {
                    "outer_ip": legacy_endpoint.get("outer_ip"),
                    "bk_host_id": legacy_endpoint.get("bk_host_id"),
                    "outer_ipv6": legacy_endpoint.get("outer_ipv6"),
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
        return dict(unique_endpoints)

    def transform_endpoint_to_leagcy(
        self,
        endpoints: typing.Dict[str, typing.List[typing.Dict[str, typing.Union[str, int]]]],
    ) -> typing.List[typing.Dict[str, typing.Any]]:
        from apps.node_man.models import AccessPoint

        legacy_endpoints = []
        if not isinstance(endpoints, dict):
            raise ValueError("endpoints must be dict")

        # endpoints 的 key 必须为这两个值，无序的 ["inner_ips", "outer_ips"]:
        for endpoint_type in endpoints:
            if endpoint_type not in [self.INNER_IPS, self.OUTER_IPS]:
                raise ValueError(
                    f"endpoints key must be in {AccessPoint.ServersType.INNER_IPS},"
                    f"or {AccessPoint.ServersType.OUTER_IPS}"
                )
            if not isinstance(endpoints[endpoint_type], list):
                raise ValueError("endpoints value must be list")

        legacy_endpoints = [
            {
                "inner_ip": inner_info.get("inner_ip"),
                "outer_ip": outer_info.get("outer_ip"),
                "inner_ipv6": inner_info.get("inner_ipv6"),
                "outer_ipv6": outer_info.get("outer_ipv6"),
                "bk_host_id": inner_info.get("bk_host_id"),
            }
            for inner_info in endpoints.get(self.INNER_IPS, [])
            for outer_info in endpoints.get(self.OUTER_IPS, [])
        ]

        # 把 legacy_endpoints 通过字典的 md5 去重
        seen = set()
        unique_endpoints = []
        for endpoint in legacy_endpoints:
            hash_value = _count_md5(json.dumps(endpoint))
            if hash_value not in seen:
                unique_endpoints.append(filter_values(endpoint))
                seen.add(hash_value)

        return unique_endpoints
