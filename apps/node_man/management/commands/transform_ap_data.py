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
import typing

from django.core.management.base import BaseCommand, CommandError

from apps.node_man import models
from apps.node_man.utils.endpoint import EndPointTransform
from common.log import logger


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "-e",
            "--transform",
            required=False,
            help="AP_ID create from V1 AP_ID",
            default=False,
            action="store_true",
        )
        parser.add_argument(
            "-l",
            "--transform_endpoint_to_legacy",
            action="store_true",
            default=False,
            help="Clean up the original mapping ID",
        )
        parser.add_argument(
            "-a",
            "--all_ap",
            action="store_true",
            default=False,
            help="Transform all the AP_IDs in the database",
        )
        parser.add_argument(
            "-t",
            "--transform_ap_id",
            required=False,
            help="Transform target AP_ID in the database",
        )

    def handle(self, **options):
        transform_endpoint_to_legacy = options.get("transform_endpoint_to_legacy")
        transform = options.get("transform")
        if not transform_endpoint_to_legacy and not transform:
            raise CommandError("Please specify the AP_ID to be transformed")
        if transform and transform_endpoint_to_legacy:
            raise CommandError("Please specify only one AP_ID to be transformed")

        all_ap_transform = options.get("all_ap")
        transform_ap_id = options.get("transform_ap_id")
        if all_ap_transform and transform_ap_id:
            raise CommandError("Please specify only one AP_ID to be transformed")
        if not all_ap_transform and not transform_ap_id:
            raise CommandError("Please specify the AP_ID to be transformed")

        if all_ap_transform:
            ap_objects: typing.List[models.AccessPoint] = models.AccessPoint.objects.all()
        else:
            ap_objects: typing.List[models.AccessPoint] = models.AccessPoint.objects.filter(id=transform_ap_id)

        if transform_endpoint_to_legacy:
            transform_func: typing.Callable = EndPointTransform().transform_endpoint_to_legacy
        elif transform:
            transform_func: typing.Callable = EndPointTransform().transform
        else:
            raise CommandError("Please specify the transformation method")

        for ap_object in ap_objects:
            logger.info(f"Transforming AP_ID: {ap_object.id}")
            try:
                ap_object.taskserver = transform_func(ap_object.taskserver)
                ap_object.dataserver = transform_func(ap_object.dataserver)
                ap_object.btfileserver = transform_func(ap_object.btfileserver)
                ap_object.save()
            except Exception as e:
                raise CommandError(f"Failed to transform AP_ID: {ap_object.id}, error: {e}")
