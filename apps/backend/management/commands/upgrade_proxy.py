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
from __future__ import absolute_import, unicode_literals

from django.core.management.base import BaseCommand

from apps.node_man import constants
from apps.node_man.models import Host
from common.api import NodeApi


class Command(BaseCommand):
    def handle(self, *args, **options):
        """
        清理老的instance record
        """
        proxy_host_ids = Host.objects.filter(node_type=constants.NodeType.PROXY).values_list("bk_host_id", flat=True)

        params = {
            "run_immediately": True,
            "bk_app_code": "nodeman",
            "bk_username": "admin",
            "scope": {
                "node_type": "INSTANCE",
                "object_type": "HOST",
                "nodes": [{"bk_host_id": bk_host_id} for bk_host_id in proxy_host_ids],
            },
            "steps": [
                {"id": "agent", "type": "AGENT", "config": {"job_type": "UPGRADE_PROXY"}, "params": {"context": {}}}
            ],
        }
        NodeApi.create_subscription(params)
