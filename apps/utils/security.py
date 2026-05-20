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
from typing import Iterable, Optional, Sequence, Tuple
from urllib.parse import urlparse, urlunparse
from urllib.request import HTTPRedirectHandler, build_opener

import requests


class UnsafeURLError(ValueError):
    pass


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_PRIVATE_HOSTS = {"localhost", "localhost.localdomain"}
SAFE_URL_BLOCKED_NETWORKS_KEY = "SAFE_URL_BLOCKED_NETWORKS"


def _get_global_blocked_networks() -> Sequence[str]:
    try:
        from apps.node_man.models import GlobalSettings

        return GlobalSettings.get_config(
            key=getattr(GlobalSettings.KeyEnum, SAFE_URL_BLOCKED_NETWORKS_KEY).value,
            default=[],
        ) or []
    except Exception:
        return []


def _normalize_allowed_hosts(allowed_hosts: Optional[Iterable[str]]) -> set:
    return {host.strip().lower().rstrip(".") for host in allowed_hosts or [] if host and host.strip()}


def _compile_blocked_networks(blocked_networks: Optional[Iterable[str]] = None) -> Sequence[ipaddress._BaseNetwork]:
    networks = list(_get_global_blocked_networks())
    networks.extend(blocked_networks or [])
    return [ipaddress.ip_network(network, strict=False) for network in networks]


def _validate_hostname(hostname: str, allowed_hosts: Optional[Iterable[str]]) -> str:
    normalized_hostname = hostname.strip().lower().rstrip(".")
    if not normalized_hostname or normalized_hostname in _PRIVATE_HOSTS:
        raise UnsafeURLError("Unsafe hostname")

    allowed_host_set = _normalize_allowed_hosts(allowed_hosts)
    if allowed_host_set and normalized_hostname not in allowed_host_set:
        raise UnsafeURLError("Host is not in allowlist")

    return normalized_hostname


def _resolve_hostname(hostname: str) -> Sequence[ipaddress._BaseAddress]:
    try:
        return [ipaddress.ip_address(hostname)]
    except ValueError:
        pass

    addresses = set()
    for family, __, ___, ____, sockaddr in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM):
        if family not in (socket.AF_INET, socket.AF_INET6):
            continue
        addresses.add(sockaddr[0])
    if not addresses:
        raise UnsafeURLError("Hostname cannot be resolved")
    return [ipaddress.ip_address(address) for address in addresses]


def validate_safe_url(
    url: str,
    allowed_hosts: Optional[Iterable[str]] = None,
    blocked_ports: Optional[Iterable[int]] = None,
    blocked_networks: Optional[Iterable[str]] = None,
) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeURLError("Invalid URL scheme")
    if parsed.username or parsed.password:
        raise UnsafeURLError("URL credentials are not allowed")
    if parsed.fragment:
        parsed = parsed._replace(fragment="")

    hostname = _validate_hostname(parsed.hostname or "", allowed_hosts)
    blocked_port_set = {int(port) for port in blocked_ports or []}
    if parsed.port is not None and parsed.port in blocked_port_set:
        raise UnsafeURLError("Blocked port")

    blocked_ipsets = _compile_blocked_networks(blocked_networks)
    for ip_obj in _resolve_hostname(hostname):
        if any(ip_obj in network for network in blocked_ipsets):
            raise UnsafeURLError("Blocked network")
        if any([ip_obj.is_loopback, ip_obj.is_link_local, ip_obj.is_multicast, ip_obj.is_reserved]):
            raise UnsafeURLError("Unsafe IP address")

    netloc = hostname
    if parsed.port is not None:
        netloc = f"{netloc}:{parsed.port}"
    return urlunparse(parsed._replace(netloc=netloc))


def validate_compatible_url(
    url: str,
    blocked_ports: Optional[Iterable[int]] = None,
    blocked_networks: Optional[Iterable[str]] = None,
) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeURLError(f"Invalid scheme: {parsed.scheme}")
    if parsed.username or parsed.password:
        raise UnsafeURLError("URL credentials are not allowed")
    hostname = parsed.hostname
    if not hostname:
        raise UnsafeURLError("Missing hostname")

    blocked_port_set = {int(port) for port in blocked_ports or []}
    if parsed.port is not None and parsed.port in blocked_port_set:
        raise UnsafeURLError(f"Blocked port: {parsed.port}")

    blocked_ipsets = [ipaddress.ip_network(network, strict=False) for network in blocked_networks or []]
    for ip_obj in _resolve_hostname(hostname):
        for network in blocked_ipsets:
            if ip_obj in network:
                raise UnsafeURLError(f"Blocked network: {ip_obj} in {network}")
        if ip_obj.is_loopback:
            raise UnsafeURLError("Loopback address detected")
        if ip_obj.is_link_local:
            raise UnsafeURLError("Link local address detected")

    return url


def is_safe_url(url_list: list, blocked_ports: list = [], blocked_networks: list = []) -> Tuple[bool, str]:
    try:
        for url in url_list:
            if not url:
                continue
            validate_compatible_url(url=url, blocked_ports=blocked_ports, blocked_networks=blocked_networks)
    except Exception as exc:
        return False, str(exc) or "URL validation failed"
    return True, "All URLs are safe"


def safe_requests_get(
    url: str,
    allowed_hosts: Optional[Iterable[str]] = None,
    blocked_ports: Optional[Iterable[int]] = None,
    blocked_networks: Optional[Iterable[str]] = None,
    **kwargs,
):
    safe_url = validate_safe_url(url, allowed_hosts, blocked_ports, blocked_networks)
    kwargs.setdefault("timeout", 5)
    kwargs["allow_redirects"] = False
    kwargs.setdefault("proxies", {})
    return requests.get(safe_url, **kwargs)


def safe_urlopen(
    url: str,
    allowed_hosts: Optional[Iterable[str]] = None,
    blocked_ports: Optional[Iterable[int]] = None,
    blocked_networks: Optional[Iterable[str]] = None,
    timeout: int = 10,
):
    safe_url = validate_safe_url(url, allowed_hosts, blocked_ports, blocked_networks)
    opener = build_opener(NoRedirectHandler)
    return opener.open(safe_url, timeout=timeout)
