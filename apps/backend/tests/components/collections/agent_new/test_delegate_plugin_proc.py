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
from collections import ChainMap
from typing import Any, Dict, List, Optional

import mock

from apps.backend.api.constants import POLLING_INTERVAL, GseDataErrCode
from apps.backend.components.collections.agent_new import components
from apps.mock_data import api_mkd, common_unit
from apps.mock_data import utils as mock_data_utils
from apps.node_man import constants, models
from apps.utils import basic
from pipeline.component_framework.test import (
    ComponentTestCase,
    ExecuteAssertion,
    ScheduleAssertion,
)

from . import utils


class DelegatePluginProcTestCase(utils.AgentServiceBaseTestCase):

    GSE_API_MOCK_PATHS: List[str] = ["apps.backend.components.collections.agent_new.delegate_plugin_proc.GseApi"]

    proc_name: Optional[str] = None
    operate_proc_result: Optional[Dict] = None
    update_proc_info_result: Optional[Dict] = None
    get_proc_operate_result: Optional[Dict] = None
    gse_api_mock_client: Optional[api_mkd.gse.utils.GseApiMockClient] = None

    @classmethod
    def get_gse_proc_key(cls, host_obj: models.Host, add_supplier_id: bool = False) -> str:
        suffix = f"{host_obj.inner_ip}:{constants.GSE_NAMESPACE}:{cls.proc_name}"

        if add_supplier_id:
            return f"{host_obj.bk_cloud_id}:{constants.DEFAULT_SUPPLIER_ID}:{suffix}"
        else:
            return f"{host_obj.bk_cloud_id}:{suffix}"

    @classmethod
    def structure_gse_mock_data(cls):
        """
        构造GSE接口返回数据
        :return:
        """

        cls.update_proc_info_result = {
            cls.get_gse_proc_key(host_obj, add_supplier_id=True): {
                "content": "",
                "error_code": GseDataErrCode.SUCCESS,
                "error_msg": "success",
            }
            for host_obj in cls.obj_factory.host_objs
        }
        cls.get_proc_operate_result = {
            "result": True,
            "code": GseDataErrCode.SUCCESS,
            "message": "",
            "data": {
                cls.get_gse_proc_key(host_obj, add_supplier_id=False): {
                    "content": "",
                    "error_code": GseDataErrCode.SUCCESS,
                    "error_msg": "success",
                }
                for host_obj in cls.obj_factory.host_objs
            },
        }
        cls.operate_proc_result = api_mkd.gse.unit.OP_RESULT

    @classmethod
    def adjust_test_data_in_db(cls):

        cls.proc_name = common_unit.plugin.PLUGIN_NAME
        os_types = {host_obj.os_type for host_obj in cls.obj_factory.host_objs}
        for os_type in os_types:
            package_data = basic.remove_keys_from_dict(origin_data=common_unit.plugin.PACKAGES_MODEL_DATA, keys=["id"])
            package_data.update({"cpu_arch": constants.CpuType.x86_64, "os": os_type.lower()})

            package_obj = models.Packages(**package_data)
            package_obj.save()

            proc_control_data = basic.remove_keys_from_dict(
                origin_data=common_unit.plugin.PROC_CONTROL_MODEL_DATA, keys=["id", "plugin_package_id"]
            )
            proc_control_data.update({"plugin_package_id": package_obj.id, "os": package_obj.os})
            proc_control_obj = models.ProcControl(**proc_control_data)
            proc_control_obj.save()

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # 初始化DB数据后再修改
        cls.adjust_test_data_in_db()
        cls.structure_gse_mock_data()

    @classmethod
    def get_default_case_name(cls) -> str:
        return "托管插件进程成功"

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        return self.common_inputs["subscription_instance_ids"]

    def component_cls(self):
        return components.DelegatePluginProcComponent

    def init_mock_clients(self):
        self.gse_api_mock_client = api_mkd.gse.utils.GseApiMockClient(
            update_proc_info_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.RETURN_VALUE.value, return_obj=self.update_proc_info_result
            ),
            get_proc_operate_result_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.RETURN_VALUE.value, return_obj=self.get_proc_operate_result
            ),
            operate_proc_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.RETURN_VALUE.value, return_obj=self.operate_proc_result
            ),
        )

    def structure_common_inputs(self) -> Dict[str, Any]:
        common_inputs = super().structure_common_inputs()
        return {**common_inputs, "plugin_name": common_unit.plugin.PLUGIN_NAME}

    def structure_common_outputs(self) -> Dict[str, Any]:
        return {
            "polling_time": 0,
            "proc_name": self.proc_name,
            "task_id": self.operate_proc_result["task_id"],
            "succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids(),
        }

    def setUp(self) -> None:
        self.init_mock_clients()
        for gse_api_mock_path in self.GSE_API_MOCK_PATHS:
            mock.patch(gse_api_mock_path, self.gse_api_mock_client).start()
        super().setUp()

    def cases(self):
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=bool(self.fetch_succeeded_sub_inst_ids()), outputs=self.structure_common_outputs()
                ),
                schedule_assertion=[
                    ScheduleAssertion(success=True, schedule_finished=True, outputs=self.structure_common_outputs()),
                ],
                execute_call_assertion=None,
            )
        ]


class NotSupportOsTestCase(DelegatePluginProcTestCase):

    REMOVE_PACKAGES = True

    @classmethod
    def adjust_test_data_in_db(cls):
        super().adjust_test_data_in_db()
        if cls.REMOVE_PACKAGES:
            models.Packages.objects.filter(project=common_unit.plugin.PLUGIN_NAME).delete()

    @classmethod
    def get_default_case_name(cls) -> str:
        return "操作系统不支持"

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        return []

    def cases(self):
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=bool(self.fetch_succeeded_sub_inst_ids()),
                    # 操作系统不支持时，task_id 等数据还未写入outputs
                    outputs={"succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids()},
                ),
                schedule_assertion=None,
                execute_call_assertion=None,
            )
        ]


class UpdateResultNotFoundTestCase(NotSupportOsTestCase):

    REMOVE_PACKAGES = False

    @classmethod
    def get_default_case_name(cls) -> str:
        return "未能查询到进程更新结果"

    @classmethod
    def structure_gse_mock_data(cls):
        """
        构造GSE接口返回数据
        :return:
        """
        super().structure_gse_mock_data()
        # 更新插件进程信息接口置空
        cls.update_proc_info_result = {}


class OpProcResultNotFoundTestCase(DelegatePluginProcTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "未能查询到进程操作结果"

    @classmethod
    def structure_gse_mock_data(cls):
        """
        构造GSE接口返回数据
        :return:
        """
        super().structure_gse_mock_data()
        # 更新插件进程信息接口置空
        cls.get_proc_operate_result["data"] = {}

    def cases(self):
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=bool(self.fetch_succeeded_sub_inst_ids()), outputs=self.structure_common_outputs()
                ),
                schedule_assertion=[
                    ScheduleAssertion(
                        success=False,
                        schedule_finished=True,
                        outputs=dict(
                            ChainMap({"succeeded_subscription_instance_ids": []}, self.structure_common_outputs())
                        ),
                    ),
                ],
                execute_call_assertion=None,
            )
        ]


class OpProcResultErrorTestCase(OpProcResultNotFoundTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "GSE进程操作错误"

    @classmethod
    def structure_gse_mock_data(cls):
        """
        构造GSE接口返回数据
        :return:
        """
        super().structure_gse_mock_data()
        # 更新插件进程信息接口置空
        cls.get_proc_operate_result["data"] = {
            cls.get_gse_proc_key(host_obj, add_supplier_id=False): {
                "content": "",
                "error_code": GseDataErrCode.AGENT_ABNORMAL,
                "error_msg": f"can not find connection by ip {host_obj.inner_ip}",
            }
            for host_obj in cls.obj_factory.host_objs
        }


class TimeOutTestCase(DelegatePluginProcTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "GSE操作结果查询超时"

    @classmethod
    def structure_gse_mock_data(cls):
        """
        构造GSE接口返回数据
        :return:
        """
        super().structure_gse_mock_data()
        # 更新插件进程信息接口置空
        cls.get_proc_operate_result["data"] = {
            cls.get_gse_proc_key(host_obj, add_supplier_id=False): {
                "content": "",
                "error_code": GseDataErrCode.RUNNING,
                "error_msg": "running",
            }
            for host_obj in cls.obj_factory.host_objs
        }

    def setUp(self) -> None:
        super().setUp()
        mock.patch(
            "apps.backend.components.collections.agent_new.delegate_plugin_proc.POLLING_TIMEOUT",
            2 * POLLING_INTERVAL - 1,
        ).start()

    def cases(self):
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=bool(self.fetch_succeeded_sub_inst_ids()), outputs=self.structure_common_outputs()
                ),
                schedule_assertion=[
                    ScheduleAssertion(
                        success=True,
                        schedule_finished=False,
                        outputs=dict(ChainMap({"polling_time": POLLING_INTERVAL}, self.structure_common_outputs())),
                    ),
                    ScheduleAssertion(
                        success=False,
                        schedule_finished=False,
                        outputs=dict(
                            ChainMap(
                                {"succeeded_subscription_instance_ids": [], "polling_time": POLLING_INTERVAL * 2},
                                self.structure_common_outputs(),
                            )
                        ),
                    ),
                ],
                execute_call_assertion=None,
            )
        ]
