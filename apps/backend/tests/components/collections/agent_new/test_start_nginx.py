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
# -*- coding: utf-8 -*-


from apps.backend.components.collections.agent_new import components
from apps.node_man import constants, models

from . import base


class StartIpv4ProxyNginxTestCase(base.JobBaseTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "启动 Ipv4 Proxy Nginx 成功"

    def component_cls(self):
        return components.StartNginxComponent


class StartIpv6ProxyNginxTestCase(base.JobBaseTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "启动 Ipv6 Proxy Nginx 成功"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        models.Host.objects.all().update(node_type=constants.NodeType.PROXY, inner_ipv6="2001:db8:85a3::8a2e:370:7334")

    def component_cls(self):
        return components.StartNginxComponent
