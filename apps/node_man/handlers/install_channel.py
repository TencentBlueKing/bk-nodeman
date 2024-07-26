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
from ipaddress import IPv4Network, ip_address, ip_network
from typing import Dict, List

from django.forms import model_to_dict

from apps.core.concurrent.cache import FuncCacheDecorator
from apps.node_man import constants, models
from apps.utils import APIModel


class InstallChannelHandler(APIModel):
    def __init__(self, bk_cloud_id: int, *args, **kwargs):
        self.bk_cloud_id = bk_cloud_id
        super().__init__(*args, **kwargs)

    @staticmethod
    def list() -> List[Dict]:
        """安装通道数量较少，直接返回全量即可"""
        return list(models.InstallChannel.objects.all().values())

    def create(self, name: str, jump_servers: List[str], upstream_servers: Dict[str, List[str]], hidden=False) -> Dict:
        install_channel = models.InstallChannel.objects.create(
            bk_cloud_id=self.bk_cloud_id,
            name=name,
            jump_servers=jump_servers,
            upstream_servers=upstream_servers,
            hidden=hidden,
        )
        return model_to_dict(install_channel)

    def update(
        self,
        install_channel_id: int,
        name: str,
        jump_servers: List[str],
        upstream_servers: Dict[str, List[str]],
        hidden=False,
    ) -> Dict:
        install_channel = models.InstallChannel.objects.get(id=install_channel_id, bk_cloud_id=self.bk_cloud_id)
        install_channel.name = name
        install_channel.jump_servers = jump_servers
        install_channel.hidden = hidden
        install_channel.upstream_servers.update(**upstream_servers)
        install_channel.save()
        return model_to_dict(models.InstallChannel.objects.get(id=install_channel_id))

    def destroy(self, install_channel_id: int):
        models.InstallChannel.objects.filter(bk_cloud_id=self.bk_cloud_id, id=install_channel_id).delete()

    @staticmethod
    @FuncCacheDecorator(cache_time=20 * constants.TimeUnit.MINUTE)
    def get_install_channel_id_network_segment():
        install_channel_id_network_segment: Dict[str, List[str]] = models.GlobalSettings.get_config(
            key=models.GlobalSettings.KeyEnum.INSTALL_CHANNEL_ID_NETWORK_SEGMENT.value, default={}
        )
        return install_channel_id_network_segment

    @classmethod
    def judge_install_channel(cls, inner_ip: str):
        """
        :param inner_ip: 内网IPv4地址
        :return: 安装通道ID
        """
        install_channel_id_network_segment: Dict[str, List[str]] = cls.get_install_channel_id_network_segment(
            get_cache=True
        )
        network_obj__install_channel_id_map: Dict[IPv4Network, int] = {
            ip_network(network_segment): int(install_channel_id)
            for install_channel_id, network_segments in install_channel_id_network_segment.items()
            for network_segment in network_segments
        }
        for network_obj, install_channel_id in network_obj__install_channel_id_map.items():
            if ip_address(inner_ip) in network_obj:
                return install_channel_id
        return None
