# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from enum import Enum
from typing import Dict, List

from django.utils.translation import ugettext_lazy as _

from apps.utils.cache import class_member_cache
from apps.utils.enum import EnhanceEnum
from config.default import StorageType as DefaultStorageType


class CosBucketEnum(EnhanceEnum):
    """对象存储仓库枚举"""

    PUBLIC = "public"
    PRIVATE = "private"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.PRIVATE: _("私有仓库"), cls.PUBLIC: _("公共仓库")}


class JobFileType(EnhanceEnum):
    """作业平台源文件类型"""

    SERVER = 1
    THIRD_PART = 3

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.SERVER: _("服务器文件"), cls.THIRD_PART: _("第三方文件源文件")}


class StorageType(EnhanceEnum):
    """文件存储类型枚举
    为了避免循环引用，在default中维护DefaultStorageType
    不允许继承已有枚举成员的Enum，故直接赋值，注意更改DefaultStorageType需要同步
    参考：https://stackoverflow.com/questions/33679930/how-to-extend-python-enum
    """

    BLUEKING_ARTIFACTORY = DefaultStorageType.BLUEKING_ARTIFACTORY.value
    FILE_SYSTEM = DefaultStorageType.FILE_SYSTEM.value

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.BLUEKING_ARTIFACTORY: _("蓝鲸制品库"), cls.FILE_SYSTEM: _("本地文件系统")}

    @classmethod
    @class_member_cache()
    def list_cos_member_values(cls) -> List[str]:
        """列举属于对象存储类型"""
        return [cls.BLUEKING_ARTIFACTORY.value]

    @classmethod
    @class_member_cache()
    def get_member_value__job_file_type_map(cls) -> Dict[str, int]:
        """
        获取文件存储类型 - JOB源文件类型映射
        """
        return {
            cls.BLUEKING_ARTIFACTORY.value: JobFileType.THIRD_PART.value,
            cls.FILE_SYSTEM.value: JobFileType.SERVER.value,
        }


class FileCredentialType(EnhanceEnum):
    """文件凭证类型"""

    SECRET_KEY = "SECRET_KEY"
    ACCESS_KEY_SECRET_KEY = "ACCESS_KEY_SECRET_KEY"
    PASSWORD = "PASSWORD"
    USERNAME_PASSWORD = "USERNAME_PASSWORD"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {
            cls.SECRET_KEY: cls.SECRET_KEY.value,
            cls.ACCESS_KEY_SECRET_KEY: cls.ACCESS_KEY_SECRET_KEY.value,
            cls.PASSWORD: cls.PASSWORD.value,
            cls.USERNAME_PASSWORD: cls.USERNAME_PASSWORD.value,
        }
