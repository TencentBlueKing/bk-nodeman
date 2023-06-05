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


class GrayBizSerializer(serializers.Serializer):
    bk_biz_ids = serializers.ListField(label=_("业务列表"), child=serializers.IntegerField(), required=True)


class GraySerializer(GrayBizSerializer):
    cloud_ips = serializers.ListField(label=_("管控区域:主机列表"), required=False)


class UpgradeOrRollbackAgentIDSerializer(serializers.Serializer):
    failed = serializers.ListField(label=_("失败的主机"), child=serializers.CharField())
    success = serializers.ListField(label=_("成功的主机"), child=serializers.CharField())
    no_bk_agent_id_hosts = serializers.ListField(label=_("无bk_agent_id的主机"), child=serializers.CharField())
