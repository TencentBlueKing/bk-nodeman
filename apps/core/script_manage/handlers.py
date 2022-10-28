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
import typing

from . import base, data


class ScriptManageHandler:
    @staticmethod
    def fetch_match_script_hook_objs(
        script_hooks: typing.List[typing.Dict[str, typing.Any]], os_type: typing.Optional[str] = None
    ) -> typing.List[base.ScriptHook]:
        match_script_hook_objs: typing.List[base.ScriptHook] = []
        for script_hook in script_hooks:
            script_info_obj: typing.Optional[base.ScriptInfo] = data.SCRIPT_NAME__INFO_OBJ_MAP.get(
                script_hook.get("name")
            )
            if script_info_obj is None:
                continue
            if os_type is None or os_type in script_info_obj.support_os_list:
                match_script_hook_objs.append(base.ScriptHook(index=0, script_info_obj=script_info_obj))
        return match_script_hook_objs
