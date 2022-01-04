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

from apps.node_man import exceptions
from apps.node_man.constants import IamActionType
from apps.node_man.handlers.permission import (
    CloudPermission,
    DebugPermission,
    GlobalSettingPermission,
    InstallChannelPermission,
    PackagePermission,
    PolicyPermission,
)
from apps.node_man.tests.utils import SEARCH_BUSINESS, MockClient, create_host


def fetch_policy(*args, **kwargs):
    return {
        IamActionType.ap_edit: [0],
        IamActionType.ap_delete: [1],
        IamActionType.ap_create: 2,
        IamActionType.ap_view: [3],
        IamActionType.cloud_view: [4],
        IamActionType.cloud_edit: [5],
        IamActionType.cloud_delete: [6],
        IamActionType.cloud_create: 7,
        IamActionType.plugin_pkg_operate: [8],
        IamActionType.plugin_pkg_import: True,
        IamActionType.strategy_operate: [9],
        IamActionType.strategy_view: [biz["bk_biz_id"] for biz in SEARCH_BUSINESS],
        IamActionType.strategy_create: [biz["bk_biz_id"] for biz in SEARCH_BUSINESS],
    }


class view:
    action = "create"
    kwargs = {}

    def __init__(self, action="create", pk=1):
        self.action = action
        self.kwargs["pk"] = pk


class request:
    method = "POST"
    data = {"bk_cloud_id": 5, "id": [1], "scope": {"nodes": [{"bk_biz_id": 999}, {"bk_biz_id": 1000}]}}
    query_params = {"bk_host_id": 1}

    class user:
        username = ""

        def __init__(self, username=""):
            self.username = username


class TestPermission(TestCase):
    @patch("apps.node_man.handlers.permission.settings.USE_IAM", True)
    @patch("apps.node_man.handlers.permission.IamHandler.fetch_policy", fetch_policy)
    def test_global_settings_permissions(self):
        """
        测试全局配置权限控制
        """
        # 测试鉴权成功
        result = GlobalSettingPermission().has_permission(request, view)
        self.assertTrue(result)

        # 测试鉴权失败
        result = GlobalSettingPermission().has_permission(request, view("update"))
        self.assertFalse(result)

    @patch("apps.node_man.handlers.permission.settings.USE_IAM", True)
    @patch("apps.node_man.handlers.permission.IamHandler.fetch_policy", fetch_policy)
    def test_cloud_permissions(self):
        """
        测试云区域权限控制
        """
        # 测试鉴权成功
        result = CloudPermission().has_permission(request, view)
        self.assertTrue(result)

        # 测试鉴权失败
        result = CloudPermission().has_permission(request, view("update"))
        self.assertFalse(result)

    @patch("apps.node_man.handlers.permission.settings.USE_IAM", True)
    @patch("apps.node_man.handlers.permission.IamHandler.fetch_policy", fetch_policy)
    def test_install_channel_permissions(self):
        """
        测试安装通道权限控制
        """
        # 测试鉴权成功
        result = InstallChannelPermission().has_permission(request, view)
        self.assertTrue(result)

    @patch("apps.node_man.handlers.permission.settings.USE_IAM", True)
    @patch("apps.node_man.handlers.permission.IamHandler.fetch_policy", fetch_policy)
    def test_debug_permissions(self):
        """
        测试Debug接口权限控制
        """
        # 测试鉴权失败
        result = DebugPermission().has_permission(request, view)
        self.assertFalse(result)

    @patch("apps.node_man.handlers.permission.settings.USE_IAM", True)
    @patch("apps.node_man.handlers.permission.IamHandler.fetch_policy", fetch_policy)
    def test_package_permissions(self):
        """
        测试插件包权限控制
        """
        # 测试鉴权成功
        result = PackagePermission().has_permission(request, view("upload"))
        self.assertTrue(result)
        result = PackagePermission().has_permission(request, view("update", 8))
        self.assertTrue(result)

        # 测试鉴权失败
        result = PackagePermission().has_permission(request, view("plugin_status_operation"))
        self.assertFalse(result)

        # 测试无鉴权
        result = PackagePermission().has_permission(request, view("history"))
        self.assertTrue(result)

    @patch("apps.node_man.handlers.permission.settings.USE_IAM", True)
    @patch("apps.node_man.handlers.permission.IamHandler.fetch_policy", fetch_policy)
    @patch("apps.node_man.handlers.cmdb.IamHandler.fetch_policy", fetch_policy)
    @patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
    def test_policy_permissions(self):
        """
        测试策略权限控制
        """
        # 测试无鉴权
        result = PolicyPermission().has_permission(request, view("fetch_common_variable"))
        self.assertTrue(result)

        # 测试鉴权失败
        result = PolicyPermission().has_permission(request, view("update"))
        self.assertFalse(result)

        # 测试鉴权host_policy
        _ = create_host(number=1, bk_host_id=1)[0]
        result = PolicyPermission().has_permission(request, view("host_policy"))
        self.assertTrue(result)

        # 测试鉴权create_policy
        self.assertRaises(
            exceptions.BusinessNotPermissionError, PolicyPermission().has_permission, request, view("create_policy")
        )
