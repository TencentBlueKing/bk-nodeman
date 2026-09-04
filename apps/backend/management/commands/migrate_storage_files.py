# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import os
from typing import List, Tuple

from django.core.management.base import BaseCommand

from apps.core.files.storage import get_storage
from apps.utils import files

from . import utils

log_and_print = utils.get_log_and_print("migrate_storage_files")


def _normalize_key(key: str) -> str:
    """统一路径分隔符为 /，并去除首尾多余的 /，便于后续拼接与相对路径计算。"""
    return "/".join([p for p in key.split("/") if p])


def _join_key(*parts: str) -> str:
    """拼接存储 key，统一分隔符。"""
    return "/".join([_normalize_key(p) for p in parts if p])


def _list_files_recursive(storage, prefix: str) -> List[str]:
    """
    递归列出 prefix 下的全部文件完整 key（保留完整路径，便于 open/save 直接使用）。

    :param storage: Storage 实例
    :param prefix: 目录前缀（如 /download/linux）
    :return: 文件完整 key 列表
    """
    file_keys: List[str] = []
    # 规范化前缀，末尾不带 /
    norm_prefix = _normalize_key(prefix)

    def _walk(current_prefix: str):
        # listdir 返回当前层 (directories, files)，名字均为相对 current_prefix 的短名
        # 注意：使用 Storage 公开方法 listdir（django 风格），不要调用 client.list_dir（内部方法）
        # listdir / open / save / exists / delete 均经过 _full_path 处理，key 约定完全一致
        directories, files = storage.listdir(current_prefix)
        for file_name in files:
            file_key = _join_key(current_prefix, file_name)
            file_keys.append(f"/{file_key}")
        for dir_name in directories:
            sub_prefix = _join_key(current_prefix, dir_name)
            _walk(f"/{sub_prefix}")

    _walk(f"/{norm_prefix}" if norm_prefix else "")
    return file_keys


def _relative_path(file_key: str, src_prefix: str) -> str:
    """计算 file_key 相对于 src_prefix 的相对路径，用于拼接到目标目录。"""
    norm_file = _normalize_key(file_key)
    norm_src = _normalize_key(src_prefix)
    if norm_file == norm_src:
        return ""
    # 去掉 src 前缀部分，得到相对路径
    if norm_file.startswith(norm_src + "/"):
        return norm_file[len(norm_src) + 1 :]
    # 非 src 子路径（理论上不会发生），整体作为相对名
    return os.path.basename(norm_file)


class Command(BaseCommand):
    """
    通用存储文件迁移命令：将指定源目录下的全部文件下载并上传到新目录。

    适用场景：
        例如将存量第三方插件包从 ``/download/{os}/{cpu_arch}`` 迁移到
        ``/download/{tenant_id}/{os}/{cpu_arch}``，或任意需要在同一存储后端内
        移动目录的场景。脚本不依赖 DB，仅操作存储层，可反复执行、可回滚。

    特性：
        - 递归遍历源目录，保留原有的子目录结构
        - 下载后重新上传到目标目录（含相对路径）
        - 支持 --dry-run 仅列出待迁移文件、不实际读写
        - 支持 --delete 迁移成功后删除源文件
        - 支持 --skip-existing 当目标已存在时跳过（仅复制到新路径，不删除源）

    用法：
        # 迁移（保留源文件）
        python manage.py migrate_storage_files --src /download/linux --dst /download/tenant1/linux
        # 仅预览
        python manage.py migrate_storage_files --src /download/linux --dst /download/tenant1/linux --dry-run
        # 迁移并删除源
        python manage.py migrate_storage_files --src /download/linux --dst /download/tenant1/linux --delete
        # 目标已存在则跳过
        python manage.py migrate_storage_files --src /download/linux --dst /download/tenant1/linux --skip-existing
    """

    def add_arguments(self, parser):
        parser.add_argument("--src", required=True, help="源目录前缀（完整 key，如 /download/linux）")
        parser.add_argument("--dst", required=True, help="目标目录前缀（完整 key，如 /download/tenant1/linux）")
        parser.add_argument(
            "--delete", action="store_true", help="迁移（复制）完成后删除源目录下的文件（默认保留）"
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="仅列出待迁移文件，不执行实际下载/上传/删除"
        )
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            help="目标文件已存在则跳过该文件（不重新上传、不删除源）",
        )
        parser.add_argument(
            "--storage-type",
            default=None,
            help="存储类型，对应 settings.STORAGE_TYPE 的取值（默认使用 settings.STORAGE_TYPE）",
        )

    def handle(self, *args, **options):
        src = options["src"]
        dst = options["dst"]
        is_delete = options["delete"]
        is_dry_run = options["dry_run"]
        skip_existing = options["skip_existing"]
        storage_type = options["storage_type"]

        # file_overwrite=True：避免目标已存在时 save 自动追加随机后缀，保证目标名与源一致
        storage = get_storage(storage_type=storage_type, file_overwrite=True)

        log_and_print(f"scanning source -> {src}")
        file_keys = _list_files_recursive(storage, src)
        log_and_print(f"found {len(file_keys)} file(s) under {src}")

        if is_dry_run:
            for file_key in file_keys:
                log_and_print(f"[dry-run] would migrate: {file_key}")
            log_and_print("dry-run finished, nothing changed.")
            return

        migrated_count = 0
        skipped_count = 0
        deleted_count = 0
        failed_count = 0

        for file_key in file_keys:
            relative = _relative_path(file_key, src)
            dst_key = f"/{_join_key(dst, relative)}" if relative else f"/{_normalize_key(dst)}"

            if skip_existing and storage.exists(dst_key):
                skipped_count += 1
                log_and_print(f"skip (target exists): {dst_key}")
                continue

            try:
                # 下载：从存储读取源文件
                with storage.open(name=file_key, mode="rb") as src_fs:
                    # 上传：写入目标路径（dst_key 已带 / 前缀，save 内部会保持）
                    storage.save(name=dst_key, content=src_fs)
            except Exception as err:  # noqa: BLE001
                failed_count += 1
                log_and_print(f"failed to migrate {file_key} -> {dst_key}: {err}")
                continue

            migrated_count += 1
            log_and_print(f"migrated: {file_key} -> {dst_key}")

            if is_delete:
                try:
                    storage.delete(name=file_key)
                    deleted_count += 1
                except Exception as err:  # noqa: BLE001
                    log_and_print(f"failed to delete source {file_key}: {err}")

        log_and_print(
            f"done. migrated={migrated_count}, skipped={skipped_count}, deleted={deleted_count}, failed={failed_count}"
        )
