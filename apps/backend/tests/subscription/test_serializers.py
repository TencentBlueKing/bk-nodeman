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

from types import SimpleNamespace

import mock
from django.test import SimpleTestCase, override_settings

from apps.backend.subscription import errors, serializers
from apps.exceptions import ValidationError
from apps.node_man import models
from apps.utils import local


@override_settings(ENABLE_MULTI_TENANT_MODE=True)
class TaskResultSerializerTenantValidationTestCase(SimpleTestCase):
    subscription_id = 1
    request_tenant_id = "tenant-request"
    other_tenant_id = "tenant-other"

    def setUp(self):
        local.set_tenant_id(self.request_tenant_id)

    def tearDown(self):
        local.set_tenant_id("default")

    def build_serializer(self, need_out_of_scope_snapshots):
        return serializers.TaskResultSerializer(
            data={
                "bk_username": "tester",
                "bk_app_code": "test-app",
                "subscription_id": self.subscription_id,
                "need_out_of_scope_snapshots": need_out_of_scope_snapshots,
            }
        )

    @mock.patch.object(models.Subscription.objects, "get")
    def test_active_subscription_uses_default_manager_scope(self, mocked_get):
        mocked_get.return_value = SimpleNamespace(tenant_id=self.request_tenant_id)

        serializer = self.build_serializer(need_out_of_scope_snapshots=False)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        mocked_get.assert_called_once_with(id=self.subscription_id)

    @mock.patch.object(models.Subscription.objects, "get")
    def test_out_of_scope_snapshots_use_deleted_aware_lookup(self, mocked_get):
        mocked_get.return_value = SimpleNamespace(tenant_id=self.request_tenant_id)

        serializer = self.build_serializer(need_out_of_scope_snapshots=True)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        mocked_get.assert_called_once_with(id=self.subscription_id, show_deleted=True)

    @mock.patch.object(models.Subscription.objects, "get")
    def test_out_of_scope_snapshots_default_uses_deleted_aware_lookup(self, mocked_get):
        mocked_get.return_value = SimpleNamespace(tenant_id=self.request_tenant_id)
        serializer = serializers.TaskResultSerializer(
            data={
                "bk_username": "tester",
                "bk_app_code": "test-app",
                "subscription_id": self.subscription_id,
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        mocked_get.assert_called_once_with(id=self.subscription_id, show_deleted=True)

    @mock.patch.object(models.Subscription.objects, "get")
    def test_active_cross_tenant_subscription_fails_closed(self, mocked_get):
        mocked_get.return_value = SimpleNamespace(tenant_id=self.other_tenant_id)

        serializer = self.build_serializer(need_out_of_scope_snapshots=False)

        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)

    @mock.patch.object(models.Subscription.objects, "get")
    def test_deleted_cross_tenant_subscription_fails_closed(self, mocked_get):
        mocked_get.return_value = SimpleNamespace(tenant_id=self.other_tenant_id)

        serializer = self.build_serializer(need_out_of_scope_snapshots=True)

        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)

    @mock.patch.object(models.Subscription.objects, "get")
    def test_hidden_subscription_is_rejected_without_out_of_scope_snapshots(self, mocked_get):
        mocked_get.side_effect = models.Subscription.DoesNotExist

        serializer = self.build_serializer(need_out_of_scope_snapshots=False)

        with self.assertRaises(errors.SubscriptionNotExist):
            serializer.is_valid(raise_exception=True)
        mocked_get.assert_called_once_with(id=self.subscription_id)

    @mock.patch.object(models.Subscription.objects, "get")
    def test_nonexistent_subscription_fails_closed_with_deleted_aware_lookup(self, mocked_get):
        mocked_get.side_effect = models.Subscription.DoesNotExist

        serializer = self.build_serializer(need_out_of_scope_snapshots=True)

        with self.assertRaises(errors.SubscriptionNotExist):
            serializer.is_valid(raise_exception=True)
        mocked_get.assert_called_once_with(id=self.subscription_id, show_deleted=True)

    @override_settings(ENABLE_MULTI_TENANT_MODE=False)
    @mock.patch.object(models.Subscription.objects, "get")
    def test_non_multi_tenant_mode_does_not_query_subscription(self, mocked_get):
        serializer = self.build_serializer(need_out_of_scope_snapshots=True)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        mocked_get.assert_not_called()
