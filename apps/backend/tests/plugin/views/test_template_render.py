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
from typing import Dict, List, Optional, Union

from django.test import TestCase

from apps.backend.tests.subscription.test_performance import subscription_data
from apps.mock_data import common_unit
from apps.node_man import constants, models

PLATFORMS = ["linux_x86_64", "linux_x86", "windows_x86_64"]


class PackageTemplateRenderTest(TestCase):
    @classmethod
    def mock_plugin_step_data(
        cls,
        plugin_is_latest: bool,
        config_tmpl_is_latest: bool,
        plugin_name: str,
        config_template_name: List[str],
        plugin_version: str,
        config_template_versions,
        platforms: Union[Optional, List[str]] = None,
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
            "type": "PLUGIN",
            "id": plugin_name,
            "params": {"context": {}},
        }

    @classmethod
    def init_package_record(cls, plugin_name: str, config_names: List[str], platforms: List[str], version: str):
        models.GsePluginDesc.objects.create(
            **{
                "name": plugin_name,
                "description": "测试插件啊",
                "scenario": "测试",
                "category": "external",
                "launch_node": "all",
                "config_file": config_names,
                "config_format": "yaml",
                "use_db": False,
            }
        )

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
        local_subscription_data = deepcopy(subscription_data)
        scope = local_subscription_data["scope"]
        subscription = models.Subscription.objects.create(
            bk_biz_id=scope["bk_biz_id"],
            object_type=scope["object_type"],
            node_type=scope["node_type"],
            nodes=scope["nodes"],
            target_hosts=subscription_data.get("target_hosts"),
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
        from itertools import product

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

        from random import randint

        return models.SubscriptionStep.objects.create(
            subscription_id=subscription_id,
            index=randint(1, 500000),
            step_id=subscription_obj.plugin_name,
            type="PLUGIN",
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

        from apps.backend.subscription.steps.adapter import PolicyStepAdapter

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
        assert policy_adapter.plugin_name == common_unit.plugin.PLUGIN_NAME

        # 存在对应平台配置模板时，选择对应平台的最后一条插入信息
        assert len(policy_adapter.get_matching_config_tmpl_objs(constants.OsType.LINUX, constants.CpuType.x86_64)) == 1
        linux_x86_policy_template_id = policy_adapter.get_matching_config_tmpl_objs(
            constants.OsType.LINUX, constants.CpuType.x86_64
        )[0].id
        linux_x86_plugin_tmpl_id = models.PluginConfigTemplate.objects.get(
            plugin_version="1.2", os=constants.OsType.LINUX.lower(), cpu_arch=constants.CpuType.x86_64, version="1.0"
        ).id
        assert linux_x86_policy_template_id == linux_x86_plugin_tmpl_id

        # 不存在任何对应平台类型的配置模板时，相关主机不渲染模板
        assert not policy_adapter.get_matching_config_tmpl_objs(constants.OsType.LINUX, constants.CpuType.aarch64)

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
        assert policy_adapter.plugin_name == common_unit.plugin.PLUGIN_NAME
        assert len(policy_adapter.get_matching_config_tmpl_objs(constants.OsType.LINUX, constants.CpuType.x86_64)) == 2

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

        self.assertTrue(last_template_obj, last_linux_x86_plugin_tmpl_id)
        self.assertTrue(first_template_obj.id, first_linux_x86_plugin_tmpl_id)

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
        self.assertTrue(config_template_obj.id, matching_config_tmpl_id)

    @classmethod
    def clear_init_db(cls):
        model_list = [
            models.PluginConfigTemplate,
            models.GsePluginDesc,
            models.Packages,
            models.Subscription,
            models.SubscriptionStep,
        ]
        for model in model_list:
            model.objects.all().delete()

    def test_with_plugin_version__diff_tmpl_case(self):
        # 插件包版本存在时，当目标配置模板版本较低且不存在时，给最新的配置
        self._with_plugin_version__diff_tmpl(
            plugin_version="1.2",
            init_config_template_versions=["1.1", "1.2"],
            step_config_template_versions=["1.0"],
            step_plugin_version="1.1",
            match_plugin_version="1.2",
            match_config_tmpl_version="1.2",
        )
        self.clear_init_db()

        # 目标版本存在时，即使插件版本高于模板指定版本，也给模板的版本
        self._with_plugin_version__diff_tmpl(
            plugin_version="1.2",
            init_config_template_versions=["1.0", "1.1", "1.2"],
            step_config_template_versions=["1.0"],
            step_plugin_version="1.2",
            match_plugin_version="1.2",
            match_config_tmpl_version="1.0",
        )
        self.clear_init_db()

        # 目标版本存在时，即使插件版本高于模板指定版本，给指定模板版本号中的高版本
        self._with_plugin_version__diff_tmpl(
            plugin_version="1.2",
            init_config_template_versions=["1.0", "1.1", "1.2"],
            step_config_template_versions=["1.0", "1.1"],
            step_plugin_version="1.2",
            match_plugin_version="1.2",
            match_config_tmpl_version="1.1",
        )
        self.clear_init_db()
