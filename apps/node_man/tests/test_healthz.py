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
from unittest.mock import patch

from django.test import TestCase

from apps.node_man.handlers.healthz.handler import HealthzHandler
from apps.node_man.handlers.healthz.saas_healthz import (
    CcHealthzChecker,
    GseHealthzChecker,
    JobHealthzChecker,
    MysqlHealthzChecker,
    NodemanHealthzChecker,
)
from apps.node_man.tests.utils import GseApi, JobApi, MockClient, NodeApi

CHECKER_NAME__INSTANCE_MAP = {
    "cmdb": CcHealthzChecker(),
    "job": JobHealthzChecker(),
    "nodeman": NodemanHealthzChecker(),
    "gse": GseHealthzChecker(),
    "mysql": MysqlHealthzChecker(),
}


def check_result(*args, **kwargs):
    class result:
        @classmethod
        def as_json(cls):
            return '{"value": ""}'

    def check(*args, **kwargs):
        return result

    return check


def get_request():
    class request:
        biz_id = 1

        class user:
            username = "admin"

    return request


class TestHealthz(TestCase):
    @patch("apps.node_man.handlers.healthz.handler.NodeApi.metric_list", NodeApi.metric_list)
    def test_process(self):
        result = HealthzHandler().list_metrics()
        metric_result = [info["metric_alias"] for info in result]
        self.assertEqual(metric_result, ["cmdb.status", "job.status", "nodeman.status", "gse.status"])

    @patch("apps.node_man.handlers.healthz.saas_healthz.get_request", get_request)
    @patch("apps.node_man.handlers.healthz.handler.NodeApi.metric_list", NodeApi.metric_list)
    @patch("apps.node_man.handlers.healthz.saas_healthz.NodeApi", NodeApi)
    @patch("apps.node_man.handlers.healthz.saas_healthz.JobApi", JobApi)
    @patch("apps.node_man.handlers.healthz.saas_healthz.GseApi", GseApi)
    @patch("apps.node_man.handlers.healthz.saas_healthz.client_v2", MockClient)
    def test_api(self):
        checker_info_list = HealthzHandler().list_metrics()
        checker_api_result = defaultdict(list)

        for checker_info in checker_info_list:
            checker_name = checker_info["node_name"]
            checker = CHECKER_NAME__INSTANCE_MAP[checker_name]
            api_list = checker_info["result"]["api_list"]

            # 获得api的执行结果
            for api in api_list:
                res, method, msg, args, data = checker.test_root_api(api["api_name"])
                api_result = {"result": res, "method_name": method, "message": msg, "args": args, **data}

                # 获得children_api的结果，如果没有children_api，则传入错误参数来验证执行结果
                children_api_result_list = []
                if not api["children_api_list"]:
                    api["children_api_list"].append({"api_name": "test", "args": {}})

                for children_api in api["children_api_list"]:
                    res, api_name, parent_api, msg, args, data = checker.test_non_root_api(
                        children_api["api_name"], api["api_name"], children_api["args"]
                    )
                    children_api_result_list.append(
                        {
                            "result": res,
                            "api_name": api_name,
                            "parent_api": parent_api,
                            "msg": msg,
                            "args": args,
                            "data": data,
                        }
                    )

                api_result.update({"children_api_result_list": children_api_result_list})
                checker_api_result[checker_name].append(api_result)

        for node_name, api_result_list in checker_api_result.items():
            for api_result in api_result_list:
                self.assertEqual(api_result["result"], True & (node_name != "job"))
                for children_api_result in api_result["children_api_result_list"]:
                    self.assertEqual(children_api_result["result"], False | (node_name == "job"))
