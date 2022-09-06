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

from apps.node_man import constants


class ConstantsTestCase(TestCase):
    def test_plugin_os_choices(self):
        # 无特殊情况下，插件操作类型系统应跟Agent支持的操作系统类型统一
        self.assertEqual(len(constants.PLUGIN_OS_TUPLE), len(constants.OS_TUPLE))
        for os_type in constants.OS_TUPLE:
            self.assertTrue(os_type.lower() in constants.PLUGIN_OS_TUPLE)
