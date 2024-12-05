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
import abc
import copy
from unittest.mock import patch

from apps.exceptions import ValidationError
from apps.mock_data import utils
from apps.mock_data.common_unit import host
from apps.mock_data.views_mkd import job
from apps.node_man import constants
from apps.node_man.models import Host, IdentityData
from apps.node_man.tests.utils import MockClient, Subscription
from apps.utils.unittest.testcase import CustomAPITestCase, MockSuperUserMixin


class JobViewsTestCase(MockSuperUserMixin, CustomAPITestCase):
    @patch("apps.node_man.handlers.job.JobHandler.create_subscription", Subscription.create_subscription)
    def test_install(self):
        data = copy.deepcopy(job.JOB_INSTALL_REQUEST_PARAMS)
        result = self.client.post(path="/api/job/install/", data=data)
        self.assertEqual(result["result"], True)

    @patch("apps.node_man.handlers.job.JobHandler.create_subscription", Subscription.create_subscription)
    def test_operate(self):
        data = copy.deepcopy(job.JOB_OPERATE_REQUEST_PARAMS)
        result = self.client.post(path="/api/job/operate/", data=data)
        self.assertEqual(result["result"], True)


class JobViewsWithoutHostIdTestCase(MockSuperUserMixin, CustomAPITestCase):
    def setUp(self) -> None:
        Host.objects.update_or_create(
            defaults={
                "bk_cloud_id": constants.DEFAULT_CLOUD,
                "node_type": constants.NodeType.AGENT,
                "bk_biz_id": utils.DEFAULT_BK_BIZ_ID,
                "inner_ip": host.DEFAULT_IP,
            },
            bk_host_id=1,
        )
        return super().setUp()

    @patch("apps.node_man.handlers.job.JobHandler.create_subscription", Subscription.create_subscription)
    def test_operate(self):
        data = copy.deepcopy(job.JOB_OPERATE_REQUEST_PARAMS_WITHOUT_HOST_ID)
        result = self.client.post(path="/api/job/operate/", data=data)
        self.assertEqual(result["result"], True)


class TestJobValidationError(JobViewsTestCase, metaclass=abc.ABCMeta):
    ERROR_MSG_KEYWORD = ""

    @staticmethod
    def generate_install_job_request_params():
        data = copy.deepcopy(job.JOB_INSTALL_REQUEST_PARAMS)
        return data

    @patch("apps.node_man.handlers.job.JobHandler.create_subscription", Subscription.create_subscription)
    def test_install_raise_validation_error(self):
        data = self.generate_install_job_request_params()
        result = self.client.post(path="/api/job/install/", data=data)
        if self.ERROR_MSG_KEYWORD:
            self.assertEqual(result["code"], ValidationError().code)
            self.assertIn(self.ERROR_MSG_KEYWORD, result["message"])


class TestInnerIpNotEmptyAtTheSameTimeError(TestJobValidationError):
    ERROR_MSG_KEYWORD = "请求参数 inner_ip 和 inner_ipv6 不能同时为空"

    @staticmethod
    def generate_install_job_request_params():
        data = copy.deepcopy(job.JOB_INSTALL_REQUEST_PARAMS)
        data["hosts"][0]["inner_ip"] = ""
        data["hosts"][0]["inner_ipv6"] = ""
        return data


class TestOuterIpNotEmptyAtTheSameTimeError(TestJobValidationError):
    ERROR_MSG_KEYWORD = "Proxy 操作的请求参数 outer_ip 和 outer_ipv6 不能同时为空"

    @staticmethod
    def generate_install_job_request_params():
        data = copy.deepcopy(job.JOB_INSTALL_REQUEST_PARAMS)
        data["job_type"] = constants.JobType.INSTALL_PROXY
        data["hosts"][0]["outer_ip"] = ""
        data["hosts"][0]["outer_ipv6"] = ""
        return data


class TestHostInfoNotUpdateCase(MockSuperUserMixin, CustomAPITestCase):
    def setUp(self) -> None:
        Host.objects.update_or_create(
            defaults={
                "bk_cloud_id": constants.DEFAULT_CLOUD,
                "node_type": constants.NodeType.AGENT,
                "bk_biz_id": 100001,
                "inner_ip": host.DEFAULT_IP,
            },
            bk_host_id=14110,
        )
        identify_data = copy.deepcopy(host.IDENTITY_MODEL_DATA)
        identify_data["bk_host_id"] = 14110
        IdentityData.objects.create(**identify_data)
        return super().setUp()

    @patch("apps.node_man.handlers.job.JobHandler.create_subscription", Subscription.create_subscription)
    @patch("apps.node_man.periodic_tasks.sync_cmdb_host.client_v2", MockClient)
    def test_install(self):
        data = copy.deepcopy(job.JOB_REINSTALL_REQUEST_PARAMS)
        data["hosts"][0]["inner_ip"] = "2.1.2.52"

        response = self.client.post(path="/api/job/install/", data=data)
        # 成功创建安装任务
        self.assertEqual(response["result"], True)
        self.assertEqual(type(response["data"]["job_id"]), int)
