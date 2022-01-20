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
from apps.node_man import constants, exceptions, models


# 安装插件配置
class StepSerializer(serializers.Serializer):
    class SettingSerializer(serializers.Serializer):
        details = serializers.ListField(child=serializers.DictField(), min_length=1)

    id = serializers.CharField()
    type = serializers.ChoiceField(
        choices=[constants.ProcType.PLUGIN], default=constants.ProcType.PLUGIN, required=False
    )
    # 插件配置模板信息
    configs = serializers.ListField(child=serializers.DictField(), min_length=1)
    # 参数配置
    params = serializers.ListField(child=serializers.DictField(), min_length=1)

    def validate(self, data):
        if models.GsePluginDesc.objects.filter(name=data["id"]).first() is None:
            raise exceptions.PluginNotExistError(_("不存在名称为: {name} 的插件").format(name=data["id"]))

        # configs校验：确保选包的os&cpu_arch唯一
        pkg_type_combinations = []
        for config in data["configs"]:
            if all([config.get("os"), config.get("cpu_arch"), config.get("version")]):
                continue
            pkg_type_combinations.append(f"{config['os']}_{config['cpu_arch']}")
            raise ValidationError(_("configs item must be contains (os, cpu_arch, version)"))
        if len(pkg_type_combinations) != len(set(pkg_type_combinations)):
            raise ValidationError(_("相同os & cpu_arch 组合至多选择一个包"))
        return data


# 策略范围
class ScopeSerializer(serializers.Serializer):
    class NodeSerializer(serializers.Serializer):
        bk_biz_id = serializers.IntegerField()
        bk_inst_id = serializers.IntegerField(required=False)
        bk_obj_id = serializers.CharField(required=False)
        bk_host_id = serializers.IntegerField(required=False)

        def validate(self, data):
            if "bk_inst_id" in data and "bk_obj_id" in data and "bk_host_id" not in data:
                return data
            if "bk_host_id" in data and not ("bk_inst_id" in data and "bk_obj_id" in data):
                return data
            raise ValidationError(_("部署节点属性组合必须是 (bk_biz_id, bk_host_id) 或者 (bk_biz_id, bk_obj_id, bk_inst_id)"))

    object_type = serializers.ChoiceField(choices=[models.Subscription.ObjectType.HOST])
    node_type = serializers.ChoiceField(
        choices=[models.Subscription.NodeType.INSTANCE, models.Subscription.NodeType.TOPO]
    )
    nodes = serializers.ListField(child=serializers.DictField(), min_length=1)

    def validate(self, data):
        # 校验节点数据
        for node in data["nodes"]:
            if "bk_biz_id" not in node:
                raise ValidationError(_("节点缺少 bk_biz_id 属性"))
            if "bk_inst_id" in node and "bk_obj_id" in node and "bk_host_id" not in node:
                continue
            if "bk_host_id" in node and not ("bk_inst_id" in node and "bk_obj_id" in node):
                continue
            raise ValidationError(_("部署节点属性组合必须是 (bk_biz_id, bk_host_id) 或者 (bk_biz_id, bk_obj_id, bk_inst_id)"))

        if data["node_type"] == models.Subscription.NodeType.INSTANCE:
            for node in data["nodes"]:
                if "bk_host_id" not in node:
                    raise ValidationError(_("部署节点[{node}]不是主机实例").format(node=node))
        elif data["node_type"] == models.Subscription.NodeType.TOPO:
            for node in data["nodes"]:
                if "bk_inst_id" not in node:
                    raise ValidationError(_("部署节点[{node}不是拓扑节点]").format(node=node))
        return data
