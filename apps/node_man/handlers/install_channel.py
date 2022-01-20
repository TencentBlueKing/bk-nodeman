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
from typing import Dict, List

from django.forms import model_to_dict

from apps.node_man import models
from apps.utils import APIModel


class InstallChannelHandler(APIModel):
    def __init__(self, bk_cloud_id: int, *args, **kwargs):
        self.bk_cloud_id = bk_cloud_id
        super().__init__(*args, **kwargs)

    @staticmethod
    def list() -> List[Dict]:
        """安装通道数量较少，直接返回全量即可"""
        return list(models.InstallChannel.objects.all().values())

    def create(self, name: str, jump_servers: List[str], upstream_servers: Dict[str, List[str]]) -> Dict:
        install_channel = models.InstallChannel.objects.create(
            bk_cloud_id=self.bk_cloud_id, name=name, jump_servers=jump_servers, upstream_servers=upstream_servers
        )
        return model_to_dict(install_channel)

    def update(
        self, install_channel_id: int, name: str, jump_servers: List[str], upstream_servers: Dict[str, List[str]]
    ) -> Dict:
        models.InstallChannel.objects.filter(id=install_channel_id, bk_cloud_id=self.bk_cloud_id).update(
            name=name, jump_servers=jump_servers, upstream_servers=upstream_servers
        )
        return model_to_dict(models.InstallChannel.objects.get(id=install_channel_id))

    def destroy(self, install_channel_id: int):
        models.InstallChannel.objects.filter(bk_cloud_id=self.bk_cloud_id, id=install_channel_id).delete()
