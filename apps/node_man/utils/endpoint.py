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
from dataclasses import dataclass, field


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
        inner_server_infos: typing.List[typing.Dict[str, typing.Any]],
        outer_server_infos: typing.List[typing.Dict[str, typing.Any]],
    ):
        self.inner_endpoints: typing.List[Endpoint] = []
        self.outer_endpoints: typing.List[Endpoint] = []
        # shortcut
        self.outer_hosts: typing.List[str] = []
        self.inner_hosts: typing.List[str] = []

        for inner_server_info in inner_server_infos:
            endpoint: Endpoint = Endpoint(
                v4=inner_server_info.get("inner_ip"),
                v6=inner_server_info.get("inner_ipv6"),
                host_id=inner_server_info.get("host_id"),
            )
            self.inner_endpoints.append(endpoint)
            if endpoint.host_str:
                self.inner_hosts.append(endpoint.host_str)

        for outer_server_info in outer_server_infos:
            endpoint: Endpoint = Endpoint(
                v4=outer_server_info.get("outer_ip"),
                v6=outer_server_info.get("outer_ipv6"),
                host_id=outer_server_info.get("host_id"),
            )
            self.outer_endpoints.append(endpoint)
            if endpoint.host_str:
                self.outer_hosts.append(endpoint.host_str)
