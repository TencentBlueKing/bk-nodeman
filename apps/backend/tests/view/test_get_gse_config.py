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

from apps.backend.constants import REDIS_AGENT_CONF_KEY_TPL
from apps.backend.subscription.steps.agent_adapter.adapter import AgentStepAdapter
from apps.backend.utils.redis import REDIS_INST
from apps.mock_data import common_unit
from apps.node_man import constants, models
from apps.utils import basic
from env.constants import GseVersion

from .base import ViewBaseTestCase


class GetLegacyGseConfigTestCase(ViewBaseTestCase):

    GSE_VERSION = GseVersion.V1.value

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
        models.AccessPoint.objects.all().update(gse_version=cls.GSE_VERSION)
        models.GsePackageDesc.objects.update_or_create(project="gse_agent", description="", category="official")
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
        cls.agent_step_adapter = AgentStepAdapter(subscription_step=cls.sub_step_obj, gse_version=cls.GSE_VERSION)

        # 此类查询在单元测试中会有如下报错， 因此将数据预先查询缓存
        # TransactionManagementError "You can't execute queries until the end of the 'atomic' block" while using signals
        # 参考：https://stackoverflow.com/questions/21458387
        cls.ap = cls.host.ap
        cls.proxies = list(cls.host.proxies)
        cls.install_channel = cls.host.install_channel()
        cls.redis_agent_conf_key = REDIS_AGENT_CONF_KEY_TPL.format(
            file_name=cls.agent_step_adapter.get_main_config_filename(), sub_inst_id=cls.sub_inst_record_obj.id
        )

    def setUp(self) -> None:
        super().setUp()
        # 每个 case 执行前移除 redis 日志列表
        REDIS_INST.delete(self.redis_agent_conf_key)

    def query_get_gse_config(self):
        query_params = {
            "bk_cloud_id": self.host.bk_cloud_id,
            "filename": self.agent_step_adapter.get_main_config_filename(),
            "node_type": self.host.node_type.lower(),
            "inner_ip": self.host.inner_ip,
            "token": self.gen_token(sub_inst_id=self.sub_inst_record_obj.id, ap_id=self.host.ap_id),
        }
        config = self.client.post(
            path="/backend/get_gse_config/",
            data=query_params,
            format=None,
            content_type="application/json",
        )
        return config

    def test_get_by_cache(self):
        config = self.query_get_gse_config()
        REDIS_INST.set(
            name=self.redis_agent_conf_key,
            value=self.agent_step_adapter.get_config(
                host=self.host,
                filename=self.agent_step_adapter.get_main_config_filename(),
                node_type=self.host.node_type.lower(),
                ap=self.ap,
                proxies=self.proxies,
                install_channel=self.install_channel,
            ),
        )
        REDIS_INST.expire(name=self.redis_agent_conf_key, time=5)
        cached_config = self.query_get_gse_config()
        self.assertEqual(config, cached_config)


class GetGseConfigTestCase(GetLegacyGseConfigTestCase):

    GSE_VERSION = GseVersion.V2.value

    def setUp(self) -> None:
        super().setUp()

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.sub_step_obj.config = {
            "job_type": constants.JobType.INSTALL_AGENT,
            "name": "gse_agent",
            "version": "2.0.0",
            "version_map_list": [],
            "choice_version_type": "unified",
        }
        cls.sub_step_obj.save()
        cls.redis_agent_conf_key = REDIS_AGENT_CONF_KEY_TPL.format(
            file_name=cls.agent_step_adapter.get_main_config_filename(), sub_inst_id=cls.sub_inst_record_obj.id
        )
        cls.agent_step_adapter = AgentStepAdapter(subscription_step=cls.sub_step_obj, gse_version=cls.GSE_VERSION)
        target_version = cls.agent_step_adapter.get_host_setup_info(cls.host).version
        models.GseConfigEnv.objects.create(
            agent_name="gse_agent",
            version=target_version,
            cpu_arch=cls.host.cpu_arch,
            os=cls.host.os_type,
            env_value={},
        )
        config_handler = cls.agent_step_adapter.get_config_handler("gse_agent", target_version)
        config_handler.fetch_config_extra_envs(cls.host.bk_biz_id)
        config_handler.get_matching_config_tmpl(
            cls.host.os_type, cls.host.cpu_arch, cls.agent_step_adapter.get_main_config_filename()
        )
        config_handler.get_matching_template_env(cls.host.os_type, cls.host.cpu_arch, "gse_agent")
