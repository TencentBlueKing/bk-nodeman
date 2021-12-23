# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making 蓝鲸 (Blueking) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""
from unittest.mock import patch

from django.conf import settings
from iam import IAM, DummyIAM, MultiActionRequest, Request, Resource
from iam.apply.models import Application

from apps.iam import ActionEnum, Permission
from apps.iam.handlers.resources import ResourceEnum
from apps.utils.unittest import testcase


class TestPermission(testcase.CustomBaseTestCase):
    def setUp(self) -> None:
        self.permission = Permission("admin")
        self.resource = ResourceEnum.BUSINESS.create_instance([1])
        self.action = ActionEnum.VIEW_BUSINESS

    def test_get_dummy_iam_client(self):
        iam_client = Permission("admin").get_iam_client()
        self.assertIsInstance(iam_client, DummyIAM)

    @patch("apps.node_man.handlers.iam.settings.BK_IAM_SKIP", False)
    def test_get_iam_client(self):
        iam_client = Permission("admin").get_iam_client()
        self.assertIsInstance(iam_client, IAM)

    def test_make_request(self):
        request = self.permission.make_request(self.action, [self.resource])
        self.assertIsInstance(request, Request)

    def test_make_multi_action_request(self):
        request = self.permission.make_multi_action_request([self.action], [self.resource])
        self.assertIsInstance(request, MultiActionRequest)

    def test_make_application(self):
        application = self.permission._make_application([self.action.id], [self.resource])
        self.assertIsInstance(application, Application)

    def test_get_apply_url(self):
        url = self.permission.get_apply_url([self.action.id], [self.resource])
        self.assertEqual(url, settings.BK_IAM_SAAS_HOST)

    def test_get_apply_data(self):
        data, url = self.permission.get_apply_data([self.action.id], [])
        self.assertEqual(url, settings.BK_IAM_SAAS_HOST)

    def test_is_allowed(self):
        result = self.permission.is_allowed(self.action.id, [])
        self.assertTrue(result)

    def test_batch_is_allowed(self):
        result = self.permission.batch_is_allowed([self.action.id], [])
        self.assertEqual(result, {})

    def test_make_resource(self):
        resource = self.permission.make_resource(self.resource.type, self.resource.id)
        self.assertIsInstance(resource, Resource)

    def test_batch_make_resource(self):
        resources = self.permission.batch_make_resource([self.resource.to_dict()])
        self.assertIsInstance(resources[0], Resource)

    def test_setup_meta(self):
        self.permission.setup_meta()
