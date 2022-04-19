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
import tarfile

from django.utils.translation import ugettext_lazy as _

from apps.backend.exceptions import AgentParseError, PluginParseError
from apps.core.files.storage import get_storage
from apps.node_man import constants

logger = logging.getLogger("app")


def pre_check(file_path: str, tmp_dir: str, action_type: str = constants.ProcType.AGENT) -> bool:

    storage = get_storage()
    panic = PluginParseError if action_type == constants.ProcType.PLUGIN else AgentParseError
    with storage.open(name=file_path, mode="rb") as tf_from_storage:
        with tarfile.open(fileobj=tf_from_storage) as tf:
            # 检查是否存在可疑内容
            for file_info in tf.getmembers():
                if file_info.name.startswith("/") or "../" in file_info.name:
                    logger.error(
                        "file-> {file_path} contains member-> {name} try to escape!".format(
                            file_path=file_path, name=file_info.name
                        )
                    )
                    raise panic(_("文件包含非法路径成员 -> {name}，请检查").format(name=file_info.name))
            logger.info(
                "file-> {file_path} extract to path -> {tmp_dir} success.".format(file_path=file_path, tmp_dir=tmp_dir)
            )
            tf.extractall(path=tmp_dir)
            return True
    return False
