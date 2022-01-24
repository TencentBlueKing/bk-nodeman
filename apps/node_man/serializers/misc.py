# _*_ coding: utf-8 _*_
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from rest_framework import serializers

from apps.node_man.constants import PLUGIN_OS_CHOICES
from apps.node_man.models import ProcControl


class ProcessControlInfoSerializer(serializers.ModelSerializer):
    module = serializers.CharField(required=False, max_length=32)
    project = serializers.CharField(required=False, max_length=32)
    plugin_package_id = serializers.IntegerField(required=False)

    install_path = serializers.CharField(required=False)
    log_path = serializers.CharField(required=False)
    data_path = serializers.CharField(required=False)
    pid_path = serializers.CharField(required=False)
    start_cmd = serializers.CharField(required=False, allow_blank=True)
    stop_cmd = serializers.CharField(required=False, allow_blank=True)
    restart_cmd = serializers.CharField(required=False, allow_blank=True)
    reload_cmd = serializers.CharField(required=False, allow_blank=True)

    kill_cmd = serializers.CharField(required=False, allow_blank=True)
    version_cmd = serializers.CharField(required=False, allow_blank=True)
    health_cmd = serializers.CharField(required=False, allow_blank=True)
    debug_cmd = serializers.CharField(required=False, allow_blank=True)

    process_name = serializers.CharField(required=False, max_length=128)
    port_range = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    need_delegate = serializers.BooleanField(default=True)

    os = serializers.ChoiceField(required=False, choices=PLUGIN_OS_CHOICES)

    class Meta:
        model = ProcControl
        fields = (
            "id",
            "module",
            "project",
            "plugin_package_id",
            "install_path",
            "log_path",
            "data_path",
            "pid_path",
            "start_cmd",
            "stop_cmd",
            "restart_cmd",
            "reload_cmd",
            "kill_cmd",
            "version_cmd",
            "health_cmd",
            "debug_cmd",
            "os",
            "process_name",
            "port_range",
            "need_delegate",
        )

    def create(self, validated_data):
        data = {
            "module": validated_data["module"],
            "project": validated_data["project"],
            "os": validated_data["os"],
            "plugin_package_id": validated_data["plugin_package_id"],
        }
        process_info, created = ProcControl.objects.update_or_create(defaults=validated_data, **data)
        return process_info
