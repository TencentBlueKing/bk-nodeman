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

from apps.mock_data.backend_mkd.subscription import api


class SubscriptionIdSer(serializers.Serializer):
    subscription_id = serializers.IntegerField(help_text=_("订阅ID"))


class RunResponseSerializer(SubscriptionIdSer):
    task_id = serializers.IntegerField(help_text=_("任务ID"), required=True)

    class Meta:
        swagger_schema_fields = {"example": api.SUBSCRIPTION_CREATE_RESPONSE}


class CreateResponseSerializer(SubscriptionIdSer):
    task_id = serializers.IntegerField(help_text=_("任务ID"), required=False)

    class Meta:
        swagger_schema_fields = {"example": api.SUBSCRIPTION_CREATE_RESPONSE}


class InfoResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": api.SUBSCRIPTION_INFO_RESPONSE}


class UpdateResponseSerializer(SubscriptionIdSer):
    task_id = serializers.IntegerField(help_text=_("任务ID"), required=False)

    class Meta:
        swagger_schema_fields = {"example": api.SUBSCRIPTION_CREATE_RESPONSE}


class DeleteResponseSerializer(serializers.Serializer):
    pass


class TaskResultResponseSerializer(serializers.Serializer):
    total = serializers.IntegerField(help_text=_("实例记录数量总和"), required=False)
    list = serializers.ListField(child=serializers.DictField(), help_text=_("实例状态列表"), required=False)
    status_counter = serializers.DictField(help_text=_("订阅全局状态统计"), required=False)

    class Meta:
        swagger_schema_fields = {"example": api.SUBSCRIPTION_TASK_RESULT_RESPONSE}


class SwitcResponseSerializer(SubscriptionIdSer):
    action = serializers.ChoiceField(choices=["enable", "disable"], help_text=_("启停动作"))

    class Meta:
        swagger_schema_fields = {"example": api.SUBSCRIPTION_TASK_RESULT_RESPONSE}


class RetryResponseSerializer(serializers.Serializer):
    task_id = serializers.CharField(help_text=_("任务ID"))

    class Meta:
        swagger_schema_fields = {"example": api.SUBSCRIPTION_RETRY_RESPONSE}


class InstanceStatusResponseSerializer(SubscriptionIdSer):
    pass
