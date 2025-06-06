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
import os.path
from abc import ABC

from django.conf import settings
from django.utils.crypto import get_random_string

from apps.backend.components.collections.agent_new import components
from apps.node_man import constants, models
from common.api import JobApi
from env.constants import GseVersion
from pipeline.component_framework.test import ComponentTestCase, ExecuteAssertion

from . import base, utils


class PushUpgradePackageTestCase(base.JobBaseTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "下发 Linux 升级包成功"

    def component_cls(self):
        return components.PushUpgradePackageComponent

    @staticmethod
    def get_assert_file_list():
        return [os.path.join(settings.DOWNLOAD_PATH, "gse_client-linux-x86_64_upgrade.tgz")]

    def tearDown(self) -> None:
        record = self.job_api_mock_client.call_recorder.record
        fast_transfer_file_query_params = record[JobApi.fast_transfer_file][0].args[0]
        self.assertEqual(
            fast_transfer_file_query_params["file_source_list"][0]["file_list"],
            self.get_assert_file_list(),
        )
        super().tearDown()


class PushUpgradePackageV2TestCase(PushUpgradePackageTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "下发 Linux 升级包 2.0 成功"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.obj_factory.init_gse_package_desc()
        models.Host.objects.filter(bk_host_id__in=cls.obj_factory.bk_host_ids).update(bk_agent_id=get_random_string())
        sub_step_obj: models.SubscriptionStep = cls.obj_factory.sub_step_objs[0]
        sub_step_obj.config.update({"name": "gse_agent", "version": "2.0.0"})
        sub_step_obj.save()

    def structure_common_inputs(self):
        inputs = super().structure_common_inputs()
        inputs["meta"] = {"GSE_VERSION": GseVersion.V2.value}
        return inputs

    def component_cls(self):
        return components.PushUpgradePackageComponent

    @staticmethod
    def get_assert_file_list():
        return [os.path.join(settings.DOWNLOAD_PATH, "agent/linux/x86_64/gse_agent-2.0.0.tgz")]


class PushWindowsUpgradePackageV2TestCase(PushUpgradePackageV2TestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "下发 Windows 升级包 2.0 成功"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        models.Host.objects.filter(bk_host_id__in=cls.obj_factory.bk_host_ids).update(os_type=constants.OsType.WINDOWS)

    def component_cls(self):
        return components.PushUpgradePackageComponent

    @staticmethod
    def get_assert_file_list():
        return [
            os.path.join(settings.DOWNLOAD_PATH, "agent/windows/x86_64/gse_agent-2.0.0.tgz"),
            os.path.join(settings.DOWNLOAD_PATH, "7z.dll"),
            os.path.join(settings.DOWNLOAD_PATH, "7z.exe"),
        ]


class PushWindowsUpgradePackageTestCase(PushUpgradePackageTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "下发 Windows 升级包成功"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        models.Host.objects.filter(bk_host_id__in=cls.obj_factory.bk_host_ids).update(os_type=constants.OsType.WINDOWS)

    def component_cls(self):
        return components.PushUpgradePackageComponent

    @staticmethod
    def get_assert_file_list():
        return [
            os.path.join(settings.DOWNLOAD_PATH, "gse_client-windows-x86_64_upgrade.tgz"),
            os.path.join(settings.DOWNLOAD_PATH, "7z.dll"),
            os.path.join(settings.DOWNLOAD_PATH, "7z.exe"),
        ]


class PushAixUpgradePackageSuccessTestCase(PushUpgradePackageTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "下发 Aix 升级包成功"

    @classmethod
    def setup_obj_factory(cls):
        cls.obj_factory.host_os_type_options = [constants.OsType.AIX]

    def component_cls(self):
        return components.PushUpgradePackageComponent

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        models.Host.objects.filter(bk_host_id__in=cls.obj_factory.bk_host_ids).update(
            os_version="6.1.0.0.1", cpu_arch=constants.CpuType.powerpc
        )

    @staticmethod
    def get_assert_file_list():
        return [os.path.join(settings.DOWNLOAD_PATH, "gse_client-aix6-powerpc_upgrade.tgz")]


class PushAixUpgradePackageFailTestCase(utils.AgentServiceBaseTestCase, ABC):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "下发 Aix 升级包失败"

    @classmethod
    def setup_obj_factory(cls):
        cls.obj_factory.host_os_type_options = [constants.OsType.AIX]

    def component_cls(self):
        return components.PushUpgradePackageComponent

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        models.Host.objects.filter(bk_host_id__in=cls.obj_factory.bk_host_ids).update(
            os_version=constants.CpuType.x86_64, cpu_arch=constants.CpuType.powerpc
        )

    def cases(self):
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=False,
                    outputs={},
                ),
                schedule_assertion=None,
                execute_call_assertion=None,
                patchers=[],
            )
        ]
