# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import os
import uuid

from apps.utils import env
from apps.utils.unittest.testcase import CustomBaseTestCase


class TestEnv(CustomBaseTestCase):
    def test_get_type_env(self):
        def _test_bool_type():
            _cases = [
                {"key": uuid.uuid4().hex, "value": "True", "except_value": True},
                {"key": uuid.uuid4().hex, "value": "False", "except_value": False},
                {"key": uuid.uuid4().hex, "value": "false", "except_value": False},
                {"key": uuid.uuid4().hex, "value": "true", "except_value": True},
            ]
            for _case in _cases:
                os.environ[_case["key"]] = _case["value"]
                self.assertEqual(env.get_type_env(key=_case["key"], _type=bool), _case["except_value"])

                os.environ.pop(_case["key"])

            _not_bool_key = uuid.uuid4().hex
            os.environ[_not_bool_key] = "not bool"
            self.assertRaises(ValueError, env.get_type_env, key=_not_bool_key, _type=bool)
            os.environ.pop(_not_bool_key)

        def _test_int_type():
            _numbers = [0, -1, 1, 1234567890]
            for _number in _numbers:
                _key = uuid.uuid4().hex
                os.environ[_key] = str(_number)
                self.assertEqual(env.get_type_env(key=_key, _type=int), _number)
                os.environ.pop(_key)

        def _test_str_type():
            _strings = ["1", "2"]
            for _string in _strings:
                _key = uuid.uuid4().hex
                os.environ[_key] = str(_string)
                self.assertEqual(env.get_type_env(key=_key, _type=str), _string)
                os.environ.pop(_key)

        def _test_get_default():
            _default_values = [10, False, "TYPE"]
            for _default_value in _default_values:
                self.assertEqual(env.get_type_env(key=uuid.uuid4().hex, default=_default_value), _default_value)

        _test_bool_type()
        _test_int_type()
        _test_str_type()
        _test_get_default()
