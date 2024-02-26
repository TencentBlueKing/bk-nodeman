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
import typing

import mock
from django.conf import settings

from apps.backend.subscription.steps.agent_adapter.handlers import GseConfigHandler
from apps.backend.tests.agent import template_env, utils
from apps.core.tag.constants import TargetType
from apps.core.tag.models import Tag
from apps.core.tag.targets.agent import AgentTargetHelper
from apps.mock_data import utils as mock_data_utils
from apps.node_man import constants, models


class FileSystemTestCase(utils.AgentBaseTestCase):

    OVERWRITE_VERSION = "stable"

    def parse_env_checker(self, env_values: typing.Dict[str, typing.Any]):
        # 字符串类型断言
        self.assertTrue(env_values["BK_GSE_HOME_DIR"] == "/usr/local/gse/agent")
        # 数字类型断言
        self.assertTrue(env_values["BK_GSE_CLOUD_ID"] == 0)
        # 布尔类型断言, 布尔类型需要json.dumps之后的结果进行渲染
        self.assertTrue(env_values["BK_GSE_DATA_ENABLE_COMPRESSION"] == "false")
        # 空字符串断言
        self.assertTrue(env_values["BK_GSE_EXTRA_CONFIG_DIRECTORY"] == "")

    def pkg_checker(self, version_str: str):
        """
        安装包检查
        :param version_str: 版本
        :return:
        """
        pkg_name: str = f"{self.ARTIFACT_BUILDER_CLASS.NAME}-{version_str}.tgz"
        for package_os, cpu_arch in self.OS_CPU_CHOICES:
            package_path: str = os.path.join(
                settings.DOWNLOAD_PATH, self.ARTIFACT_BUILDER_CLASS.BASE_STORAGE_DIR, package_os, cpu_arch, pkg_name
            )
            self.assertTrue(os.path.exists(package_path))

    def tag_checker(self):
        agent_name_target_id_map: typing.Dict[str, int] = AgentTargetHelper.get_agent_name_target_id_map()

        agent_target_version = Tag.objects.get(
            target_id=agent_name_target_id_map[self.NAME],
            name=self.OVERWRITE_VERSION,
            target_type=TargetType.AGENT.value,
        ).target_version

        self.assertTrue(agent_target_version == utils.VERSION)

    def template_and_env_checker(self, version_str):
        gse_config_handler: GseConfigHandler = GseConfigHandler(self.NAME, version_str)

        for package_os, cpu_arch in self.OS_CPU_CHOICES:
            filter_kwargs: dict = {
                "agent_name": self.NAME,
                "os": package_os,
                "cpu_arch": cpu_arch,
                "version": version_str,
            }
            self.assertDictEqual(
                gse_config_handler.get_matching_template_env(package_os, cpu_arch, self.NAME),
                self.ARTIFACT_BUILDER_CLASS.parse_env(
                    (template_env.DEFAULT_AGENT_TEMPLATE_ENV, template_env.DEFAULT_PROXY_TEMPLATE_ENV)[
                        self.NAME == constants.GsePackageCode.PROXY.value
                    ]
                ),
            )

            # gse_agent.conf 一定是 gse_agent 的
            self.assertEqual(
                gse_config_handler.get_matching_config_tmpl(
                    package_os, cpu_arch, config_name="gse_agent.conf"
                ).agent_name_from,
                constants.GsePackageCode.AGENT.value,
            )
            gse_config_handler.get_matching_config_tmpl(package_os, cpu_arch, config_name="gse_agent.conf")

            if self.NAME == constants.GsePackageCode.PROXY.value:
                self.assertEqual(
                    gse_config_handler.get_matching_config_tmpl(
                        package_os, cpu_arch, config_name="gse_data_proxy.conf"
                    ).agent_name_from,
                    self.NAME,
                )
                self.assertEqual(
                    gse_config_handler.get_matching_config_tmpl(
                        package_os, cpu_arch, config_name="gse_file_proxy.conf"
                    ).agent_name_from,
                    self.NAME,
                )

            config_env_obj: models.GseConfigEnv = models.GseConfigEnv.objects.filter(**filter_kwargs).first()
            self.parse_env_checker(env_values=config_env_obj.env_value)

            self.assertTrue(models.GseConfigTemplate.objects.filter(**filter_kwargs).exists())

    def gse_package_and_desc_records_checker(self, version_str):
        for package_os, cpu_arch in self.OS_CPU_CHOICES:
            filter_kwargs: dict = {
                "project": self.NAME,
                "os": package_os,
                "cpu_arch": cpu_arch,
                "version": version_str,
            }
            self.assertTrue(models.GsePackages.objects.filter(**filter_kwargs).exists())
            self.assertTrue(models.GsePackageDesc.objects.filter(**{"project": filter_kwargs.pop("project")}).exists())

    def test_make(self):
        """测试安装包制作"""
        with self.ARTIFACT_BUILDER_CLASS(initial_artifact_path=self.ARCHIVE_PATH) as builder:
            builder.make()
        self.pkg_checker(version_str=utils.VERSION)
        self.template_and_env_checker(version_str=utils.VERSION)
        self.gse_package_and_desc_records_checker(version_str=utils.VERSION)

    def test_make__overwrite_version(self):
        """测试版本号覆盖"""
        with self.ARTIFACT_BUILDER_CLASS(
            initial_artifact_path=self.ARCHIVE_PATH,
            overwrite_version=self.OVERWRITE_VERSION,
            tags=[self.OVERWRITE_VERSION],
        ) as builder:
            builder.make()

            env_values: typing.Dict[str, typing.Any] = builder.parse_env(self.TEMPLATE_ENV)
            self.parse_env_checker(env_values)

        # overwrite_version 会上传一个额外副本到文件源
        self.pkg_checker(version_str=utils.VERSION)
        self.template_and_env_checker(version_str=utils.VERSION)
        self.pkg_checker(version_str=self.OVERWRITE_VERSION)
        self.tag_checker()
        self.gse_package_and_desc_records_checker(version_str=utils.VERSION)


class BkRepoTestCase(FileSystemTestCase):
    FILE_OVERWRITE = True
    OVERWRITE_OBJ__KV_MAP = mock_data_utils.OVERWRITE_OBJ__KV_MAP

    @classmethod
    def setUpClass(cls):
        mock.patch("apps.core.files.storage.CustomBKRepoStorage", mock_data_utils.CustomBKRepoMockStorage).start()
        super().setUpClass()


class AutoTypeStrategyCrontabTestCase(utils.AutoTypeStrategyMixin, FileSystemTestCase):
    pass


class AutoTypeStrategyDefaultTestCase(AutoTypeStrategyCrontabTestCase):
    AUTO_TYPE = constants.GseLinuxAutoType.RCLOCAL.value

    def setUp(self):
        super().setUp()
        models.GlobalSettings.objects.filter(key=models.GlobalSettings.KeyEnum.GSE2_LINUX_AUTO_TYPE.value).delete()


class AutoTypeStrategyDiffTestCase(AutoTypeStrategyCrontabTestCase):
    AUTO_TYPE_STRATEGY = {constants.GsePackageCode.PROXY.value: "crontab"}
    AUTO_TYPE = constants.GseLinuxAutoType.RCLOCAL.value


class AutoTypeStrategyNotEffectTestCase(AutoTypeStrategyCrontabTestCase):
    AUTO_TYPE_STRATEGY = {constants.GsePackageCode.AGENT.value: "crontab"}
    AUTO_TYPE = constants.GseLinuxAutoType.CRONTAB.value
