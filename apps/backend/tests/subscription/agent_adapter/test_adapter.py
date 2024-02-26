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
import copy
import json

from apps.backend.subscription.steps.agent_adapter.adapter import AgentStepAdapter
from apps.backend.tests.agent.utils import VERSION, AgentBaseTestCase, ProxyBaseTestCase
from apps.backend.tests.components.collections.agent_new.utils import (
    AgentTestObjFactory,
)
from apps.mock_data import common_unit
from apps.node_man import constants, models
from apps.utils import basic
from env.constants import GseVersion


class AgentStepAdapterTestCase(AgentBaseTestCase):
    host: models.Host = None
    sub_step_obj: models.SubscriptionStep = None
    sub_inst_record_obj: models.SubscriptionInstanceRecord = None
    agent_step_adapter: AgentStepAdapter = None
    redis_agent_conf_key: str = None

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        host_model_data = copy.deepcopy(common_unit.host.HOST_MODEL_DATA)
        cls.host = models.Host.objects.create(**host_model_data)
        AgentTestObjFactory.init_gse_package_desc()

        # 创建订阅相关数据
        sub_inst_data = basic.remove_keys_from_dict(
            origin_data=common_unit.subscription.SUB_INST_RECORD_MODEL_DATA, keys=["id"]
        )
        sub_step_data = basic.remove_keys_from_dict(
            origin_data=common_unit.subscription.SUB_AGENT_STEP_MODEL_DATA, keys=["id"]
        )
        cls.sub_inst_record_obj = models.SubscriptionInstanceRecord.objects.create(**sub_inst_data)
        cls.sub_step_obj = models.SubscriptionStep.objects.create(
            **{
                **sub_step_data,
                **{
                    "subscription_id": cls.sub_inst_record_obj.subscription_id,
                    "config": {"job_type": constants.JobType.INSTALL_AGENT, "version_map_list": []},
                },
            }
        )
        cls.agent_step_adapter = AgentStepAdapter(subscription_step=cls.sub_step_obj)

        # 此类查询在单元测试中会有如下报错， 因此将数据预先查询缓存
        # TransactionManagementError "You can't execute queries until the end of the 'atomic' block" while using signals
        # 参考：https://stackoverflow.com/questions/21458387
        cls.ap = cls.host.ap
        cls.proxies = list(cls.host.proxies)
        cls.install_channel = cls.host.install_channel()

    def get_config(self, config_name: str):
        return self.agent_step_adapter.get_config(
            host=self.host,
            filename=config_name,
            node_type=self.host.node_type.lower(),
            ap=self.ap,
            proxies=self.proxies,
            install_channel=self.install_channel,
        )

    def test_get_config(self):
        self.get_config(self.agent_step_adapter.get_main_config_filename())


class Proxy2StepAdapterTestCase(ProxyBaseTestCase, AgentStepAdapterTestCase):
    @classmethod
    def clear_agent_data(cls):
        models.GseConfigEnv.objects.all().delete()
        models.GseConfigTemplate.objects.all().delete()

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.sub_step_obj.config = {
            "job_type": constants.JobType.INSTALL_AGENT,
            "name": constants.GsePackageCode.PROXY.value,
            "version": VERSION,
            "version_map_list": [],
            "choice_version_type": "unified",
        }
        cls.sub_step_obj.save()
        cls.agent_step_adapter = AgentStepAdapter(subscription_step=cls.sub_step_obj, gse_version=GseVersion.V2.value)

    def test_get_config(self):
        self.clear_agent_data()
        self.host.node_type = "PROXY"
        self.host.bk_cloud_id = 1
        agent_setup_info = self.agent_step_adapter.get_host_setup_info(self.host)
        for config_name in constants.GsePackageTemplate.PROXY.value:
            self.get_config(config_name)
            self.assertEqual(
                self.agent_step_adapter.get_config_handler(
                    agent_name=agent_setup_info.name,
                    target_version=agent_setup_info.version,
                )
                .get_matching_config_tmpl(self.host.os_type, self.host.cpu_arch, config_name)
                .agent_name_from,
                constants.GsePackageCode.PROXY.value,
            )
        for config_name in constants.GsePackageTemplate.AGENT.value:
            self.get_config(config_name)
            self.assertEqual(
                self.agent_step_adapter.get_config_handler(
                    agent_name=agent_setup_info.name,
                    target_version=agent_setup_info.version,
                )
                .get_matching_config_tmpl(self.host.os_type, self.host.cpu_arch, config_name)
                .agent_name_from,
                constants.GsePackageCode.AGENT.value,
            )


class Proxy2StepAdapterWithManagerTestCase(Proxy2StepAdapterTestCase):
    def setUp(self):
        super().setUp()
        with self.ARTIFACT_BUILDER_CLASS(initial_artifact_path=self.ARCHIVE_PATH) as builder:
            builder.make()

    @classmethod
    def clear_agent_data(cls):
        pass

    def test_get_env(self):
        agent_setup_info = self.agent_step_adapter.get_host_setup_info(self.host)
        agent_env = self.agent_step_adapter.get_config_handler(
            agent_name=agent_setup_info.name,
            target_version=agent_setup_info.version,
        ).get_matching_template_env(self.host.os_type, self.host.cpu_arch, constants.GsePackageCode.AGENT.value)

        self.assertEqual(agent_env["BK_GSE_HOME_DIR"], "/usr/local/gse/agent")

        proxy_env = self.agent_step_adapter.get_config_handler(
            agent_name=agent_setup_info.name,
            target_version=agent_setup_info.version,
        ).get_matching_template_env(self.host.os_type, self.host.cpu_arch, constants.GsePackageCode.PROXY.value)

        self.assertEqual(proxy_env["BK_GSE_HOME_DIR"], "/usr/local/gse/proxy")

    def test_render_log_level(self):
        config = json.loads(self.get_config(self.agent_step_adapter.get_main_config_filename()))
        self.assertEqual(config["logger"]["level"], "INFO")


class Agent2StepAdapterTestCase(AgentStepAdapterTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.sub_step_obj.config = {
            "job_type": constants.JobType.INSTALL_AGENT,
            "name": constants.GsePackageCode.AGENT.value,
            "version": VERSION,
            "version_map_list": [],
            "choice_version_type": "unified",
        }
        cls.sub_step_obj.save()
        cls.agent_step_adapter = AgentStepAdapter(subscription_step=cls.sub_step_obj, gse_version=GseVersion.V2.value)

    def test_get_config__extra_env(self):
        config: str = self.get_config(self.agent_step_adapter.get_main_config_filename())
        self.assertTrue('"bind_ip": "::"' in config)
        self.assertTrue('"enable_compression": false' in config)

        # 清理缓存
        self.agent_step_adapter._config_handler_cache = {}

        config_extra_env_obj: models.GseConfigExtraEnv = models.GseConfigExtraEnv.objects.create(
            bk_biz_id=self.host.bk_biz_id,
            name="test",
            enable=True,
            condition={"bk_cloud_id": [0], "node_type": [constants.NodeType.AGENT]},
            env_value={"BK_GSE_DATA_ENABLE_COMPRESSION": "true", "BK_GSE_PROXY_BIND_IP": "0.0.0.0"},
        )

        config: str = self.get_config(self.agent_step_adapter.get_main_config_filename())

        self.assertTrue('"bind_ip": "0.0.0.0"' in config)
        self.assertTrue('"enable_compression": true' in config)

        # 清理缓存
        self.agent_step_adapter._config_handler_cache = {}

        # 未命中策略
        config_extra_env_obj.condition["bk_cloud_id"] = [1]
        config_extra_env_obj.save()

        config: str = self.get_config(self.agent_step_adapter.get_main_config_filename())
        self.assertTrue('"bind_ip": "::"' in config)
        self.assertTrue('"enable_compression": false' in config)
