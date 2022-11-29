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
from typing import Dict, Union

from django.conf import settings
from jinja2 import Template

from apps.backend.components.collections.agent_new.base import (
    AgentCommonData,
    AgentExecuteScriptService,
)
from apps.backend.components.collections.common.script_content import (
    START_NGINX_TEMPLATE,
)
from apps.backend.subscription.errors import ScriptRenderFailed
from apps.node_man import models
from apps.utils import basic


class StartNginxService(AgentExecuteScriptService):
    @property
    def script_name(self):
        return "start_nginx"

    def get_script_content(self, data, common_data: AgentCommonData, host: models.Host) -> str:
        template = Template(START_NGINX_TEMPLATE)
        script_variable_map: Dict[str, Union[str, bool]] = {
            "nginx_path": settings.DOWNLOAD_PATH,
            "bk_nodeman_nginx_download_port": settings.BK_NODEMAN_NGINX_DOWNLOAD_PORT,
            "bk_nodeman_nginx_proxy_pass_port": settings.BK_NODEMAN_NGINX_PROXY_PASS_PORT,
            "is_v6_host": basic.is_v6(host.inner_ipv6),
            "inner_ipv6": host.inner_ipv6,
        }
        try:
            content: str = template.render(script_variable_map)
        except Exception as e:
            raise ScriptRenderFailed({"name": self.script_name, "msg": e})

        return content
