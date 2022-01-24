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

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from . import constants


class ConcurrentControlConfigSerializer(serializers.Serializer):
    execute_all = serializers.BooleanField(
        label=_("是否全量执行"), required=False, default=constants.DEFAULT_CONCURRENT_CONTROL_CONFIG["execute_all"]
    )
    limit = serializers.IntegerField(
        label=_("每批任务的执行数量限制"),
        required=False,
        min_value=1,
        default=constants.DEFAULT_CONCURRENT_CONTROL_CONFIG["limit"],
    )
    is_concurrent_between_batches = serializers.BooleanField(
        label=_("批次间是否并发执行"),
        required=False,
        default=constants.DEFAULT_CONCURRENT_CONTROL_CONFIG["is_concurrent_between_batches"],
    )
    interval = serializers.FloatField(
        label=_("任务提交间隔"), min_value=0, required=False, default=constants.DEFAULT_CONCURRENT_CONTROL_CONFIG["interval"]
    )
