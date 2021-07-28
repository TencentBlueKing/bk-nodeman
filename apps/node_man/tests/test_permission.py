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
from unittest.mock import patch

from django.test import TestCase

from apps.node_man.constants import IamActionType
from apps.node_man.handlers.permission import CloudPermission, GlobalSettingPermission


def fetch_policy(*args, **kwargs):
    return {
        IamActionType.ap_edit: 0,
        IamActionType.ap_delete: 1,
        IamActionType.ap_create: 2,
        IamActionType.ap_view: 3,
        IamActionType.cloud_view: 4,
        IamActionType.cloud_edit: 5,
        IamActionType.cloud_delete: 6,
        IamActionType.cloud_create: 7,
    }


class view:
    action = "create"


class request:
    class user:
        username = ""


class TestPermission(TestCase):
    @patch("apps.node_man.handlers.permission.settings.USE_IAM", True)
    @patch("apps.node_man.handlers.permission.IamHandler.fetch_policy", fetch_policy)
    def test_global_settings_permissions(self):
        result = GlobalSettingPermission().has_permission(request, view)
        self.assertTrue(result)

    @patch("apps.node_man.handlers.permission.settings.USE_IAM", True)
    @patch("apps.node_man.handlers.permission.IamHandler.fetch_policy", fetch_policy)
    def test_cloud_permissions(self):
        result = CloudPermission().has_permission(request, view)
        self.assertTrue(result)

    @patch("apps.node_man.handlers.permission.settings.USE_IAM", True)
    @patch("apps.node_man.handlers.permission.IamHandler.fetch_policy", fetch_policy)
    def test_debug_permissions(self):
        result = CloudPermission().has_permission(request, view)
        self.assertTrue(result)
