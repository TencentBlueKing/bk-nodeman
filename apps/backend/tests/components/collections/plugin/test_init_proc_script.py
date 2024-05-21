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
import os

import mock
from mock.mock import patch

from apps.backend.api.job import process_parms
from apps.backend.components.collections.common.script_content import INITIALIZE_SCRIPT
from apps.backend.components.collections.plugin import InitProcOperateScriptComponent
from apps.backend.tests.components.collections.plugin.test_install_package import (
    InstallPackageTest,
)
from apps.backend.tests.components.collections.plugin.utils import (
    JOB_INSTANCE_ID,
    PluginTestObjFactory,
)
from apps.mock_data import api_mkd
from apps.mock_data import utils as mock_data_utils
from apps.node_man import models
from pipeline.component_framework.test import (
    ComponentTestCase,
    ExecuteAssertion,
    ScheduleAssertion,
)


class InitProcOperateScriptTest(InstallPackageTest):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "测试初始化插件操作脚本"

    def component_cls(self):
        return InitProcOperateScriptComponent

    def cases(self):
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=True,
                    outputs={"succeeded_subscription_instance_ids": [self.ids["subscription_instance_record_id"]]},
                ),
                schedule_assertion=ScheduleAssertion(
                    success=True,
                    schedule_finished=True,
                    outputs={
                        "succeeded_subscription_instance_ids": [self.ids["subscription_instance_record_id"]],
                        "polling_time": 5,
                    },
                    callback_data=[],
                ),
                execute_call_assertion=None,
            )
        ]


class InitProcOperateInTmpDir(InitProcOperateScriptTest):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "【下发脚本】到临时路径"

    def test_component(self):
        with patch(
            "apps.backend.tests.components.collections.plugin.utils.JobMockClient.fast_execute_script"
        ) as fast_execute_script:
            fast_execute_script.return_value = {
                "job_instance_name": "API Quick execution script1521100521303",
                "job_instance_id": JOB_INSTANCE_ID,
            }
            super().test_component()

            # 验证脚本参数
            file_target_path = os.path.join("/usr/local/gse", "plugins", "bin")
            self.assertEqual(
                process_parms(f"/tmp/plugin_scripts_sub_{self.ids['subscription_id']} {file_target_path}"),
                fast_execute_script.call_args[0][0]["script_param"],
            )

            # 验证脚本内容
            self.assertEqual(
                process_parms(INITIALIZE_SCRIPT),
                fast_execute_script.call_args[0][0]["script_content"],
            )


class InstallPluginWhenHostDoesNotExist(InitProcOperateScriptTest):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "主机不存在时【安装插件】"

    @property
    def list_biz_hosts(self):
        host_params = PluginTestObjFactory.host_obj()
        host_params["bk_host_innerip"] = host_params["inner_ip"]
        return {
            "count": 1,
            "info": [host_params],
        }

    def init_mock_clients(self):
        self.cmdb_mock_client = api_mkd.cmdb.utils.CCApiMockClient(
            list_biz_hosts_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.RETURN_VALUE.value, return_obj=self.list_biz_hosts
            ),
        )

    def start_patch(self):
        mock.patch("apps.component.esbclient.client_v2.cc", self.cmdb_mock_client).start()

    def adjust_data(self):
        # 填充meta信息
        self.COMMON_INPUTS["meta"] = {
            "GSE_VERSION": "V2",
            "STEPS": [
                {
                    "action": "MAIN_INSTALL_PLUGIN",
                    "extra_info": {},
                    "id": "bkmonitorbeat",
                    "index": 0,
                    "node_name": "[bkmonitorbeat] 部署插件程序",
                    "pipeline_id": "xxxxxxxxxxxxxxxxx",
                    "type": "PLUGIN",
                }
            ],
        }

        # 主机删除
        models.Host.objects.all().delete()

    def setUp(self):
        super().setUp()
        self.init_mock_clients()
        self.start_patch()
        self.adjust_data()


class ReloadPluginWhenHostDoesNotExist(InstallPluginWhenHostDoesNotExist):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "主机不存在时【重载插件】"

    def adjust_data(self):
        super().adjust_data()
        self.COMMON_INPUTS["meta"] = {
            "GSE_VERSION": "V2",
            "STEPS": [
                {
                    "action": "MAIN_RELOAD_PLUGIN",
                    "extra_info": {},
                    "id": "bkmonitorbeat",
                    "index": 0,
                    "node_name": "[bkmonitorbeat] 重载插件",
                    "pipeline_id": "xxxxxxxxxxxxxxxxx",
                    "type": "PLUGIN",
                }
            ],
        }

    def _do_case_assert(self, service, method, assertion, no, name, args=None, kwargs=None):
        try:
            super()._do_case_assert(service, method, assertion, no, name, args, kwargs)
        except AssertionError:
            self.assertEqual(
                list(service.failed_subscription_instance_id_reason_map.keys()),
                self.COMMON_INPUTS["subscription_instance_ids"],
            )

            self.assertEqual(
                list(service.failed_subscription_instance_id_reason_map.values()),
                ["主机不存在或未同步"],
            )
