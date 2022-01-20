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

from apps.exceptions import ValidationError
from apps.node_man import constants, exceptions, models, tools
from apps.node_man.serializers import base
from apps.utils import basic


class SearchDeployPolicySerializer(serializers.Serializer):
    class SortSerializer(serializers.Serializer):
        head = serializers.ChoiceField(label=_("排序字段"), choices=list(constants.POLICY_HEAD_TUPLE))
        sort_type = serializers.ChoiceField(label=_("排序类型"), choices=list(constants.SORT_TUPLE))

    bk_biz_ids = serializers.ListField(child=serializers.IntegerField(min_value=0), min_length=1, required=False)
    only_root = serializers.BooleanField(label="仅搜索父策略", required=False, default=True)
    conditions = serializers.ListField(required=False)
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    pagesize = serializers.IntegerField(required=False, default=10)
    sort = SortSerializer(label=_("排序"), required=False)


class FetchPolicyTopoSerializer(serializers.Serializer):
    bk_biz_ids = serializers.ListField(
        label=_("业务ID列表"), child=serializers.IntegerField(min_value=0), min_length=1, required=False
    )
    plugin_name = serializers.CharField(label=_("插件名称"), required=False)
    keyword = serializers.CharField(label=_("模糊搜索关键字，支持策略名称、插件名称的模糊搜索"), required=False)
    is_lazy = serializers.BooleanField(label=_("是否采取懒加载策略（仅返回一级节点）"), required=False, default=False)


class CreatePolicySerializer(serializers.Serializer):
    name = serializers.CharField(min_length=1)
    # 策略范围
    scope = base.ScopeSerializer()
    # 参数配置
    steps = serializers.ListField(child=base.StepSerializer(), min_length=1)

    pid = serializers.IntegerField(label=_("所属父策略"), required=False, default=models.Subscription.ROOT)

    def validate(self, data):
        if data["pid"] == models.Subscription.ROOT:
            return data

        parent_policy = tools.policy.PolicyTools.get_policy(policy_id=data["pid"], need_steps=True)

        # 校验插件相同
        if not basic.list_equal(
            [step["id"] for step in data["steps"]], [step["id"] for step in parent_policy["steps"]]
        ):
            raise ValidationError(_("灰度策略与父策略所部署插件不一致"))

        if parent_policy["pid"] != models.Subscription.ROOT:
            raise ValidationError(_("灰度策略不能作为父策略"))

        if data["scope"]["node_type"] != models.Subscription.NodeType.INSTANCE:
            raise ValidationError(_("灰度策略仅支持静态IP目标"))

        parent_policy_host_ids = set(tools.HostV2Tools.list_scope_host_ids(parent_policy["scope"]))
        grayscale_host_ids = set(tools.HostV2Tools.list_scope_host_ids(data["scope"]))
        # TODO 创建灰度后缩小父策略目标，已创建的灰度可能调整目标时极易校验失败，考虑在update时放开校验
        if parent_policy_host_ids & grayscale_host_ids != grayscale_host_ids:
            raise ValidationError(_("灰度策略目标不在父策略范围内"))

        return data


class UpdatePolicySerializer(CreatePolicySerializer):
    pass


class SimpleUpdatePolicySerializer(serializers.Serializer):
    name = serializers.CharField(min_length=1)


class SelectReviewSerializer(serializers.Serializer):
    bk_biz_id = serializers.ListField(
        label=_("业务ID"), child=serializers.IntegerField(min_value=0), required=False, min_length=1
    )
    conditions = serializers.ListField(label=_("搜索条件"), required=False, default=[])
    page = serializers.IntegerField(label=_("当前页数"), required=False, min_value=1, default=1)
    pagesize = serializers.IntegerField(label=_("分页大小"), required=False, default=10)
    policy_id = serializers.IntegerField(label=_("策略ID"), required=False)
    # 策略创建参数
    name = serializers.CharField(min_length=1, required=False)
    # 策略范围
    scope = base.ScopeSerializer(required=False)
    # 参数配置
    steps = serializers.ListField(required=False, child=base.StepSerializer(), min_length=1)

    with_hosts = serializers.BooleanField(required=False, default=True)

    def validate(self, data):
        if "policy_id" in data or "scope" in data:
            return data
        raise ValidationError(_("policy_id, scope 必须其中一个存在"))


class RollbackPreview(serializers.Serializer):
    policy_id = serializers.IntegerField(label=_("策略ID"))
    bk_biz_id = serializers.ListField(
        label=_("业务ID"), child=serializers.IntegerField(min_value=0), required=False, min_length=1
    )
    conditions = serializers.ListField(label=_("搜索条件"), required=False, default=[])
    page = serializers.IntegerField(label=_("当前页数"), required=False, min_value=1, default=1)
    pagesize = serializers.IntegerField(label=_("分页大小"), required=False, default=10)


class MigratePreviewSerializer(SelectReviewSerializer):
    category = serializers.ChoiceField(
        label=_("订阅类别"),
        required=False,
        default=models.Subscription.CategoryType.POLICY,
        choices=models.Subscription.CATEGORY_ALIAS_MAP,
    )
    job_type = serializers.ChoiceField(label=_("任务类型"), required=False, choices=constants.JOB_TUPLE)
    plugin_name = serializers.CharField(label=_("插件名称"), required=False)


class PluginPreSelectionSerializer(serializers.Serializer):
    # 策略范围
    scope = base.ScopeSerializer()
    plugin_id = serializers.IntegerField()


class HostPolicySerializer(serializers.Serializer):
    bk_host_id = serializers.IntegerField(label=_("主机ID"))


class PolicyOperateSerializer(serializers.Serializer):
    policy_id = serializers.IntegerField(label=_("策略ID"), required=True)
    op_type = serializers.ChoiceField(label=_("操作类型"), required=True, choices=constants.POLICY_OP_CHOICES)
    only_disable = serializers.BooleanField(label=_("仅停用策略"), required=False, default=False)
    pid = serializers.IntegerField(label=_("父策略ID"), required=False)

    def validate(self, data):
        policy: models.Subscription = models.Subscription.objects.filter(id=data["policy_id"]).first()
        if not policy:
            exceptions.PolicyNotExistError(_("不存在ID为: {id} 的策略").format(id=data["policy_id"]))
        if policy.is_running():
            exceptions.PolicyIsRunningError({"policy_id": policy.id, "name": policy.name})
        return data


class FetchPolicyAbnormalInfoSerializer(serializers.Serializer):
    policy_ids = serializers.ListField(
        label=_("策略ID列表"), child=serializers.IntegerField(label=_("策略ID")), required=True
    )
