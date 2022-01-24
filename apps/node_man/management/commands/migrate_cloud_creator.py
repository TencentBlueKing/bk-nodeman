# coding: utf-8
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""


from django.core.management.base import BaseCommand

from apps.component.esbclient import client_v2
from apps.node_man.models import Cloud


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("-c", "--bk_cloud_id", type=int, help="cloud id")
        parser.add_argument("-b", "--bk_biz_id", type=int, help="biz id")

    def handle(self, *args, **kwargs):
        bk_biz_maintainer = (
            client_v2.cc.search_business(
                {
                    "fields": ["bk_biz_id", "bk_biz_name", "bk_biz_maintainer"],
                    "condition": {"bk_biz_id": kwargs["bk_biz_id"]},
                }
            )["info"][0]
            .get("bk_biz_maintainer", "")
            .split(",")
        )
        cloud = Cloud.objects.get(bk_cloud_id=kwargs["bk_cloud_id"])
        cloud.creator = bk_biz_maintainer
        cloud.save()
