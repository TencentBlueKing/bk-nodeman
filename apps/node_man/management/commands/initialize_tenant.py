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
from django.core.management import BaseCommand

from apps.node_man.periodic_tasks.utils import get_tenant_id_list
from common.log import logger


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("-t", "--tenant_id", help="租户ID", type=str)

    def handle(self, *args, **options):
        exist_tenant_id_list = get_tenant_id_list()
        tenant_id = options.get("tenant_id")
        if tenant_id not in exist_tenant_id_list:
            logger.error(f"tenant_id {tenant_id} not exist or register, initialize tenant failed")
            return
        if not tenant_id:
            logger.error(message="tenant_id is None initialize tenant failed")
            return

        logger.info(message=f"initialize tenant {tenant_id} success")
