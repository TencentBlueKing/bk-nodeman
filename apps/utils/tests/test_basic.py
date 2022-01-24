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

from copy import deepcopy

from apps.utils import basic
from apps.utils.unittest.testcase import CustomBaseTestCase


class TestBasic(CustomBaseTestCase):
    def test_remove_keys_from_dict(self):
        unit_data = {1: [1, 2], 2: [{2: 1, 1: 1}], "3": ["1", "2", {2: "3"}]}

        def _test_dict():
            _data = deepcopy(unit_data)

            # 测试递归移除
            _result = basic.remove_keys_from_dict(origin_data=_data, keys=[1, 2], recursive=True, return_deep_copy=True)
            self.assertEqual(_result, {"3": ["1", "2", {}]})
            # 深拷贝模式下返回的不是原对象
            self.assertFalse(_result == _data)

            # 测试非递归移除，仅移除一层
            _result = basic.remove_keys_from_dict(origin_data=_data, keys={1, 2}, return_deep_copy=True)
            self.assertEqual(_result, {"3": ["1", "2", {2: "3"}]})
            self.assertFalse(_result == _data)

            # 测试非深拷贝（操作原数据）
            _result = basic.remove_keys_from_dict(origin_data=_data, keys=(1,), return_deep_copy=False)
            self.assertTrue(_result == _data)

        def _test_list():
            _data = [deepcopy(unit_data), deepcopy(unit_data)]
            _result = basic.remove_keys_from_dict(origin_data=_data, keys=[1, 2], recursive=True)
            self.assertEqual(
                _result,
                [
                    basic.remove_keys_from_dict(origin_data=unit_data, keys=[1, 2], recursive=True),
                    basic.remove_keys_from_dict(origin_data=unit_data, keys=[1, 2], recursive=True),
                ],
            )

        def _test_empty():
            self.assertEqual(basic.remove_keys_from_dict(origin_data=[], keys=[]), [])
            self.assertEqual(basic.remove_keys_from_dict(origin_data={}, keys=[]), {})

        _test_dict()
        _test_list()
        _test_empty()
