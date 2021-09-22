# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""


from rest_framework import serializers

from apps.exceptions import ValidationError
from apps.node_man import constants, models
from apps.node_man.models import ProcessStatus


class GatewaySerializer(serializers.Serializer):
    bk_username = serializers.CharField()
    bk_app_code = serializers.CharField()


class ScopeSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(required=False, default=None)
    bk_biz_scope = serializers.ListField(required=False)
    object_type = serializers.ChoiceField(choices=models.Subscription.OBJECT_TYPE_CHOICES)
    node_type = serializers.ChoiceField(choices=models.Subscription.NODE_TYPE_CHOICES)
    need_register = serializers.BooleanField(required=False, default=False)
    nodes = serializers.ListField()


class TargetHostSerializer(serializers.Serializer):
    bk_host_id = serializers.CharField(required=False, label="目标机器主机ID")
    ip = serializers.CharField(required=False, label="目标机器IP")
    bk_host_innerip = serializers.CharField(required=False, label="目标机器IP")
    bk_cloud_id = serializers.CharField(required=False, label="目标机器云区域ID")
    bk_supplier_id = serializers.CharField(default="0", label="目标机器开发商ID")

    def validate(self, attrs):
        # bk_host_id 和 (ip, bk_cloud_id) 必须有一组
        if attrs.get("bk_host_id"):
            return attrs

        if (attrs.get("ip") or attrs.get("bk_host_innerip")) and attrs.get("bk_cloud_id"):
            return attrs

        raise ValidationError("目前机器参数必须要有 bk_host_id 或者 (ip/bk_host_innerip + bk_cloud_id)")


class CreateSubscriptionSerializer(GatewaySerializer):
    class ScopeSerializer(serializers.Serializer):
        bk_biz_id = serializers.IntegerField(required=False, default=None)
        bk_biz_scope = serializers.ListField(required=False)
        object_type = serializers.ChoiceField(choices=models.Subscription.OBJECT_TYPE_CHOICES)
        node_type = serializers.ChoiceField(choices=models.Subscription.NODE_TYPE_CHOICES)
        need_register = serializers.BooleanField(required=False, default=False)
        nodes = serializers.ListField()

    class StepSerializer(serializers.Serializer):
        id = serializers.CharField()
        type = serializers.CharField()
        config = serializers.DictField()
        params = serializers.DictField()

    name = serializers.CharField(required=False)
    scope = ScopeSerializer(many=False)
    steps = serializers.ListField(child=StepSerializer(), min_length=1)
    target_hosts = TargetHostSerializer(many=True, label="下发的目标机器列表", required=False, allow_empty=False)
    run_immediately = serializers.BooleanField(required=False, default=False)
    is_main = serializers.BooleanField(required=False, default=False)

    # 策略新参数
    plugin_name = serializers.CharField(required=False)
    bk_biz_scope = serializers.ListField(child=serializers.IntegerField(), required=False, default=[])
    category = serializers.CharField(required=False)

    # 灰度策略指定父策略
    pid = serializers.IntegerField(required=False)


class GetSubscriptionSerializer(GatewaySerializer):
    subscription_id_list = serializers.ListField(child=serializers.IntegerField())
    show_deleted = serializers.BooleanField(default=False)


class UpdateSubscriptionSerializer(GatewaySerializer):
    class ScopeSerializer(serializers.Serializer):
        node_type = serializers.ChoiceField(choices=models.Subscription.NODE_TYPE_CHOICES)
        nodes = serializers.ListField()
        bk_biz_id = serializers.IntegerField(required=False, default=None)

    class StepSerializer(serializers.Serializer):
        id = serializers.CharField()
        params = serializers.DictField()
        config = serializers.DictField(required=False)

    subscription_id = serializers.IntegerField()
    name = serializers.CharField(required=False)
    scope = ScopeSerializer()
    steps = serializers.ListField(child=StepSerializer())
    run_immediately = serializers.BooleanField(required=False, default=False)

    # 策略新参数
    plugin_name = serializers.CharField(required=False)
    bk_biz_scope = serializers.ListField(child=serializers.IntegerField(), required=False, default=[])
    category = serializers.CharField(required=False)


class DeleteSubscriptionSerializer(GatewaySerializer):
    subscription_id = serializers.IntegerField()


class SwitchSubscriptionSerializer(GatewaySerializer):
    subscription_id = serializers.IntegerField()
    action = serializers.ChoiceField(choices=["enable", "disable"])


class RunSubscriptionSerializer(GatewaySerializer):
    class ScopeSerializer(serializers.Serializer):
        node_type = serializers.ChoiceField(choices=models.Subscription.NODE_TYPE_CHOICES)
        nodes = serializers.ListField()

    subscription_id = serializers.IntegerField()
    scope = ScopeSerializer(required=False)
    actions = serializers.DictField(child=serializers.CharField(), required=False)


class RevokeSubscriptionSerializer(GatewaySerializer):
    subscription_id = serializers.IntegerField()
    instance_id_list = serializers.ListField(required=False)


class RetrySubscriptionSerializer(GatewaySerializer):
    subscription_id = serializers.IntegerField()
    instance_id_list = serializers.ListField(required=False)
    # SaaS侧必传
    task_id_list = serializers.ListField(child=serializers.IntegerField(), required=False)
    actions = serializers.DictField(child=serializers.CharField(), required=False)


class CheckTaskReadySerializer(GatewaySerializer):
    subscription_id = serializers.IntegerField()
    task_id_list = serializers.ListField(child=serializers.IntegerField(), required=False)


class TaskResultSerializer(GatewaySerializer):
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    pagesize = serializers.IntegerField(required=False, default=-1)
    # 放开对status的可选项校验
    statuses = serializers.ListField(required=False, child=serializers.CharField())
    return_all = serializers.BooleanField(required=False, default=False)
    instance_id_list = serializers.ListField(required=False, child=serializers.CharField())
    subscription_id = serializers.IntegerField()
    task_id_list = serializers.ListField(child=serializers.IntegerField(), required=False)
    need_detail = serializers.BooleanField(default=False)


class TaskResultDetailSerializer(GatewaySerializer):
    subscription_id = serializers.IntegerField()
    task_id = serializers.IntegerField(required=False)
    task_id_list = serializers.ListField(child=serializers.IntegerField(), required=False)
    instance_id = serializers.CharField()


class InstanceHostStatusSerializer(GatewaySerializer):
    subscription_id_list = serializers.ListField(child=serializers.IntegerField())
    show_task_detail = serializers.BooleanField(default=False)
    need_detail = serializers.BooleanField(default=False)


class RetryNodeSerializer(GatewaySerializer):
    subscription_id = serializers.IntegerField()
    instance_id = serializers.CharField()


class CMDBSubscriptionSerializer(serializers.Serializer):
    event_type = serializers.CharField()
    action = serializers.CharField()
    obj_type = serializers.CharField()
    data = serializers.ListField()


class FetchCommandsSerializer(serializers.Serializer):
    bk_host_id = serializers.IntegerField()
    host_install_pipeline_id = serializers.CharField()
    is_uninstall = serializers.BooleanField()
    batch_install = serializers.BooleanField()


class SubscriptionStatisticSerializer(serializers.Serializer):
    subscription_id_list = serializers.ListField()


class SearchDeployPolicySerializer(GatewaySerializer):
    class SortSerializer(serializers.Serializer):
        head = serializers.ChoiceField(choices=list(constants.POLICY_HEAD_TUPLE))
        sort_type = serializers.ChoiceField(choices=list(constants.SORT_TUPLE))

    bk_biz_ids = serializers.ListField(child=serializers.IntegerField(min_value=0), min_length=1, required=False)
    conditions = serializers.ListField(required=False)
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    pagesize = serializers.IntegerField(required=False, default=10)
    sort = SortSerializer(required=False)
    only_root = serializers.BooleanField(label="仅搜索父策略", required=False, default=True)


class QueryHostPolicySerializer(serializers.Serializer):
    bk_host_id = serializers.IntegerField()


class QueryHostSubscriptionsSerializer(TargetHostSerializer):
    source_type = serializers.ChoiceField(choices=ProcessStatus.SOURCE_TYPE_CHOICES)
