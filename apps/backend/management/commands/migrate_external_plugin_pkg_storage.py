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

from typing import List

from django.core.management.base import BaseCommand

from apps.core.files.storage import get_storage
from apps.node_man.models import GsePluginDesc, Packages

from . import utils

log_and_print = utils.get_log_and_print("migrate_external_plugin_pkg_storage")


class Command(BaseCommand):
    """
    将存量第三方插件包适配新的租户隔离路径。

    背景：
        新上传逻辑已对第三方插件包使用 ``DOWNLOAD_PATH/{tenant_id}/{os}/{cpu_arch}/{pkg_name}`` 的隔离路径，
        但存量第三方包的文件与 DB 记录（pkg_path/location）仍处于 ``DOWNLOAD_PATH/{os}/{cpu_arch}/{pkg_name}``。
        本命令同时完成两件事：
          1. 回填 DB 的 pkg_path / location，加上租户前缀；
          2. 将物理文件从旧路径（无租户层）复制到新的租户隔离路径。

    说明：
        不使用 Django migration，统一通过本命令执行，便于在生产环境按需反复运行与回滚。

    用法：
        python manage.py migrate_external_plugin_pkg_storage            # 正向：复制（保留旧文件）
        python manage.py migrate_external_plugin_pkg_storage --delete  # 正向：复制后删除旧文件
        python manage.py migrate_external_plugin_pkg_storage --rollback            # 回滚：DB 去租户前缀 + 物理文件迁回旧路径（保留新文件）
        python manage.py migrate_external_plugin_pkg_storage --rollback --delete  # 回滚：物理文件迁回旧路径后删除新路径文件
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete", action="store_true", help="复制/回滚完成后是否删除源路径下的插件包文件（默认保留）"
        )
        parser.add_argument(
            "--rollback", action="store_true", help="回滚模式：将 DB 的 pkg_path/location 还原为无租户前缀的旧路径，并将物理文件迁回旧路径"
        )

    @staticmethod
    def _build_legacy_root(pkg_path: str) -> str:
        """根据 DB 中记录的 pkg_path 还原无租户层的旧目录根路径。

        pkg_path 可能为旧格式（.../download/os/cpu_arch）或已回填的新格式
        （.../download/{tenant_id}/os/cpu_arch）。无论哪种，旧文件始终位于
        .../download/os/cpu_arch，故统一取 download 后第二个段（租户层）剔除后的路径。
        """
        parts = [p for p in pkg_path.split("/") if p]
        if "download" in parts:
            idx = parts.index("download")
            # 去掉 download 之后的第一个段（即租户层），得到 .../download/os/cpu_arch
            root_parts = parts[: idx + 1] + parts[idx + 2 :]
        else:
            root_parts = parts
        return "/" + "/".join(root_parts)

    def handle(self, *args, **options):
        is_delete = options["delete"]
        is_rollback = options["rollback"]
        storage = get_storage(file_overwrite=True)

        external_projects = set(GsePluginDesc.objects.filter(category="external").values_list("name", flat=True))
        if not external_projects:
            log_and_print("no external plugin found, nothing to do")
            return

        # 仅处理现存且已就绪的第三方插件包
        pkg_objs: List[Packages] = list(Packages.objects.filter(project__in=external_projects, is_ready=True))

        migrated_count = 0
        skipped_count = 0
        for pkg in pkg_objs:
            tenant_id = pkg.tenant_id or "default"
            # 无租户层的旧目录根：DOWNLOAD_PATH/os/cpu_arch
            legacy_root = self._build_legacy_root(pkg.pkg_path)
            legacy_root_parts = [p for p in legacy_root.split("/") if p]
            if "download" in legacy_root_parts:
                idx = legacy_root_parts.index("download")
                new_root_parts = legacy_root_parts[: idx + 1] + [tenant_id] + legacy_root_parts[idx + 1 :]
            else:
                new_root_parts = [tenant_id] + legacy_root_parts
            # 带租户前缀的新目录根：DOWNLOAD_PATH/tenant_id/os/cpu_arch
            new_pkg_path = "/" + "/".join(new_root_parts)
            new_location = f"http://{{LAN_IP}}/download/{tenant_id}/{pkg.os}/{pkg.cpu_arch}"
            old_file_path = f"{legacy_root}/{pkg.pkg_name}"
            new_file_path = f"{new_pkg_path}/{pkg.pkg_name}"

            if is_rollback:
                # 回滚：物理文件从新路径迁回旧路径，DB 去租户前缀
                self._rollback_pkg(pkg, storage, old_file_path, new_file_path, legacy_root, is_delete)
                continue

            # 正向：物理文件从旧路径迁到新路径，DB 加租户前缀
            if not storage.exists(old_file_path):
                skipped_count += 1
                log_and_print(f"skip (source not exists): {old_file_path}")
                continue

            if storage.exists(new_file_path):
                # 目标文件已存在：仅确保 DB 字段已回填为带租户前缀的值
                if pkg.pkg_path != new_pkg_path or pkg.location != new_location:
                    pkg.pkg_path = new_pkg_path
                    pkg.location = new_location
                    pkg.save(update_fields=["pkg_path", "location"])
                    log_and_print(f"db updated (target exists): {new_pkg_path}")
                else:
                    skipped_count += 1
                    log_and_print(f"skip (target already exists): {new_file_path}")
                continue

            with storage.open(name=old_file_path, mode="rb") as old_fs:
                storage.save(name=new_file_path, content=old_fs)

            # 回填 DB 字段（pkg_path / location），与新上传逻辑保持一致
            pkg.pkg_path = new_pkg_path
            pkg.location = new_location
            pkg.save(update_fields=["pkg_path", "location"])

            if is_delete:
                try:
                    storage.delete(name=old_file_path)
                except Exception as err:  # noqa: BLE001
                    log_and_print(f"failed to delete old file {old_file_path}: {err}")

            migrated_count += 1
            log_and_print(f"migrated: {old_file_path} -> {new_file_path}")

        log_and_print(f"done. migrated={migrated_count}, skipped={skipped_count}")

    def _rollback_pkg(self, pkg, storage, old_file_path, new_file_path, legacy_root, is_delete):
        """回滚单个插件包：DB 去租户前缀，物理文件从新路径迁回旧路径。"""
        # DB 已是旧格式则无需处理
        if pkg.pkg_path == legacy_root and pkg.location == f"http://{{LAN_IP}}/download/{pkg.os}/{pkg.cpu_arch}":
            log_and_print(f"skip (already legacy): {legacy_root}")
            return

        if not storage.exists(new_file_path):
            # 新路径文件不存在：若旧路径文件也不存在则无法回滚
            if not storage.exists(old_file_path):
                log_and_print(f"skip (both not exists): new={new_file_path}, old={old_file_path}")
                return

        if not storage.exists(old_file_path) and storage.exists(new_file_path):
            # 将新路径物理文件复制回旧路径
            with storage.open(name=new_file_path, mode="rb") as new_fs:
                storage.save(name=old_file_path, content=new_fs)

        # 还原 DB 字段为无租户前缀的旧格式
        pkg.pkg_path = legacy_root
        pkg.location = f"http://{{LAN_IP}}/download/{pkg.os}/{pkg.cpu_arch}"
        pkg.save(update_fields=["pkg_path", "location"])
        log_and_print(f"rolled back db/db: {new_file_path} -> {old_file_path}")

        if is_delete:
            try:
                if storage.exists(new_file_path):
                    storage.delete(name=new_file_path)
            except Exception as err:  # noqa: BLE001
                log_and_print(f"failed to delete new file {new_file_path}: {err}")
