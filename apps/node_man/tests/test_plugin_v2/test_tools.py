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
from django.test import TestCase

from apps.node_man import tools
from apps.node_man.tests.test_plugin_v2 import utils


class TestConfigTplParse(TestCase):
    config_tpl_list = [
        utils.config_tpl_1,
        utils.config_tpl_2,
        utils.config_tpl_3,
        utils.config_tpl_4,
        utils.config_tpl_5,
    ]

    def test_parse2json_success(self):
        for config_tpl in self.config_tpl_list:
            var_json = tools.PluginV2Tools.parse_tpl2var_json(
                tools.PluginV2Tools.shield_tpl_unparse_content(config_tpl)
            )
            tools.PluginV2Tools.simplify_var_json(var_json)
            self.assertTrue(isinstance(var_json, dict))
