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
import json
import typing

from django.conf import settings

from apps.backend.utils.data_renderer import nested_render_data
from apps.node_man import constants, models

from ..common import script_content
from .base import AgentCommonData, AgentPushConfigService


class PushEnvironFilesService(AgentPushConfigService):
    def get_config_info_list(
        self, data, common_data: AgentCommonData, host: models.Host
    ) -> typing.List[typing.Dict[str, typing.Any]]:

        if host.os_type == constants.OsType.WINDOWS:
            environ_file_names: typing.List[str] = ["environ.sh", "environ.bat"]
        else:
            environ_file_names: typing.List[str] = ["environ.sh"]

        agent_config: typing.Dict[str, typing.Any] = common_data.host_id__ap_map[host.bk_host_id].get_agent_config(
            host.os_type
        )
        path_sep: str = (constants.LINUX_SEP, constants.WINDOWS_SEP)[host.os_type == constants.OsType.WINDOWS]

        setup_path: str = agent_config["setup_path"]
        dataipc: str = agent_config.get("dataipc") or ""
        plugin_setup_path: str = path_sep.join([setup_path, constants.PluginChildDir.OFFICIAL.value])

        if host.os_type == constants.OsType.WINDOWS:
            setup_path: str = json.dumps(setup_path)[1:-1]
            plugin_setup_path: str = json.dumps(plugin_setup_path)[1:-1]

        config_info_list: typing.List[typing.Dict[str, typing.Any]] = []

        for environ_file_name in environ_file_names:
            template = (script_content.ENVIRON_BAT_TEMPLATE, script_content.ENVIRON_SH_TEMPLATE)[
                environ_file_name == "environ.sh"
            ]

            config_info_list.append(
                {
                    "file_name": environ_file_name,
                    "content": nested_render_data(
                        template, {"setup_path": setup_path, "dataipc": dataipc, "plugin_setup_path": plugin_setup_path}
                    ),
                }
            )

        return config_info_list

    def get_file_target_path(self, data, common_data: AgentCommonData, host: models.Host) -> str:
        environ_dir: str = (settings.GSE_ENVIRON_DIR, settings.GSE_ENVIRON_WIN_DIR)[
            host.os_type == constants.OsType.WINDOWS
        ]
        return environ_dir
