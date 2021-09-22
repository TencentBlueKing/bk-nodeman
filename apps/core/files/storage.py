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
import os
from typing import Any, Callable, Dict, List, Optional

from bkstorages.backends import bkrepo
from django.conf import settings
from django.core.files.storage import FileSystemStorage, Storage, get_storage_class
from django.utils.deconstruct import deconstructible
from django.utils.functional import cached_property

from apps.utils.basic import filter_values

from . import constants
from .base import BaseStorage
from .file_source import BkJobFileSourceManager


@deconstructible
class CustomBKRepoStorage(BaseStorage, bkrepo.BKRepoStorage):

    storage_type: str = constants.StorageType.BLUEKING_ARTIFACTORY.value
    location: str = getattr(settings, "BKREPO_LOCATION", "")
    file_overwrite: Optional[bool] = None

    endpoint_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    project_id: Optional[str] = None
    bucket: Optional[str] = None

    def __init__(
        self,
        root_path=None,
        username=None,
        password=None,
        project_id=None,
        bucket=None,
        endpoint_url=None,
        file_overwrite=None,
    ):
        # 类成员变量应该和构造函数解耦，通过 params or default 的形式给构造参数赋值，防止该类被继承扩展时需要覆盖全部的成员默认值
        root_path = root_path or self.location
        self.username = username or settings.BKREPO_USERNAME
        self.password = password or settings.BKREPO_PASSWORD
        self.project_id = project_id or settings.BKREPO_PROJECT
        self.bucket = bucket or settings.BKREPO_BUCKET
        self.endpoint_url = endpoint_url or settings.BKREPO_ENDPOINT_URL
        self.file_overwrite = file_overwrite or settings.FILE_OVERWRITE

        # 根据 MRO 顺序，super() 仅调用 BaseStorage.__init__()，通过显式调用 BKRepoStorage 的初始化函数
        # 获得自定义 BaseStorage 类的重写特性，同时向 BKRepoStorage 注入成员变量
        bkrepo.BKRepoStorage.__init__(
            self,
            root_path=root_path,
            username=self.username,
            password=self.password,
            project_id=self.project_id,
            bucket=self.bucket,
            endpoint_url=self.endpoint_url,
            file_overwrite=self.file_overwrite,
        )

    def path(self, name):
        raise NotImplementedError()

    def _handle_file_source_list(
        self, file_source_list: List[Dict[str, Any]], extra_transfer_file_params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:

        # 获取或创建文件源
        file_source_obj = BkJobFileSourceManager.get_or_create_file_source(
            bk_biz_id=extra_transfer_file_params["bk_biz_id"],
            storage_type=self.storage_type,
            credential_type=constants.FileCredentialType.USERNAME_PASSWORD.value,
            credential_auth_info={"credential_username": self.username, "credential_password": self.password},
            access_params={"base_url": self.endpoint_url},
        )

        file_source_with_source_info_list = []
        for file_source in file_source_list:
            # 作业平台要求制品库分发的路径带上 project/bucket 前缀
            file_list = [
                os.path.join(self.project_id, self.bucket) + file_path for file_path in file_source.get("file_list", [])
            ]

            file_source_with_source_info_list.append(
                {
                    "file_list": file_list,
                    "file_source_id": file_source_obj.file_source_id,
                    "file_type": constants.StorageType.get_member_value__job_file_type_map()[self.storage_type],
                }
            )

        return file_source_with_source_info_list


@deconstructible
class AdminFileSystemStorage(BaseStorage, FileSystemStorage):

    storage_type = constants.StorageType.FILE_SYSTEM.value
    safe_class = FileSystemStorage
    OS_OPEN_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)

    def __init__(
        self,
        location=None,
        base_url=None,
        file_permissions_mode=None,
        directory_permissions_mode=None,
        file_overwrite=None,
    ):
        FileSystemStorage.__init__(
            self,
            location=location,
            base_url=base_url,
            file_permissions_mode=file_permissions_mode,
            directory_permissions_mode=directory_permissions_mode,
        )

        if file_overwrite is not None and isinstance(file_overwrite, bool):
            self.file_overwrite = file_overwrite

        # 如果文件允许覆盖，去掉 O_CREAT 配置，存在文件打开时不报错
        if self.file_overwrite:
            self.OS_OPEN_FLAGS = os.O_WRONLY | os.O_CREAT | getattr(os, "O_BINARY", 0)

    # 重写 path，将 safe_join 替换为 os.path.join，从而满足往「项目根路径」外读写的需求
    # safe_join 仅允许项目根目录以内的读写，具体参考 -> django.utils._os safe_join
    # 本项目的读写控制不存在用户行为，保留safe_mode成员变量，便于切换
    def path(self, name):
        return os.path.join(self.location, name)

    @cached_property
    def location(self):
        """路径指向 / ，重写前路径指向「项目根目录」"""
        return self.base_location

    def _handle_file_source_list(
        self, file_source_list: List[Dict[str, Any]], extra_transfer_file_params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        预处理源文件列表，添加文件源等信息
        :param file_source_list: 源文件
        :param extra_transfer_file_params: transfer_files 的其他参数
        :return: 源文件对象列表
        """

        account = {
            "alias": extra_transfer_file_params.get("account_alias"),
            "id": extra_transfer_file_params.get("account_id"),
        }

        file_source_with_source_info_list = []
        for file_source in file_source_list:
            file_source_with_source_info_list.append(
                {
                    "file_list": file_source.get("file_list", []),
                    "server": {
                        # 添加 NFS 服务器信息
                        "ip_list": [{"bk_cloud_id": settings.DEFAULT_CLOUD_ID, "ip": settings.BKAPP_NFS_IP}]
                    },
                    "account": filter_values(account),
                    "file_type": constants.StorageType.get_member_value__job_file_type_map()[self.storage_type],
                }
            )

        return file_source_with_source_info_list


# 缓存最基础的Storage
_STORAGE_OBJ_CACHE: [str, Storage] = {}


def cache_storage_obj(get_storage_func: Callable[[str, Dict], Storage]):
    """用于Storage 缓存读写的装饰器"""

    def inner(storage_type: Optional[str] = None, *args, **construct_params) -> Storage:
        # 仅默认参数情况下返回缓存
        if not (construct_params or args) and storage_type in _STORAGE_OBJ_CACHE:
            return _STORAGE_OBJ_CACHE[storage_type]

        storage_obj = get_storage_func(storage_type, *args, **construct_params)

        # 仅默认参数情况下写入缓存
        if not (construct_params or args):
            _STORAGE_OBJ_CACHE[storage_type] = storage_obj

        return storage_obj

    return inner


@cache_storage_obj
def get_storage(storage_type: Optional[str] = None, safe: bool = False, **construct_params) -> BaseStorage:
    """
    获取 Storage
    :param storage_type: 文件存储类型，参考 constants.StorageType
    :param safe: 是否启用安全访问，当前项目不存在用户直接指定上传路径的情况，该字段使用默认值即可
    :param construct_params: storage class 构造参数，用于修改storage某些默认行为（写入仓库、base url等）
    :return: Storage实例
    """
    storage_type = storage_type or settings.STORAGE_TYPE
    storage_import_path = settings.STORAGE_TYPE_IMPORT_PATH_MAP.get(storage_type)
    if storage_import_path is None:
        raise ValueError(f"please provide valid storage_type {settings.STORAGE_TYPE_IMPORT_PATH_MAP.values()}")
    storage_class = get_storage_class(import_path=storage_import_path)

    if safe:
        if not hasattr(storage_class, "safe_class"):
            raise ValueError(f"please add safe_class to {storage_class.__name__}")
        return storage_class.safe_class(**construct_params)
    return storage_class(**construct_params)
