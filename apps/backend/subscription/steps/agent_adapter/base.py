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
from dataclasses import dataclass


@dataclass
class AgentConfigTemplate:
    name: str
    content: str
    agent_name_from: str


@dataclass
class AgentSetupInfo:
    """Agent 设置信息"""

    # 是否未旧版本 Agent，用于兼容旁路判定
    is_legacy: bool

    # Agent 设置工具目录
    agent_tools_relative_dir: str = ""
    # 构件名称，is_legacy=False 不为空
    name: typing.Optional[str] = None
    # 构件版本，is_legacy=False 不为空
    version: typing.Optional[str] = None

    # extra setup info
    # 是否强制更新 AgentID，True：注册 AgentID 前会先
    force_update_agent_id: bool = False


class AgentSetupTools:
    GSE_FILE_CACHE_PREFIX: str = "/data"
    GSE_FILE_CACHE_DIR_BASE_NAME = "file_cache"

    @classmethod
    def generate_default_file_cache_dir(cls, path: str, is_legacy: bool) -> str:
        if is_legacy:
            file_cache_dir: str = os.path.join(cls.GSE_FILE_CACHE_PREFIX, os.path.basename(path))
        else:
            file_cache_dir: str = os.path.join(
                cls.GSE_FILE_CACHE_PREFIX, os.path.basename(path), cls.GSE_FILE_CACHE_DIR_BASE_NAME
            )
        return file_cache_dir

    @classmethod
    def full_gse_file_cache_dir(cls, path: str):
        last_dir = os.path.basename(path)
        if last_dir == cls.GSE_FILE_CACHE_DIR_BASE_NAME:
            return path
        else:
            return os.path.join(path, cls.GSE_FILE_CACHE_DIR_BASE_NAME)
