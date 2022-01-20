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
from django.test import TestCase

from apps.node_man.handlers.install_channel import InstallChannelHandler
from apps.node_man.tests.utils import create_install_channel


class TestInstallChannel(TestCase):
    def test_install_channel_list(self, *args, **kwargs):
        # 创建安装通道100个
        number = 100
        bk_cloud_channel_map = create_install_channel(number)
        install_channels = InstallChannelHandler.list()
        for bk_cloud_id, channels in bk_cloud_channel_map.items():
            cloud_install_channel = [channel for channel in install_channels if channel["bk_cloud_id"] == bk_cloud_id]
            self.assertEqual(len(cloud_install_channel), len(channels))

    def test_install_channel_create(self, *args, **kwargs):
        # 创建安装通道1000个
        host_ip = "127.0.0.1"
        bk_cloud_id = 123
        install_channel_dict = InstallChannelHandler(bk_cloud_id=bk_cloud_id).create(
            name="create_channel",
            jump_servers=[host_ip],
            upstream_servers={"taskserver": [host_ip], "btfileserver": [host_ip], "dataserver": [host_ip]},
        )
        self.assertEqual(
            install_channel_dict["upstream_servers"],
            {"taskserver": [host_ip], "btfileserver": [host_ip], "dataserver": [host_ip]},
        )

    def test_install_channel_update(self, *args, **kwargs):
        # 创建安装通道1000个
        new_channel_name = "update_channel"
        bk_cloud_channel_map = create_install_channel(1)
        for bk_cloud_id, install_channels in bk_cloud_channel_map.items():
            for install_channel in install_channels:
                update_install_channel_dict = InstallChannelHandler(bk_cloud_id=bk_cloud_id).update(
                    install_channel_id=install_channel.id,
                    name=new_channel_name,
                    jump_servers=install_channel.jump_servers,
                    upstream_servers=install_channel.upstream_servers,
                )
                self.assertEqual(update_install_channel_dict["name"], new_channel_name)

    def test_install_channel_destroy(self, *args, **kwargs):
        bk_cloud_channel_map = create_install_channel(10)
        for bk_cloud_id, install_channels in bk_cloud_channel_map.items():
            for install_channel in install_channels:
                InstallChannelHandler(bk_cloud_id=bk_cloud_id).destroy(
                    install_channel_id=install_channel.id,
                )
        self.assertEqual(len(InstallChannelHandler.list()), 0)
