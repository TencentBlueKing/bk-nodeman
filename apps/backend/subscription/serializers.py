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

import base64

from bkcrypto.asymmetric.ciphers import BaseAsymmetricCipher
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.backend.constants import SubscriptionSwithBizAction
from apps.backend.subscription.tools import check_subscription_is_disabled
from apps.exceptions import ValidationError
from apps.node_man import constants, models, tools
from apps.node_man.models import ProcessStatus
from apps.node_man.serializers import policy
from apps.node_man.serializers.base import SubScopeInstSelectorSerializer
from apps.utils import basic


class GatewaySerializer(serializers.Serializer):
    bk_username = serializers.CharField()
    bk_app_code = serializers.CharField()


class ScopeSerializer(SubScopeInstSelectorSerializer):
    bk_biz_id = serializers.IntegerField(required=False, default=None)
    # TODO: 是否取消掉这个范围内的scope
    bk_biz_scope = serializers.ListField(required=False)
    object_type = serializers.ChoiceField(choices=models.Subscription.OBJECT_TYPE_CHOICES, label="对象类型")
    node_type = serializers.ChoiceField(choices=models.Subscription.NODE_TYPE_CHOICES, label="节点类别")
    need_register = serializers.BooleanField(required=False, default=False, label="是否需要注册到CMDB")
    nodes = serializers.ListField(child=serializers.DictField())

    def validate(self, attrs):
        for node in attrs["nodes"]:
            basic.ipv6_formatter(data=node, ipv6_field_names=["ip"])
            basic.ipv6_formatter(
                data=node.get("instance_info", {}),
                ipv6_field_names=["bk_host_innerip_v6", "bk_host_outerip_v6", "login_ip", "data_ip"],
            )
        return attrs


class TargetHostSerializer(serializers.Serializer):
    bk_host_id = serializers.CharField(required=False, label="目标机器主机ID")
    ip = serializers.CharField(required=False, label="目标机器IP")
    bk_host_innerip = serializers.CharField(required=False, label="目标机器IP")
    bk_cloud_id = serializers.CharField(required=False, label="目标机器管控区域ID")
    bk_supplier_id = serializers.CharField(default="0", label="目标机器开发商ID")

    def validate(self, attrs):
        # bk_host_id 和 (ip, bk_cloud_id) 必须有一组
        if attrs.get("bk_host_id"):
            return attrs

        if (attrs.get("ip") or attrs.get("bk_host_innerip")) and attrs.get("bk_cloud_id"):
            for query_field in ["ip", "bk_host_innerip"]:
                if attrs.get(query_field):
                    attrs[query_field] = attrs[query_field].split(",")[0]
            return attrs

        raise ValidationError("目前机器参数必须要有 bk_host_id 或者 (ip/bk_host_innerip + bk_cloud_id)")


class HostOperateInfoSerializer(serializers.Serializer):
    bk_host_id = serializers.IntegerField(label=_("主机ID"))
    user = serializers.CharField(label=_("操作用户"))


class CreateSubscriptionSerializer(GatewaySerializer):
    class CreateStepSerializer(serializers.Serializer):
        id = serializers.CharField(label="步骤标识符", validators=[])
        type = serializers.ChoiceField(label="步骤类型", choices=constants.SUB_STEP_TUPLE)
        config = serializers.DictField(label="步骤配置")
        params = serializers.DictField(label="步骤参数")

    name = serializers.CharField(required=False, label="订阅名称")
    scope = ScopeSerializer(many=False, label="事件订阅监听的范围")
    steps = serializers.ListField(child=CreateStepSerializer(), min_length=1, label="事件订阅触发的动作列表")
    target_hosts = TargetHostSerializer(many=True, label="下发的目标机器列表", required=False, allow_empty=False)
    run_immediately = serializers.BooleanField(required=False, default=False, label="是否立即执行")
    is_main = serializers.BooleanField(required=False, default=False, label="是否为主配置")
    operate_info = serializers.ListField(required=False, child=HostOperateInfoSerializer(), default=[], label="操作信息")
    system_account = serializers.DictField(required=False, label=_("操作系统对应账户"))

    # 策略新参数
    plugin_name = serializers.CharField(required=False, label="插件名")
    bk_biz_scope = serializers.ListField(child=serializers.IntegerField(), required=False, default=[], label="订阅监听业务范围")
    category = serializers.ChoiceField(
        required=False,
        choices=list(models.Subscription.CATEGORY_ALIAS_MAP.items()),
        label="订阅类型",
    )

    # 灰度策略指定父策略
    pid = serializers.IntegerField(required=False, label="父策略ID")

    def validate(self, attrs):
        if check_subscription_is_disabled(
            subscription_identity=attrs["scope"], scope=attrs["scope"], steps=attrs["steps"]
        ):
            raise ValidationError(_("订阅范围包含Gse2.0灰度业务"))
        step_types = {step["type"] for step in attrs["steps"]}
        if attrs.get("system_account"):
            for key in attrs["system_account"]:
                if key not in constants.OS_TUPLE:
                    raise ValidationError(_(f"操作系统类型只能为{constants.OS_TUPLE}"))
        if constants.SubStepType.AGENT not in step_types:
            return attrs

        fields_need_decrypt = ["password", "key"]
        cipher: BaseAsymmetricCipher = tools.HostTools.get_asymmetric_cipher()
        for node in attrs["scope"]["nodes"]:
            instance_info = node.get("instance_info", {})
            if not instance_info:
                continue
            for field_need_decrypt in fields_need_decrypt:
                if isinstance(instance_info.get(field_need_decrypt), str):
                    instance_info[field_need_decrypt] = tools.HostTools.decrypt_with_friendly_exc_handle(
                        cipher=cipher, encrypt_message=instance_info[field_need_decrypt], raise_exec=ValidationError
                    )
                instance_info[field_need_decrypt] = base64.b64encode(
                    instance_info.get(field_need_decrypt, "").encode()
                ).decode()
        return attrs

    class Meta:
        refer_name = "create"


class GetSubscriptionSerializer(GatewaySerializer):
    subscription_id_list = serializers.ListField(child=serializers.IntegerField(), label="订阅ID列表")
    show_deleted = serializers.BooleanField(default=False, label="显示已删除的订阅")


class UpdateSubscriptionSerializer(GatewaySerializer):
    class UpdateScopeSerializer(SubScopeInstSelectorSerializer):
        node_type = serializers.ChoiceField(choices=models.Subscription.NODE_TYPE_CHOICES)
        nodes = serializers.ListField()
        bk_biz_id = serializers.IntegerField(required=False, default=None)

    class UpdateStepSerializer(serializers.Serializer):
        id = serializers.CharField()
        type = serializers.CharField(required=False)
        params = serializers.DictField()
        config = serializers.DictField(required=False)

    subscription_id = serializers.IntegerField()
    name = serializers.CharField(required=False)
    scope = UpdateScopeSerializer()
    steps = serializers.ListField(child=UpdateStepSerializer())
    run_immediately = serializers.BooleanField(required=False, default=False)
    operate_info = serializers.ListField(required=False, child=HostOperateInfoSerializer(), default=[], label="操作信息")
    system_account = serializers.DictField(required=False, label=_("操作系统对应账户"))

    # 策略新参数
    plugin_name = serializers.CharField(required=False)
    bk_biz_scope = serializers.ListField(child=serializers.IntegerField(), required=False, default=[])
    category = serializers.CharField(required=False)

    def validate(self, attrs):
        if attrs.get("system_account"):
            for key in attrs["system_account"]:
                if key not in constants.OS_TUPLE:
                    raise ValidationError(_(f"操作系统类型只能为{constants.OS_TUPLE}"))
        return attrs


class DeleteSubscriptionSerializer(GatewaySerializer):
    subscription_id = serializers.IntegerField(label="订阅ID")


class SwitchSubscriptionSerializer(GatewaySerializer):
    subscription_id = serializers.IntegerField(label="订阅ID")
    action = serializers.ChoiceField(choices=["enable", "disable"], label="启停动作")


class RunSubscriptionSerializer(GatewaySerializer):
    class RunScopeSerializer(SubScopeInstSelectorSerializer):
        node_type = serializers.ChoiceField(choices=models.Subscription.NODE_TYPE_CHOICES, label="节点类型")
        nodes = serializers.ListField(child=serializers.DictField(), label="拓扑节点列表")

    subscription_id = serializers.IntegerField(label="订阅ID")
    scope = RunScopeSerializer(required=False, label="订阅监听的范围")
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
    page = serializers.IntegerField(required=False, min_value=1, default=1, label="当前页面")
    pagesize = serializers.IntegerField(required=False, default=-1, label="页面大小")
    start = serializers.IntegerField(required=False, label="开始位置优先于page使用", min_value=1)
    exclude_instance_ids = serializers.ListField(
        required=False, child=serializers.CharField(), label="排除的实例列表", default=[]
    )
    # 放开对status的可选项校验
    statuses = serializers.ListField(required=False, child=serializers.CharField(), label="过滤的状态列表")
    return_all = serializers.BooleanField(required=False, default=False, label="是否返回全量")
    instance_id_list = serializers.ListField(required=False, child=serializers.CharField(), label="需过滤的实例ID列表")
    subscription_id = serializers.IntegerField(label="订阅任务ID")
    task_id_list = serializers.ListField(child=serializers.IntegerField(), required=False, label="任务ID列表")
    need_detail = serializers.BooleanField(default=False, label="是否需要详情")
    need_aggregate_all_tasks = serializers.BooleanField(default=False, label="是否需要聚合全部任务查询最后一次视图")
    need_out_of_scope_snapshots = serializers.BooleanField(default=True, label="是否需要已不在范围内的快照信息")


class TaskResultDetailSerializer(GatewaySerializer):
    subscription_id = serializers.IntegerField()
    task_id = serializers.IntegerField(required=False)
    task_id_list = serializers.ListField(child=serializers.IntegerField(), required=False)
    instance_id = serializers.CharField()


class InstanceHostStatusSerializer(GatewaySerializer):
    subscription_id_list = serializers.ListField(child=serializers.IntegerField(), label="订阅ID列表")
    show_task_detail = serializers.BooleanField(default=False, label="展示任务详细信息")
    need_detail = serializers.BooleanField(default=False, label="展示实例主机详细信息")


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
    sub_inst_id = serializers.IntegerField()
    host_install_pipeline_id = serializers.CharField()
    is_uninstall = serializers.BooleanField()


class SubscriptionStatisticSerializer(serializers.Serializer):
    subscription_id_list = serializers.ListField()

    def validate(self, attrs):
        attrs["subscription_id_list"] = list(set(attrs["subscription_id_list"]))
        return attrs


class SearchDeployPolicySerializer(GatewaySerializer, policy.SearchDeployPolicySerializer):
    pass


class QueryHostPolicySerializer(serializers.Serializer):
    bk_host_id = serializers.IntegerField()


class QueryHostSubscriptionsSerializer(TargetHostSerializer):
    source_type = serializers.ChoiceField(choices=ProcessStatus.SOURCE_TYPE_CHOICES)


class SubscriptionSwitchBizSerializer(serializers.Serializer):
    bk_biz_ids = serializers.ListField(child=serializers.IntegerField())
    action = serializers.ChoiceField(choices=SubscriptionSwithBizAction.list_choices())


class ClearnSubscriptionSerializer(serializers.Serializer):
    subscription_id_list = serializers.ListField(required=True, label=_("订阅ID列表"), child=serializers.IntegerField())
    action_type = serializers.ChoiceField(choices=constants.OpType, default="STOP", label=_("执行动作类型"))
    is_force = serializers.BooleanField(default=False, label=_("是否强制清理"))
