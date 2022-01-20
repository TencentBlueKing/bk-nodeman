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

from apps.node_man.constants import JOB_MAX_VALUE, NODE_MAN_LOG_LEVEL


class JobSettingSerializer(serializers.Serializer):
    """
    用于创建任务配置的验证
    """

    install_p_agent_timeout = serializers.IntegerField(label=_("安装P-Agent超时时间"), max_value=JOB_MAX_VALUE, min_value=0)
    install_agent_timeout = serializers.IntegerField(label=_("安装Agent超时时间"), max_value=JOB_MAX_VALUE, min_value=0)
    install_proxy_timeout = serializers.IntegerField(label=_("安装Proxy超时时间"), max_value=JOB_MAX_VALUE, min_value=0)
    install_download_limit_speed = serializers.IntegerField(label=_("安装下载限速"), max_value=JOB_MAX_VALUE, min_value=0)
    parallel_install_number = serializers.IntegerField(label=_("并行安装数"), max_value=JOB_MAX_VALUE, min_value=0)
    node_man_log_level = serializers.ChoiceField(label=_("节点管理日志级别"), choices=list(NODE_MAN_LOG_LEVEL))
