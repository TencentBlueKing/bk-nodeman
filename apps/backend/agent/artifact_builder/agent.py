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
import logging
import os
import tarfile
import typing

from apps.node_man import constants

from . import base

logger = logging.getLogger("app")


class AgentArtifactBuilder(base.BaseArtifactBuilder):

    NAME = constants.GsePackageCode.AGENT.value
    PKG_DIR = constants.GsePackageDir.AGENT.value
    CERT_FILENAMES = [
        constants.GseCert.CA.value,
        constants.GseCert.AGENT_CERT.value,
        constants.GseCert.AGENT_KEY.value,
        constants.GseCert.CERT_ENCRYPT_KEY.value,
    ]

    def extract_initial_artifact(self, initial_artifact_local_path: str, extract_dir: str):
        with tarfile.open(name=initial_artifact_local_path) as tf:
            tf.extractall(path=extract_dir)
        extract_dir: str = os.path.join(extract_dir, self.BASE_PKG_DIR)
        self._inject_dependencies(extract_dir)
        return extract_dir

    def _get_support_files_info(self, extract_dir: str) -> typing.Dict[str, typing.Any]:
        # Agent 包管理实现
        pass
