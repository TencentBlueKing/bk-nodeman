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
import typing
from copy import deepcopy

import mock

from apps.backend.constants import ActionNameType, InstNodeType, PluginMigrateType
from apps.backend.subscription import tools
from apps.backend.subscription.steps import StepFactory
from apps.backend.tests.components.collections.plugin import utils
from apps.mock_data import api_mkd
from apps.mock_data import utils as mock_data_utils
from apps.mock_data.common_unit.host import PROCESS_STATUS_MODEL_DATA
from apps.node_man import constants, models
from apps.utils import concurrent
from apps.utils.unittest.testcase import CustomAPITestCase


class CmdbHandler(object):
    @staticmethod
    def list_biz_ids_in_biz_set(*args, **kwargs):
        return list(set([bk_biz_info["bk_biz_id"] for bk_biz_info in utils.CORRECT_BIZ_SET_BIZ_INFO]))


class MigrateCmdbBase(abc.ABC):
    @staticmethod
    def _get_search_biz_inst_topo_return(params):
        raise NotImplementedError

    @staticmethod
    def _get_get_biz_internal_module_return(params):
        raise NotImplementedError

    @staticmethod
    def get_get_mainline_object_topo_return(*args):
        # 主线 TOPO 无需关注
        return [
            {
                "bk_obj_id": "biz",
                "bk_obj_name": "Business",
                "bk_supplier_account": "0",
                "bk_next_obj": "set",
                "bk_next_name": "Set",
                "bk_pre_obj_id": "",
                "bk_pre_obj_name": "",
            },
            {
                "bk_obj_id": "set",
                "bk_obj_name": "Set",
                "bk_supplier_account": "0",
                "bk_next_obj": "module",
                "bk_next_name": "Module",
                "bk_pre_obj_id": "biz",
                "bk_pre_obj_name": "Business",
            },
            {
                "bk_obj_id": "module",
                "bk_obj_name": "Module",
                "bk_supplier_account": "0",
                "bk_next_obj": "host",
                "bk_next_name": "Host",
                "bk_pre_obj_id": "set",
                "bk_pre_obj_name": "Set",
            },
            {
                "bk_obj_id": "host",
                "bk_obj_name": "Host",
                "bk_supplier_account": "0",
                "bk_next_obj": "",
                "bk_next_name": "",
                "bk_pre_obj_id": "module",
                "bk_pre_obj_name": "Module",
            },
        ]

    @staticmethod
    def _find_host_by_topo(bk_host_ids: typing.List[int]):
        info = [{"bk_cloud_id": 0, "bk_host_id": bk_host_id} for bk_host_id in bk_host_ids]
        return {"count": len(bk_host_ids), "info": info}

    @staticmethod
    def search_business_return(*args, **kwargs):
        info = [
            {"bk_biz_id": info["bk_biz_id"], "bk_biz_name": info["bk_biz_name"], "default": 0}
            for info in utils.CORRECT_BIZ_SET_BIZ_INFO + utils.OTHER_BIZ_SET_BIZ_INFO
        ]
        return {"count": len(info), "info": info}


class SubMigrateBaseTestCase(utils.PluginTestObjFactory, CustomAPITestCase, MigrateCmdbBase):

    SCOPE_TYPE = constants.SubscriptionType.POLICY

    @classmethod
    def _get_subscription_params(cls):
        init_subscription_param = deepcopy(utils.SUBSCRIPTION_PARAMS)
        init_subscription_param["nodes"] = [{"bk_obj_id": InstNodeType.BIZ_SET, "bk_inst_id": utils.CORRECT_BIZ_SET_ID}]

        init_subscription_param["node_type"] = models.Subscription.NodeType.TOPO
        init_subscription_param["scope_type"] = models.Subscription.ScopeType.BIZ_SET
        init_subscription_param["categary"] = cls.SCOPE_TYPE
        return init_subscription_param

    @staticmethod
    def _get_get_biz_internal_module_return(params):
        # 空闲机 等模块应该 ID 是固定的，不需要关注
        bk_biz_id: int = params["bk_biz_id"]
        return {
            "bk_set_id": bk_biz_id,
            "bk_set_name": "idle pool",
            "module": [
                {"bk_module_id": 3, "bk_module_name": "idle host", "default": 1, "host_apply_enabled": True},
                {"bk_module_id": 4, "bk_module_name": "fault host", "default": 2, "host_apply_enabled": False},
                {"bk_module_id": 6, "bk_module_name": "recycle host", "default": 3, "host_apply_enabled": False},
            ],
        }

    def get_list_biz_hosts_return(self, *args, **kwargs):
        bk_host_ids = [self.sub_infos["bk_host_id"]]
        info = [
            {
                "bk_addressing": "static",
                "bk_agent_id": f"02000000005254000b102a1691498886573{index}",
                "bk_bak_operator": "admin",
                "bk_cloud_id": constants.DEFAULT_CLOUD,
                "bk_cpu_architecture": "x86",
                "bk_cpu_module": "AMD EPYC 7K83 64-Core Processor",
                "bk_host_id": bk_host_id,
                "bk_host_innerip": "127.0.0.29",
                "bk_host_innerip_v6": "",
                "bk_host_name": "VM-6-29-centos",
                "bk_host_outerip": "",
                "bk_host_outerip_v6": "",
                "bk_isp_name": "test_isp",
                "bk_os_bit": "64-bit",
                "bk_os_name": "linux centos",
                "bk_os_type": "1",
                "bk_os_version": "7.8.2003",
                "bk_province_name": "test_province",
                "bk_state": "test_state",
                "bk_state_name": "test_state_name",
                "bk_supplier_account": "0",
                "operator": "admin",
            }
            for index, bk_host_id in enumerate(bk_host_ids)
        ]
        return info

    def _get_find_host_biz_relations_return(self):
        bk_host_id = self.sub_infos["bk_host_id"]
        return [
            {
                "bk_biz_id": utils.CORRECT_BIZ_SET_BIZ_INFO[0]["bk_biz_id"],
                "bk_host_id": bk_host_id,
                "bk_module_id": 3,
                "bk_set_id": 2,
                "bk_supplier_account": "0",
            }
        ]

    @staticmethod
    def _get_search_biz_inst_topo_return(params):
        bk_biz_id: int = params["bk_biz_id"]
        return [
            {
                "bk_inst_id": bk_biz_id,
                "bk_inst_name": "蓝鲸",
                "bk_obj_id": "biz",
                "bk_obj_name": "Business",
                "default": 0,
                "child": [
                    {
                        "bk_inst_id": bk_biz_id,
                        "bk_inst_name": "自定义第二层",
                        "bk_obj_id": "set",
                        "bk_obj_name": "Set",
                        "default": 0,
                        "child": [
                            {
                                "bk_inst_id": bk_biz_id,
                                "bk_inst_name": "测试场景",
                                "bk_obj_id": "module",
                                "bk_obj_name": "Module",
                                "default": 0,
                                "child": [],
                            }
                        ],
                    }
                ],
            }
        ]

    def setUp(self) -> None:
        self.sub_infos = self.init_db(
            init_subscription_param=self._get_subscription_params(), is_obj=True, with_plugin_template=True
        )
        self.subscription = models.Subscription.objects.get(id=self.sub_infos["subscription_id"])
        self.subscription_step = models.SubscriptionStep.objects.get(id=self.sub_infos["subscription_step_id"])
        self.list_biz_client = mock.patch("apps.node_man.handlers.cmdb.CmdbHandler", CmdbHandler)
        self.list_biz_client.start()
        bk_biz_ids = list(set([bk_biz_info["bk_biz_id"] for bk_biz_info in utils.CORRECT_BIZ_SET_BIZ_INFO]))
        info = [
            {"bk_biz_id": bk_biz_id, "bk_biz_name": f"test_biz_name_{index}", "default": 0}
            for index, bk_biz_id in enumerate(bk_biz_ids)
        ]
        self.cmdb_mock_client = api_mkd.cmdb.utils.CMDBMockClient(
            list_business_in_business_set_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.RETURN_VALUE.value,
                return_obj={"count": len(bk_biz_ids), "info": info},
            ),
            list_business_set_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.RETURN_VALUE.value,
                return_obj={"count": len(bk_biz_ids), "info": []},
            ),
        )

        find_host_by_topo_result = self._find_host_by_topo(bk_host_ids=[self.sub_infos["bk_host_id"]])
        mock.patch("apps.node_man.handlers.cmdb.client_v2", self.cmdb_mock_client).start()
        self.cmdb_sub_mock_client = api_mkd.cmdb.utils.CMDBMockClient(
            search_biz_inst_topo_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.SIDE_EFFECT.value,
                return_obj=self._get_search_biz_inst_topo_return,
            ),
            get_biz_internal_module_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.SIDE_EFFECT.value,
                return_obj=self._get_get_biz_internal_module_return,
            ),
            get_mainline_object_topo_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.SIDE_EFFECT.value,
                return_obj=self.get_get_mainline_object_topo_return,
            ),
            find_host_by_topo_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.RETURN_VALUE.value, return_obj=find_host_by_topo_result
            ),
            search_business_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.SIDE_EFFECT.value, return_obj=self.search_business_return
            ),
            list_biz_hosts_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.RETURN_VALUE.value, return_obj=self.get_list_biz_hosts_return
            ),
            find_host_biz_relations_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.RETURN_VALUE.value,
                return_obj=self._get_find_host_biz_relations_return(),
            ),
        )

        mock.patch("apps.backend.subscription.tools.client_v2", self.cmdb_sub_mock_client).start()
        mock.patch("apps.backend.subscription.commons.client_v2", self.cmdb_sub_mock_client).start()
        self.batch_request_client = mock.patch(
            "apps.backend.subscription.commons.batch_request", self.get_list_biz_hosts_return
        )
        self.batch_request_client.start()

    def _run_instance_migrate(self) -> typing.Dict[str, typing.Any]:
        # TODO: 覆盖整个 run_subscription_task_and_create_instance 方法
        step_managers = {step.step_id: StepFactory.get_step_manager(step) for step in self.subscription.steps}
        step = list(step_managers.values())[0]
        scope = self.subscription.scope
        instance = tools.get_instances_by_scope(scope)
        return step.make_instances_migrate_actions(instance, auto_trigger=True, preview_only=True)


class WithHostMigrateActionTestCase(SubMigrateBaseTestCase):
    def test_action_and_without_main_check(self):
        # 指定 aciton 时所有的动作都应该同一个 JobType
        self.subscription_step.config.update(job_type=constants.JobType.STOP_DEBUG_PLUGIN)
        self.subscription_step.save()
        self.assertEqual(
            set(list(self._run_instance_migrate()["instance_actions"].values())), {constants.JobType.STOP_DEBUG_PLUGIN}
        )

    def test_biz_set_sub_change_migrate(self):
        #  指定了 aciton 的订阅不会计算变更，所以这里调整  job_type 为空
        self.subscription_step.config.update(job_type="")
        self.subscription_step.save()
        mock.patch("apps.backend.subscription.steps.plugin.concurrent.batch_call", concurrent.batch_call_serial).start()
        not_change_result = self._run_instance_migrate()
        # 对于进程状态版本正确 & 插件状态正常 & 插件配置文件对应的主机，不做变更
        self.assertFalse(not_change_result["instance_actions"])
        for reason in not_change_result["migrate_reasons"].values():
            self.assertEqual(reason["migrate_type"], PluginMigrateType.NOT_CHANGE)

        # 对于进程已经被终止的进程，下发 拉起 动作
        models.ProcessStatus.objects.all().update(status=constants.ProcStateType.TERMINATED)
        start_acition_result = self._run_instance_migrate()
        self.assertEqual(list(start_acition_result["instance_actions"].values()), [ActionNameType.START])

        # 对于目标插件版本变动的主机 区别类型下发
        self.subscription_step.config["version"] = utils.PKG_VERSION
        self.subscription_step.save()
        models.ProcessStatus.objects.all().update(
            version=f"{utils.PKG_VERSION}.rc", status=constants.ProcStateType.RUNNING
        )

        # 非策略订阅不对于版本变动进行下发
        not_change_action_result = self._run_instance_migrate()
        for reason in not_change_action_result["migrate_reasons"].values():
            self.assertEqual(reason["migrate_type"], PluginMigrateType.NOT_CHANGE)

        # 策略类型的订阅版本变动 重新安装插件
        self.subscription.category = constants.SubscriptionType.POLICY
        self.subscription.save()
        install_aciton_result = self._run_instance_migrate()
        self.assertEqual(list(install_aciton_result["instance_actions"].values()), [ActionNameType.INSTALL])

        # 对于订阅类型的主机 配置变更后应该推送配置
        models.ProcessStatus.objects.filter(bk_host_id=self.sub_infos["bk_host_id"]).update(
            configs=[
                {"md5": "546afad620e55eeb49ced52784712419", "name": f"{utils.PKG_PROJECT_NAME}.conf", "content": "test"}
            ],
            version=f"{utils.PKG_VERSION}",
        )
        push_config_aciton_result = self._run_instance_migrate()
        self.assertTrue(push_config_aciton_result["migrate_reasons"])
        self.assertEqual(
            list(push_config_aciton_result["migrate_reasons"].values())[0]["migrate_type"],
            PluginMigrateType.CONFIG_CHANGE,
        )


class BizSetSubInstRemoveTestCase(SubMigrateBaseTestCase):
    # 测试策略订阅在主机转移出业务集后的场景
    def get_list_biz_hosts_return(self, *args, **kwargs):
        return []

    def _find_host_by_topo(*args, **kwargs):
        return {"count": 0, "info": []}

    def setUp(self) -> None:
        super().setUp()
        self.subscription_step.config.update(job_type="")
        self.subscription_step.save()

    def test_sub_host_remove_abnormal_agent(self):
        # 这里没有对于 gse_agent 进程信息进行初始化， 但是有插件进程信息，所以会认为主机是不正常的，等待下一轮检查
        result = self._run_instance_migrate()
        self.assertFalse(result["instance_actions"])
        self.assertEqual(
            list(result["migrate_reasons"].values())[0]["migrate_type"], PluginMigrateType.ABNORMAL_AGENT_STATUS
        )

    def test_sub_host_remove_normal_agent(self):
        host_proc_params = deepcopy(PROCESS_STATUS_MODEL_DATA)
        host_proc_params.update(bk_host_id=utils.BK_HOST_ID)
        # gse_agent 状态正常的主机 如果不在业务集范围内 但是又有对应的主机插件进程 则进行卸载
        models.ProcessStatus.objects.create(**host_proc_params)
        result = self._run_instance_migrate()
        self.assertTrue(result["instance_actions"])
        self.assertEqual(
            list(result["migrate_reasons"].values())[0]["migrate_type"], PluginMigrateType.REMOVE_FROM_SCOPE
        )
