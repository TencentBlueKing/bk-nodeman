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
from collections import defaultdict
from typing import Any, Dict, List, Optional, Union
from unittest import mock

from django.contrib.auth.models import User
from django.test import Client, RequestFactory, TestCase

from apps.utils.unittest import base


class AssertDataMixin:
    # None表示展示全量断言差异
    maxDiff = None

    recursion_type = [dict, list]
    exempted_fields = ["created_at", "updated_at"]

    def remove_keys(self, data: Union[Dict, List], keys: List[str]) -> None:
        """
        移除嵌套数据中dict的指定key-value
        :param data: 目前仅支持List / Dict，后续按需支持
        :param keys: 需要移除的key列表
        :return: None
        """
        children = []
        if isinstance(data, dict):
            for key in keys:
                data.pop(key, None)
            children = data.values()
        elif isinstance(data, list):
            children = data
        for child_data in children:
            if type(child_data) in self.recursion_type:
                self.remove_keys(child_data, keys)
        return

    def assertExemptDataStructure(self, actual_data, expected_data, value_eq=True, list_exempt=False):
        """
        支持字段豁免的数据断言
        :param actual_data: 实际的数据
        :param expected_data: 期望的数据
        :param value_eq: 子数据是否断言
        :param list_exempt: 是否豁免列表
        :return:
        """
        self.remove_keys(actual_data, self.exempted_fields)
        self.remove_keys(expected_data, self.exempted_fields)
        return self.assertDataStructure(actual_data, expected_data, value_eq, list_exempt, is_sort=False)

    def assertDataStructure(self, actual_data, expected_data, value_eq=True, list_exempt=False, is_sort=True):
        actual_data_type = type(actual_data)

        self.assertEqual(
            actual_data_type, type(expected_data), msg=f"actual_data -> {actual_data}, expected_data -> {expected_data}"
        )

        if actual_data_type is dict:
            self.assertListEqual(
                list(actual_data.keys()),
                list(expected_data.keys()),
                is_sort=True,
                msg=f"excepted dict keys -> {expected_data.keys()}, but actual keys -> {actual_data.keys()}",
            )
            for expected_key, expected_value in expected_data.items():
                self.assertDataStructure(
                    actual_data=actual_data[expected_key],
                    expected_data=expected_value,
                    value_eq=value_eq,
                    list_exempt=list_exempt,
                    is_sort=is_sort,
                )
        elif actual_data_type is list:
            if list_exempt:
                return
            if value_eq:
                self.assertListEqual(actual_data, expected_data, is_sort=is_sort)
            else:
                # 默认列表数据结构一致
                _expected_data = expected_data[0]
                for _data in actual_data:
                    self.assertDataStructure(
                        _data, _expected_data, value_eq=value_eq, list_exempt=list_exempt, is_sort=is_sort
                    )

        if value_eq:
            self.assertEqual(actual_data, expected_data)

    def assertListEqual(self, list1, list2, msg=None, is_sort=False):
        if is_sort:
            # TODO 没有考虑Dict类型的排序
            list1.sort()
            list2.sort()
        super().assertListEqual(list1, list2, msg=msg)


class MockSuperUserMixin:
    SUPERUSER_NAME = "admin"
    SUPERUSER_PASSWORD = "admin"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # 创建用于测试的超管
        cls.superuser = User.objects.create_user(
            username=cls.SUPERUSER_NAME,
            password=cls.SUPERUSER_PASSWORD,
            is_superuser=True,
            is_staff=True,
            is_active=True,
        )

    def setUp(self) -> None:
        super().setUp()
        self.client.login(username=self.SUPERUSER_NAME, password=self.SUPERUSER_PASSWORD)

    def tearDown(self) -> None:
        super().tearDown()
        self.client.logout()


class TestCaseLifeCycleMixin:
    def setUp(self) -> None:
        """Hook before test function"""
        super().setUp()

    def tearDown(self) -> None:
        """Hook after test function"""
        super().tearDown()

    @classmethod
    def setUpTestData(cls):
        """Hook in testcase.__call__ , after setUpClass"""
        super().setUpTestData()

    @classmethod
    def setUpClass(cls):
        """Hook method for setting up class fixture before running tests in the class."""
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        """Hook method for deconstructing the class fixture after running all tests in the class."""
        super().tearDownClass()
        mock.patch.stopall()


class OverwriteSettingsMixin(TestCaseLifeCycleMixin):
    OVERWRITE_OBJ__KV_MAP: Optional[Dict[Any, Dict[str, Any]]] = None
    OBJ__ORIGIN_KV_MAP: Optional[Dict[Any, Dict[str, Any]]] = None

    @classmethod
    def setUpClass(cls):
        cls.OVERWRITE_OBJ__KV_MAP = cls.OVERWRITE_OBJ__KV_MAP or {}
        cls.OBJ__ORIGIN_KV_MAP = defaultdict(lambda: defaultdict(dict))

        super().setUpClass()

    @classmethod
    def setUpTestData(cls):
        for setting_obj, kv in cls.OVERWRITE_OBJ__KV_MAP.items():
            for k, v in kv.items():
                cls.OBJ__ORIGIN_KV_MAP[setting_obj][k] = getattr(setting_obj, k, None)
                setattr(setting_obj, k, v)
        super().setUpTestData()

    @classmethod
    def tearDownClass(cls):
        for setting_obj, origin_kv in cls.OBJ__ORIGIN_KV_MAP.items():
            for k, origin_value in origin_kv.items():
                setattr(setting_obj, k, origin_value)

        cls.OBJ__ORIGIN_KV_MAP = cls.OBJ__ORIGIN_KV_MAP = None
        super().tearDownClass()


class CustomBaseTestCase(AssertDataMixin, OverwriteSettingsMixin, TestCase):
    client_class = Client

    @property
    def request_factory(self):
        """按需加载request_factory"""
        if hasattr(self, "_request_factory"):
            return self._request_factory
        setattr(self, "_request_factory", RequestFactory())
        return self._request_factory


class CustomAPITestCase(CustomBaseTestCase):
    client_class = base.CustomAPIClient
