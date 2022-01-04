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

from apps.node_man.constants import IamActionType
from apps.node_man.handlers.iam import IamHandler
from apps.utils.unittest.testcase import CustomBaseTestCase

from .utils import MockIAM, create_cloud_area


class TestIAM(CustomBaseTestCase):
    resource_num = 10

    def init_db(self):
        """创建测试数据"""
        create_cloud_area(number=self.resource_num, creator="creator")

    @patch("apps.node_man.handlers.iam.IamHandler._iam", MockIAM)
    @patch("apps.node_man.handlers.iam.settings.USE_IAM", True)
    def test_fetch_policy(self):
        self.init_db()

        # 测试超级用户
        ret = IamHandler().fetch_policy("admin", [IamActionType.cloud_edit])
        self.assertEqual(len(ret[IamActionType.cloud_edit]), self.resource_num)

        # 测试创建者
        ret = IamHandler().fetch_policy("creator", [IamActionType.cloud_edit])
        self.assertEqual(len(ret[IamActionType.cloud_edit]), self.resource_num)

        # 测试拥有any权限的用户
        ret = IamHandler().fetch_policy("normal_any", [IamActionType.cloud_view, IamActionType.cloud_edit])
        self.assertEqual(len(ret[IamActionType.cloud_view]), self.resource_num)
        self.assertEqual(len(ret[IamActionType.cloud_edit]), 0)

        # 测试拥有部分权限的用户
        ret = IamHandler().fetch_policy("normal_in", [IamActionType.agent_view, IamActionType.ap_view])
        self.assertGreater(len(ret[IamActionType.agent_view]), 1)
        self.assertGreater(len(ret[IamActionType.ap_view]), 1)

        # 测试拥有单个权限的用户
        ret = IamHandler().fetch_policy("normal_eq", [IamActionType.plugin_view, IamActionType.strategy_view])
        self.assertEqual(len(ret[IamActionType.plugin_view]), 1)
        self.assertEqual(len(ret[IamActionType.strategy_view]), 1)

        # 测试无权限用户
        ret = IamHandler().fetch_policy("abnormal_eq", [IamActionType.globe_task_config])
        self.assertEqual(ret[IamActionType.globe_task_config], False)

    @patch("apps.node_man.handlers.iam.IamHandler._iam", MockIAM)
    @patch("apps.node_man.handlers.iam.settings.USE_IAM", True)
    def test_fetch_redirect_url(self):
        # 测试无资源关联跳转url
        apply_info_list = [{"action": IamActionType.plugin_pkg_import}]
        ret = IamHandler().fetch_redirect_url(apply_info_list, "admin")
        self.assertEqual(ret, "127.0.0.1/without_resource")

        # 测试有资源关联跳转url
        apply_info_list = [{"action": IamActionType.agent_view, "instance_id": 1, "instance_name": "host"}]
        ret = IamHandler().fetch_redirect_url(apply_info_list, "admin")
        self.assertEqual(ret, "127.0.0.1/with_resource")

    @patch("apps.node_man.handlers.iam.IamHandler._iam", MockIAM)
    def test_fetch_policy_without_use_iam(self):
        self.init_db()

        # 测试超级用户
        ret = IamHandler().fetch_policy("admin", [IamActionType.cloud_edit])
        self.assertEqual(len(ret[IamActionType.cloud_edit]), self.resource_num)

        # 测试无权限用户
        ret = IamHandler().fetch_policy("normal", [IamActionType.ap_edit])
        self.assertEqual(len(ret[IamActionType.ap_edit]), 0)
