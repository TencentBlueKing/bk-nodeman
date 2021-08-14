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
from typing import Callable, Dict

from bkstorages.backends import bkrepo
from django.conf import settings
from django.core.files.storage import FileSystemStorage, Storage, get_storage_class
from django.utils.deconstruct import deconstructible
from django.utils.functional import cached_property

from apps.core.files.base import StorageFileOverwriteMixin


@deconstructible
class CustomBKRepoStorage(StorageFileOverwriteMixin, bkrepo.BKRepoStorage):

    location = getattr(settings, "BKREPO_LOCATION", "")
    file_overwrite = getattr(settings, "FILE_OVERWRITE", False)

    endpoint_url = settings.BKREPO_ENDPOINT_URL
    username = settings.BKREPO_USERNAME
    password = settings.BKREPO_PASSWORD
    project_id = settings.BKREPO_PROJECT
    bucket = settings.BKREPO_BUCKET

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
        username = username or self.username
        password = password or self.password
        project_id = project_id or self.project_id
        bucket = bucket or self.bucket
        endpoint_url = endpoint_url or self.endpoint_url
        file_overwrite = file_overwrite or self.file_overwrite
        super().__init__(
            root_path=root_path,
            username=username,
            password=password,
            project_id=project_id,
            bucket=bucket,
            endpoint_url=endpoint_url,
            file_overwrite=file_overwrite,
        )


@deconstructible
class AdminFileSystemStorage(StorageFileOverwriteMixin, FileSystemStorage):

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
        super().__init__(
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


# 缓存最基础的Storage
_STORAGE_OBJ_CACHE: [str, Storage] = {}


def cache_storage_obj(get_storage_func: Callable[[str, Dict], Storage]):
    """用于Storage 缓存读写的装饰器"""

    def inner(storage_type: str = settings.STORAGE_TYPE, *args, **construct_params) -> Storage:
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
def get_storage(storage_type: str = settings.STORAGE_TYPE, safe: bool = False, **construct_params) -> Storage:
    """
    获取 Storage
    :param storage_type: 文件存储类型，参考 constants.StorageType
    :param safe: 是否启用安全访问，当前项目不存在用户直接指定上传路径的情况，该字段使用默认值即可
    :param construct_params: storage class 构造参数，用于修改storage某些默认行为（写入仓库、base url等）
    :return: Storage实例
    """
    storage_import_path = settings.STORAGE_TYPE_IMPORT_PATH_MAP.get(storage_type)
    if storage_import_path is None:
        raise ValueError(f"please provide valid storage_type {settings.STORAGE_TYPE_IMPORT_PATH_MAP.values()}")
    storage_class = get_storage_class(import_path=storage_import_path)

    if safe:
        if not hasattr(storage_class, "safe_class"):
            raise ValueError(f"please add safe_class to {storage_class.__name__}")
        return storage_class.safe_class(**construct_params)
    return storage_class(**construct_params)
