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
from copy import deepcopy
from itertools import product
from random import randint
from typing import Dict, List, Optional

from apps.backend.subscription.steps.adapter import PolicyStepAdapter
from apps.mock_data import common_unit
from apps.mock_data.backend_mkd.subscription.unit import (
    GSE_PLUGIN_DESC_DATA,
    SUBSCRIPTION_DATA,
)
from apps.node_man import constants, models
from apps.utils.unittest.testcase import CustomAPITestCase
from apps.node_man.tests.utils import create_host
from apps.backend.subscription.tools import get_all_subscription_steps_context

PLATFORMS = ["linux_x86_64", "linux_x86", "windows_x86_64"]


class PackageTemplateRenderTest(CustomAPITestCase):
    @classmethod
    def mock_plugin_step_data(
        cls,
        plugin_is_latest: bool,
        config_tmpl_is_latest: bool,
        plugin_name: str,
        config_template_name: List[str],
        plugin_version: str,
        config_template_versions,
        platforms: Optional[List[str]] = None,
        job_type: str = constants.JobType.MAIN_INSTALL_PLUGIN,
    ):

        if plugin_is_latest:
            plugin_version = "latest"
        if config_tmpl_is_latest:
            config_template_versions = ["latest"]

        config_templates: List[Dict[str, str]] = []

        def single_config_template(single_config_name, single_config_version, single_platform: str = None):
            if single_platform is None:
                single_platform_dict = {}
            else:
                cpu_arch, os_type = single_platform.split("_", maxsplit=1)
                single_platform_dict = f"{os_type}_{cpu_arch}"

            return {
                **single_platform_dict,
                **{
                    "version": single_config_version,
                    "name": single_config_name,
                    "is_main": True,
                },
            }

        if platforms is not None:
            for (config_name, config_version, platform) in product(
                config_template_name, config_template_versions, platforms
            ):
                config_templates.append(
                    single_config_template(
                        single_config_name=config_name, single_config_version=config_version, single_platform=platform
                    )
                )
        else:
            for (config_name, config_version) in product(config_template_name, config_template_versions):
                config_templates.append(
                    single_config_template(single_config_name=config_name, single_config_version=config_version)
                )

        return {
            "config": {
                "config_templates": config_templates,
                "plugin_version": plugin_version,
                "plugin_name": plugin_name,
                "job_type": job_type,
            },
            "type": constants.ProcType.PLUGIN,
            "id": plugin_name,
            "params": {"context": {}},
        }

    @classmethod
    def init_package_record(cls, plugin_name: str, config_names: List[str], platforms: List[str], version: str):
        plugin_desc_data = dict(GSE_PLUGIN_DESC_DATA, **{"name": plugin_name, "config_file": config_names})
        models.GsePluginDesc.objects.create(**plugin_desc_data)

        for platform in platforms:
            os_type, cpu_arch = platform.split("_", maxsplit=1)
            models.Packages.objects.create(
                pkg_name="test1.tar",
                version=version,
                module="gse_plugin",
                project=plugin_name,
                pkg_size=10255,
                pkg_path="/data/bkee/miniweb/download/windows/x86_64",
                location="http://127.0.0.1/download/windows/x86_64",
                md5="a95c530a7af5f492a74499e70578d150",
                pkg_ctime="2019-05-05 11:54:28.070771",
                pkg_mtime="2019-05-05 11:54:28.070771",
                os=os_type,
                cpu_arch=cpu_arch,
                is_release_version=False,
                is_ready=True,
            )

    @classmethod
    def init_subscription_record(cls, plugin_name: str):
        local_subscription_data = deepcopy(SUBSCRIPTION_DATA)
        scope = local_subscription_data["scope"]
        subscription = models.Subscription.objects.create(
            bk_biz_id=scope["bk_biz_id"],
            object_type=scope["object_type"],
            node_type=scope["node_type"],
            nodes=scope["nodes"],
            target_hosts=SUBSCRIPTION_DATA.get("target_hosts"),
            from_system="blueking",
            enable=False,
            creator="admin",
            plugin_name=plugin_name,
        )

        return subscription.id

    @classmethod
    def config_template_creator(
        cls,
        os_type: str,
        cpu_arch: str,
        versions: list,
        plugin_name: str,
        names: list,
        plugin_versions: List[str] = ["*"],
        is_main: bool = True,
        is_release_version: bool = False,
    ):

        common_params = {
            "file_path": "etc",
            "content": " ",
            "is_release_version": 1,
            "creator": "admin",
            "create_time": "2000-01-01 09:30:00",
            "source_app_code": "bk_nodeman",
        }

        for (name, version, plugin_version) in product(names, versions, plugin_versions):
            config_template_params = {
                **common_params,
                **{
                    "os": os_type,
                    "cpu_arch": cpu_arch,
                    "version": version,
                    "plugin_name": plugin_name,
                    "name": name,
                    "is_main": is_main,
                    "is_release_version": is_release_version,
                    "plugin_version": plugin_version,
                },
            }
            models.PluginConfigTemplate.objects.create(**config_template_params)

    @classmethod
    def init_subscription_step_record(cls, subscription_id: int, step: Dict) -> models.SubscriptionStep:
        subscription_obj = models.Subscription.objects.get(id=subscription_id)

        return models.SubscriptionStep.objects.create(
            subscription_id=subscription_id,
            index=randint(1, 500000),
            step_id=subscription_obj.plugin_name,
            type=constants.ProcType.PLUGIN,
            config=step["config"],
            params=step["params"],
        ).step_id

    @classmethod
    def platform_split_to_os(cls, platform: str):
        os_type, cpu_arch = platform.split("_", maxsplit=1)
        return os_type, cpu_arch

    def init_policy_adapter(
        self,
        plugin_name: str,
        config_files_names: List[str],
        platforms: List,
        plugin_version: str,
        init_config_template_versions: List[str],
        step_config_template_versions: List[str],
        step_plugin_version: str,
    ):

        config_tmpl_is_latest = init_config_template_versions == ["latest"]
        plugin_is_latest = step_plugin_version == "latest"

        subscription_id = self.init_subscription_record(plugin_name=plugin_name)
        subscription_step_config_template = self.mock_plugin_step_data(
            config_tmpl_is_latest=config_tmpl_is_latest,
            plugin_is_latest=plugin_is_latest,
            plugin_name=plugin_name,
            config_template_name=config_files_names,
            plugin_version=plugin_version,
            config_template_versions=step_config_template_versions,
        )
        subscription_step_id = self.init_subscription_step_record(
            subscription_id=subscription_id, step=subscription_step_config_template
        )
        self.init_package_record(
            plugin_name=plugin_name, config_names=config_files_names, platforms=platforms, version=plugin_version
        )

        plugin_versions = ["*", plugin_version]
        for platform in platforms:
            os_type, cpu_arch = self.platform_split_to_os(platform)
            # 创建配置模板
            self.config_template_creator(
                os_type=os_type,
                cpu_arch=cpu_arch,
                versions=init_config_template_versions,
                plugin_name=plugin_name,
                names=config_files_names,
                plugin_versions=plugin_versions,
            )

        policy_adapter = PolicyStepAdapter(models.SubscriptionStep.objects.get(step_id=subscription_step_id))

        return policy_adapter

    def test_single_config_latest_case(self):
        # 订阅插件和模板都为latest时，"*" 版本先于配置模板创建

        policy_adapter = self.init_policy_adapter(
            plugin_name=common_unit.plugin.PLUGIN_NAME,
            config_files_names=["basereport.conf"],
            platforms=PLATFORMS,
            plugin_version="1.2",
            init_config_template_versions=["1.1", "1.2", "1.3", "1.0"],
            step_config_template_versions=["latest"],
            step_plugin_version="latest",
        )
        self.assertEqual(policy_adapter.plugin_name, common_unit.plugin.PLUGIN_NAME)

        # 存在对应平台配置模板时，选择对应平台的最后一条插入信息
        self.assertTrue(
            len(policy_adapter.get_matching_config_tmpl_objs(constants.OsType.LINUX, constants.CpuType.x86_64)), 1
        )
        linux_x86_policy_template_id = policy_adapter.get_matching_config_tmpl_objs(
            constants.OsType.LINUX, constants.CpuType.x86_64
        )[0].id
        linux_x86_plugin_tmpl_id = models.PluginConfigTemplate.objects.get(
            plugin_version="1.2", os=constants.OsType.LINUX.lower(), cpu_arch=constants.CpuType.x86_64, version="1.0"
        ).id
        self.assertEqual(linux_x86_policy_template_id, linux_x86_plugin_tmpl_id)

        # 不存在任何对应平台类型的配置模板时，相关主机不渲染模板
        self.assertFalse(
            policy_adapter.get_matching_config_tmpl_objs(constants.OsType.LINUX, constants.CpuType.aarch64)
        )

    def test_multi_config_latest_case(self):
        policy_adapter = self.init_policy_adapter(
            plugin_name=common_unit.plugin.PLUGIN_NAME,
            config_files_names=["basereport.conf", "env.yaml"],
            platforms=PLATFORMS,
            plugin_version="1.2",
            init_config_template_versions=["1.1", "1.2"],
            step_config_template_versions=["latest"],
            step_plugin_version="latest",
        )
        self.assertEqual(policy_adapter.plugin_name, common_unit.plugin.PLUGIN_NAME)
        self.assertEqual(
            len(policy_adapter.get_matching_config_tmpl_objs(constants.OsType.LINUX, constants.CpuType.x86_64)), 2
        )

        first_template_obj, last_template_obj = policy_adapter.get_matching_config_tmpl_objs(
            constants.OsType.LINUX, constants.CpuType.x86_64
        )
        first_linux_x86_plugin_tmpl_id = models.PluginConfigTemplate.objects.get(
            plugin_version="1.2",
            os=constants.OsType.LINUX.lower(),
            cpu_arch=constants.CpuType.x86_64,
            name=first_template_obj.name,
            version="1.2",
        ).id

        last_linux_x86_plugin_tmpl_id = models.PluginConfigTemplate.objects.get(
            plugin_version="1.2",
            os=constants.OsType.LINUX.lower(),
            cpu_arch=constants.CpuType.x86_64,
            name=last_template_obj.name,
            version="1.2",
        ).id

        self.assertEqual(last_template_obj.id, last_linux_x86_plugin_tmpl_id)
        self.assertEqual(first_template_obj.id, first_linux_x86_plugin_tmpl_id)

    def _with_plugin_version__diff_tmpl(
        self,
        plugin_version: str,
        init_config_template_versions: List[str],
        step_config_template_versions: List[str],
        step_plugin_version: str,
        match_plugin_version: str,
        match_config_tmpl_version: str,
    ):
        policy_adapter = self.init_policy_adapter(
            plugin_name=common_unit.plugin.PLUGIN_NAME,
            config_files_names=["basereport.conf"],
            platforms=PLATFORMS,
            plugin_version=plugin_version,
            init_config_template_versions=init_config_template_versions,
            step_config_template_versions=step_config_template_versions,
            step_plugin_version=step_plugin_version,
        )
        config_template_obj = policy_adapter.get_matching_config_tmpl_objs(
            constants.OsType.LINUX, constants.CpuType.x86_64
        )[0]
        matching_config_tmpl_id = models.PluginConfigTemplate.objects.get(
            plugin_version=match_plugin_version,
            os=constants.OsType.LINUX.lower(),
            cpu_arch=constants.CpuType.x86_64,
            name=config_template_obj.name,
            version=match_config_tmpl_version,
        ).id
        self.assertEqual(config_template_obj.id, matching_config_tmpl_id)

    def test_plugin_version__without_tmpl_case(self):
        # 插件包版本存在时，当目标配置模板版本较低且不存在时，给最新的配置
        self._with_plugin_version__diff_tmpl(
            plugin_version="1.2",
            init_config_template_versions=["1.1", "1.2"],
            step_config_template_versions=["1.0"],
            step_plugin_version="1.1",
            match_plugin_version="1.2",
            match_config_tmpl_version="1.2",
        )

    def test_get_all_subscription_steps_context(self):
        """测试获取渲染配置模板参数"""
        # 创建主机数据
        host_list, _, _ = create_host(
            1,
            bk_host_id=1,
            bk_cloud_id=0,
            ip="127.0.0.1",
            os_type=constants.OsType.LINUX,
        )
        target_host = host_list[0]

        # 创建订阅数据
        subscription = models.Subscription.objects.create(
            bk_biz_id=target_host.bk_biz_id,
            object_type=models.Subscription.ObjectType.HOST,
            node_type=models.Subscription.NodeType.TOPO,
            nodes=[{"bk_host_id": target_host.bk_host_id}],
            from_system="blueking",
            enable=False,
            creator="admin",
        )
        subscription_step = models.SubscriptionStep.objects.create(
            subscription_id=subscription.id,
            index=0,
            step_id=common_unit.plugin.PLUGIN_NAME,
            type="PLUGIN",
            config={
                "plugin_name": common_unit.plugin.PLUGIN_NAME,
                "plugin_version": common_unit.plugin.PACKAGE_VERSION,
                "config_templates": [{
                    "name": common_unit.plugin.GSE_PLUGIN_DESC_MODEL_DATA["config_file"],
                    "version": common_unit.plugin.PACKAGE_VERSION
                }]
            },
            params={"context": {"params_context": "test"}},
        )

        # 创建插件相关数据数据
        models.GsePluginDesc.objects.create(**common_unit.plugin.GSE_PLUGIN_DESC_MODEL_DATA)
        models.Packages.objects.create(**common_unit.plugin.PACKAGES_MODEL_DATA)
        models.ProcControl.objects.create(**common_unit.plugin.PROC_CONTROL_MODEL_DATA)

        proc_status_model_data = deepcopy(common_unit.plugin.PROC_STATUS_MODEL_DATA)
        proc_status_model_data["group_id"] = f"sub_{subscription.id}_host_{target_host.bk_host_id}"
        proc_status_model_data["source_id"] = subscription.id
        models.ProcessStatus.objects.create(**proc_status_model_data)

        policy_step_adapter = PolicyStepAdapter(subscription_step)
        context = get_all_subscription_steps_context(
            subscription_step,
            {"host": {"bk_host_id": target_host.bk_host_id}},
            target_host,
            common_unit.plugin.PLUGIN_NAME,
            target_host.agent_config,
            policy_step_adapter,
        )

        # 验证 context 中包含 control_info
        self.assertTrue("control_info" in context.keys())

        # 验证 step.params.context 处于 context 根节点下
        self.assertTrue("params_context" in context.keys())

    # 当前没有指定具体插件模板版本好的需求 有需要再打开

    # def test_plugin_version__lower_tmpl_case(self):
    #     # 目标版本存在时，即使插件版本高于模板指定版本，也给模板的版本
    #     self._with_plugin_version__diff_tmpl(
    #         plugin_version="1.2",
    #         init_config_template_versions=["1.0", "1.1", "1.2"],
    #         step_config_template_versions=["1.0"],
    #         step_plugin_version="1.2",
    #         match_plugin_version="1.2",
    #         match_config_tmpl_version="1.0",
    #     )
    #
    # def test_plugin_version__higher_tmpl_case(self):
    #     # 目标版本存在时，即使插件版本高于模板指定版本，给指定模板版本号中的高版本
    #     self._with_plugin_version__diff_tmpl(
    #         plugin_version="1.2",
    #         init_config_template_versions=["1.0", "1.1", "1.2"],
    #         step_config_template_versions=["1.0", "1.1"],
    #         step_plugin_version="1.2",
    #         match_plugin_version="1.2",
    #         match_config_tmpl_version="1.1",
    #     )
