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

import ipaddress
import socket
from urllib.parse import urlparse


def is_safe_url(url_list: list, blocked_ports: list = [], blocked_networks: list = []) -> bool:

    # 解析并验证网段列表
    blocked_ipsets = []
    for network in blocked_networks:
        try:
            blocked_ipsets.append(ipaddress.ip_network(network, strict=False))
        except ValueError:
            raise ValueError(f"Invalid network CIDR: {network}")

    try:
        for url in url_list:
            if not url:
                continue
            parsed = urlparse(url)

            # 限定协议
            if parsed.scheme not in ["http", "https"]:
                return False, f"Invalid scheme: {parsed.scheme}"

            # 限定域名
            hostname = parsed.hostname
            if not hostname:
                return False, "Missing hostname"

            # 解析真实 IP
            ip = socket.gethostbyname(hostname)
            ip_obj = ipaddress.ip_address(ip)

            # 网段限制检查
            for network in blocked_ipsets:
                if ip_obj in network:
                    return False, f"Blocked network: {ip} in {network}"

            # 回环、链路本地地址
            if ip_obj.is_loopback:
                return False, "Loopback address detected"
            if ip_obj.is_link_local:
                return False, "Link local address detected"

            # 端口限制
            if parsed.port is not None:
                if parsed.port in blocked_ports:
                    return False, f"Blocked port: {parsed.port}"
        else:
            return True, "All URLs are safe"
    except Exception:
        return False, "URL validation failed"
