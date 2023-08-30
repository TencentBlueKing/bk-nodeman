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
from apps.backend.tests.agent import utils
from apps.core.tag.constants import AGENT_NAME_TARGET_ID_MAP, TargetType
from apps.core.tag.models import Tag
from apps.node_man import models
from apps.node_man.constants import GsePackageCode

from .. import test_manage_commands


class FileSystemImportAgentTestCase(test_manage_commands.FileSystemImportAgentTestCase):
    @classmethod
    def setUpClass(cls):
        # 开启Agent包管理
        super().setUpClass()
        models.GlobalSettings.update_config(models.GlobalSettings.KeyEnum.ENABLE_AGENT_PKG_MANAGE.value, True)

    def tag_checker(self, target_id: int):

        agent_target_version = Tag.objects.get(
            target_id=target_id,
            name=self.OVERWRITE_VERSION,
            target_type=TargetType.AGENT.value,
        ).target_version

        self.assertTrue(agent_target_version == utils.VERSION)

    def test_make__overwrite_version(self):
        """测试版本号覆盖"""
        with self.ARTIFACT_BUILDER_CLASS(
            initial_artifact_path=self.ARCHIVE_PATH,
            overwrite_version=self.OVERWRITE_VERSION,
            tags=[self.OVERWRITE_VERSION],
        ) as builder:
            builder.make()

        # 测试
        self.pkg_checker(version_str=utils.VERSION)
        self.tag_checker(target_id=AGENT_NAME_TARGET_ID_MAP[GsePackageCode.AGENT.value])


class BkRepoImportAgentTestCase(FileSystemImportAgentTestCase, test_manage_commands.BkRepoImportAgentTestCase):
    pass
